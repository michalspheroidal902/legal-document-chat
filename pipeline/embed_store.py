"""M2-3 — Embed the M2-2 chunks with bge-m3 (system Ollama) and store in LanceDB.

Each chunk's ``embedding_text`` (the SAC-prefixed text — the D-18 anti-DRM signal)
is embedded via the system Ollama at 127.0.0.1:11434 (bge-m3, 1024-dim, D-11), NOT
the bare ``text``. Vectors + full payload {source_filename, matter, page_number,
section, char_start, char_end, text} are written to an embedded LanceDB table. The
text + offsets are retained in the payload because M2-6 needs them for mechanical
span-level citation verification.

The LanceDB store contains document text -> it must live under a git-ignored path
(D-28). Scope (M2-3): embed + store + a basic similarity sanity check only — no
metadata-filter, reranker, answering LLM, or HTTP surface (those are M2-4..M2-7).
"""

import json
import urllib.request
from pathlib import Path

import lancedb
import pyarrow as pa

EMBED_DIM = 1024

_SCHEMA = pa.schema([
    pa.field("vector", pa.list_(pa.float32(), EMBED_DIM)),
    pa.field("source_filename", pa.string()),
    pa.field("matter", pa.string()),
    pa.field("page_number", pa.int64()),
    pa.field("section", pa.string()),
    pa.field("char_start", pa.int64()),
    pa.field("char_end", pa.int64()),
    pa.field("text", pa.string()),
])


def embed_texts(texts, model="bge-m3", host="http://127.0.0.1:11434"):
    """Embed a list of strings via the loopback Ollama embed API -> list of vectors."""
    payload = json.dumps({"model": model, "input": list(texts)}).encode("utf-8")
    req = urllib.request.Request(
        f"{host}/api/embed", data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)["embeddings"]


def build_store(chunks_path, db_path, table_name="chunks"):
    """Embed every chunk's embedding_text and (over)write a LanceDB table. Returns the table."""
    chunks = [json.loads(l) for l in open(chunks_path, encoding="utf-8") if l.strip()]
    vectors = embed_texts([c["embedding_text"] for c in chunks])
    if any(len(v) != EMBED_DIM for v in vectors):
        raise ValueError("embedding dimension mismatch (expected 1024 from bge-m3)")

    rows = [{
        "vector": vec,
        "source_filename": c["source_filename"],
        "matter": c["matter"],
        "page_number": c["page_number"],
        "section": c["section"],
        "char_start": c["char_start"],
        "char_end": c["char_end"],
        "text": c["text"],
    } for c, vec in zip(chunks, vectors)]

    db = lancedb.connect(str(db_path))
    return db.create_table(table_name, data=rows, schema=_SCHEMA, mode="overwrite")


def open_table(db_path, table_name="chunks"):
    """Open an existing LanceDB table."""
    return lancedb.connect(str(db_path)).open_table(table_name)
