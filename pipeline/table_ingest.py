"""T-TBL — table chunk + embed + index (D-50/D-51).

Turn extracted tables (``table_extract.extract_tables``) into embeddable chunks and append
them to a KB/scratch LanceDB store (NEVER the eval baseline). One Markdown table per chunk
(D-50); large tables split into multiple chunks, each repeating the header row.

Table-chunk verbatim-span semantics (D-19/D-38, the never-false-accept invariant): the
chunk's ``text`` IS its Markdown and ``char_start/char_end`` index into that Markdown
(self-relative, 0..len). The existing mechanical verifier therefore checks a cited cell
value by substring-overlap against the table chunk's own text — a fabricated value can
never match. These offsets are Docling-Markdown offsets, kept strictly separate from the
PyMuPDF page offsets used by prose chunks (offset-routing, D-51): one canonical extractor
per chunk, never mixed on the same chunk.

The prose (PyMuPDF) ingestion path is untouched; this is an additive, table-only path,
run only on table-bearing docs.
"""

from pathlib import Path

from embed_store import add_chunks
from table_extract import extract_tables

# Tag marking a chunk as Docling-sourced table markdown (offset-routing provenance, D-51).
TABLE_TAG = "[TABLE]"
_MAX_CHARS = 1400  # split a table's markdown above this, repeating the header row


def _split_markdown_table(markdown, max_chars=_MAX_CHARS):
    """Split a Markdown table into pieces under ``max_chars``, each repeating the
    header + separator rows. Small tables return as a single piece (D-50)."""
    md = markdown.strip()
    lines = md.splitlines()
    if len(md) <= max_chars or len(lines) < 3:
        return [md]
    header, sep, data = lines[0], lines[1], lines[2:]
    prefix = header + "\n" + sep
    pieces, cur = [], []
    for row in data:
        cand = prefix + "\n" + "\n".join(cur + [row])
        if cur and len(cand) > max_chars:
            pieces.append(prefix + "\n" + "\n".join(cur))
            cur = [row]
        else:
            cur.append(row)
    if cur:
        pieces.append(prefix + "\n" + "\n".join(cur))
    return pieces


def chunk_tables(tables, matter_slug, filename, max_chars=_MAX_CHARS):
    """Turn extracted tables into store-ready chunks (one Markdown table per chunk).

    Each chunk matches the embed-store payload schema plus ``embedding_text``:
    ``text`` is the Markdown; ``char_start=0`` / ``char_end=len(text)`` index into it
    (self-relative). ``section`` carries the ``[TABLE]`` extractor tag + page so the
    chunk's provenance is explicit. ``embedding_text`` is the Markdown with a short SAC
    context line (matter + table) so bge-m3 can retrieve a cell value.
    """
    chunks = []
    for t in tables:
        page = t.get("page_number")
        for piece in _split_markdown_table(t["markdown"], max_chars):
            section = f"{TABLE_TAG} page {page}"
            chunks.append({
                "source_filename": filename,
                "matter": matter_slug,
                "document_type": "table",
                "page_number": page,
                "section": section,
                "char_start": 0,
                "char_end": len(piece),
                "text": piece,
                "embedding_text": f"[Matter: {matter_slug} | Type: table | "
                                  f"Section: fee/exhibit schedule]\n{piece}",
            })
    return chunks


def has_tables(file_path):
    """Cheap PyMuPDF pre-check: does this PDF contain at least one table? Used to gate
    the heavy Docling table pass so it runs ONLY on table-bearing docs (D-51 latency).
    Best-effort: any error -> False (skip the table pass, never fail the prose ingest)."""
    try:
        import fitz
        with fitz.open(file_path) as doc:
            for page in doc:
                if len(page.find_tables().tables) > 0:
                    return True
    except Exception:
        return False
    return False


def ingest_tables(file_path, matter_slug, db_path, filename=None):
    """Extract -> chunk -> embed (bge-m3 loopback) -> APPEND table chunks into the
    KB/scratch store at ``db_path``. Returns the chunk list (``[]`` if the doc has no
    detected tables — the table path is skipped for table-free docs, D-51 latency).
    Writes ONLY to ``db_path`` (a KB/scratch store), never an eval baseline."""
    file_path = Path(file_path)
    name = filename or file_path.name
    tables = extract_tables(file_path)
    if not tables:
        return []
    chunks = chunk_tables(tables, matter_slug, name)
    add_chunks(chunks, db_path)  # embeds embedding_text via bge-m3, appends to 'chunks'
    return chunks
