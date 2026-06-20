"""M2-3 proof: embed the M2-2 chunks (SAC text) with bge-m3, store in LanceDB.

Verifies: 50 chunks -> 50 rows, each a 1024-dim vector + complete payload that
round-trips; the embedded source is embedding_text (SAC), NOT bare text; a basic
similarity sanity check (plain vector search, no metadata filter) puts the correct
chunk in top-k for a few present-fact questions. Egress is loopback-only (the
Ollama embed call to 127.0.0.1:11434). Scope: embed + store + sanity only.
"""

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = PIPELINE_DIR.parent
CHUNKS = REPO_ROOT / "documents" / "synthetic_corpus" / "chunks" / "chunks.jsonl"
MANIFEST = REPO_ROOT / "eval" / "golden_manifest.jsonl"
QUESTIONS = REPO_ROOT / "eval" / "golden_questions.jsonl"

sys.path.insert(0, str(PIPELINE_DIR))
from embed_store import build_store, open_table, embed_texts, EMBED_DIM  # noqa: E402

PAYLOAD_FIELDS = {
    "source_filename", "matter", "page_number", "section", "char_start", "char_end", "text",
}


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb)


def _read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def _load_chunks():
    return _read_jsonl(CHUNKS)


def _present_facts():
    return {r["fact_id"]: r for r in _read_jsonl(MANIFEST) if not r["expected_absent_topics"]}


def _questions():
    return {r["fact_id"]: r["question"] for r in _read_jsonl(QUESTIONS)}


class EmbedStoreFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.table = build_store(CHUNKS, cls.tmp, "chunks")
        cls.rows = cls.table.to_arrow().to_pylist()
        cls.chunks = _load_chunks()


class TestStoreShapeAndPayload(EmbedStoreFixture):
    def test_50_rows_1024_dim_with_complete_payload_that_roundtrips(self):
        self.assertEqual(len(self.rows), 50)
        self.assertEqual(len(self.chunks), 50)
        # index source chunks by (filename, page, char_start) for round-trip check
        src = {(c["source_filename"], c["page_number"], c["char_start"]): c for c in self.chunks}
        for row in self.rows:
            self.assertEqual(len(list(row["vector"])), EMBED_DIM)  # 1024
            self.assertTrue(PAYLOAD_FIELDS.issubset(row.keys()))
            key = (row["source_filename"], int(row["page_number"]), int(row["char_start"]))
            self.assertIn(key, src, "row payload must map back to a source chunk")
            c = src[key]
            self.assertEqual(row["text"], c["text"])
            self.assertEqual(int(row["char_end"]), c["char_end"])
            self.assertEqual(row["matter"], c["matter"])
            self.assertEqual(row["section"], c["section"])


class TestEmbeddedSourceIsSACText(EmbedStoreFixture):
    def test_stored_vector_matches_embedding_text_not_bare_text(self):
        # Pick chunks where SAC prefix is non-trivial (section present) so the two differ.
        sample = [c for c in self.chunks if c["section"]][:3]
        self.assertTrue(sample)
        emb_sac = embed_texts([c["embedding_text"] for c in sample])
        emb_bare = embed_texts([c["text"] for c in sample])
        rows_by_key = {(r["source_filename"], int(r["page_number"]), int(r["char_start"])): r
                       for r in self.rows}
        for c, vs, vb in zip(sample, emb_sac, emb_bare):
            stored = list(rows_by_key[(c["source_filename"], c["page_number"], c["char_start"])]["vector"])
            sim_sac = _cosine(stored, vs)
            sim_bare = _cosine(stored, vb)
            self.assertGreater(sim_sac, 0.999, "stored vector must be the SAC embedding")
            self.assertGreater(sim_sac, sim_bare, "SAC embedding must fit better than bare text")


class TestSimilaritySanity(EmbedStoreFixture):
    def test_correct_chunk_in_topk_for_present_fact_questions(self):
        facts = _present_facts()
        questions = _questions()
        # A few diverse present facts across different documents.
        fact_ids = ["F-001", "F-019", "F-046"]
        k = 5
        for fid in fact_ids:
            fact = facts[fid]
            qvec = embed_texts([questions[fid]])[0]
            hits = self.table.search(qvec).limit(k).to_arrow().to_pylist()
            hit = any(
                h["source_filename"] == fact["filename"] and int(h["page_number"]) == fact["page_number"]
                and _normalize(fact["verbatim_span"]) in _normalize(h["text"])
                for h in hits
            )
            self.assertTrue(hit, f"{fid}: correct chunk not in top-{k}")


class TestLoopbackOnlyEgress(unittest.TestCase):
    def test_all_connections_during_embedding_are_loopback(self):
        import socket
        original = socket.socket.connect
        seen = []

        def recording_connect(self, address, *a, **k):
            seen.append(address)
            return original(self, address, *a, **k)

        socket.socket.connect = recording_connect
        try:
            tmp = tempfile.mkdtemp()
            build_store(CHUNKS, tmp, "chunks")
        finally:
            socket.socket.connect = original
        self.assertTrue(seen, "embedding must make the loopback Ollama call")
        for addr in seen:
            host = addr[0] if isinstance(addr, tuple) else str(addr)
            self.assertIn(host, ("127.0.0.1", "::1", "localhost"), f"non-loopback egress: {addr}")


def _normalize(text):
    import re
    return re.sub(r"\s+", " ", re.sub(r"-\n", "-", text)).strip()


if __name__ == "__main__":
    unittest.main(verbosity=2)
