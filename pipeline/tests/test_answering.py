"""M2-5 proof: hand-rolled grounded answering over the matter-filtered context.

Verifies (a small validity check, not the full eval — that's M2-8): present facts
answer with the correct filename + real page citation; not-found refuses on
substance (D-30) and cites nothing; a DRM query answers from the right matter; and
the structured result exposes per-chunk grounding offsets (the M2-6 substrate).
Answering is hand-rolled over CE_PLAN §10 (no LlamaIndex, D-37); retrieval is the
rerank=False base path. Egress is loopback-only.
"""

import json
import sys
import unittest
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = PIPELINE_DIR.parent
MANIFEST = REPO_ROOT / "eval" / "golden_manifest.jsonl"
QUESTIONS = REPO_ROOT / "eval" / "golden_questions.jsonl"

sys.path.insert(0, str(PIPELINE_DIR))
from answering import answer, REFUSAL, _parse_citations  # noqa: E402

PEMBERTON = "Pemberton Logistics (Nimbus MSA)"
GROUNDING_FIELDS = {
    "chunk_id", "source_filename", "page_number", "char_start", "char_end", "text",
}


def _read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def _fact(fid):
    return next(r for r in _read_jsonl(MANIFEST) if r["fact_id"] == fid)


def _q(fid):
    return next(r["question"] for r in _read_jsonl(QUESTIONS) if r["fact_id"] == fid)


def _cited(result, filename, page):
    return any(c["filename"] == filename and int(c["page"]) == page for c in result["citations"])


class TestPresentFactAnswers(unittest.TestCase):
    def test_f001_effective_date_answer_cites_correct_filename_and_real_page(self):
        f = _fact("F-001")
        res = answer(_q("F-001"), matter=PEMBERTON)
        self.assertNotIn(REFUSAL, res["answer_text"])
        self.assertIn("March 14, 2024", res["answer_text"])
        self.assertTrue(_cited(res, f["filename"], f["page_number"]),
                        f"missing citation {f['filename']} p{f['page_number']}: {res['citations']}")

    def test_f046_order_ruling_cites_correct_filename_and_page(self):
        f = _fact("F-046")
        res = answer(_q("F-046"), matter="Tessaro v. Brightwater Mutual")
        self.assertNotIn(REFUSAL, res["answer_text"])
        self.assertTrue(_cited(res, f["filename"], f["page_number"]),
                        f"missing citation {f['filename']} p{f['page_number']}: {res['citations']}")


class TestStructuredGroundingForM26(unittest.TestCase):
    def test_grounding_chunks_expose_offsets(self):
        res = answer(_q("F-001"), matter=PEMBERTON)
        self.assertTrue(res["grounding_chunks"])
        for g in res["grounding_chunks"]:
            self.assertEqual(set(g.keys()), GROUNDING_FIELDS)
            self.assertIsInstance(g["char_start"], int)
            self.assertIsInstance(g["char_end"], int)
            self.assertLess(g["char_start"], g["char_end"])
            self.assertTrue(g["text"])
        # every parsed citation maps to a grounding chunk_id
        ids = {g["chunk_id"] for g in res["grounding_chunks"]}
        for c in res["citations"]:
            if c["chunk_id"] is not None:
                self.assertIn(c["chunk_id"], ids)


class TestNotFoundRefusesOnSubstance(unittest.TestCase):
    def test_nf001_and_nf002_refuse_and_cite_nothing(self):
        for fid in ("NF-001", "NF-002"):
            res = answer(_q(fid), matter=None)
            self.assertIn(REFUSAL, res["answer_text"], f"{fid} did not refuse: {res['answer_text'][:160]}")
            self.assertEqual(res["citations"], [], f"{fid} cited something for an absent topic")


class TestDRMRightMatter(unittest.TestCase):
    def test_f009_indemnification_answers_from_pemberton_not_castellano(self):
        res = answer(_q("F-009"), matter=PEMBERTON)
        self.assertNotIn(REFUSAL, res["answer_text"])
        self.assertTrue(_cited(res, "nimbus_pemberton_msa.pdf", 3))
        self.assertFalse(any(c["filename"] == "greenfield_castellano_lease.pdf" for c in res["citations"]))
        self.assertTrue(all(g["source_filename"] != "greenfield_castellano_lease.pdf"
                            for g in res["grounding_chunks"]))


class TestChunkDerivedCitations(unittest.TestCase):
    """D-38: displayed filename+page come from the chunk, never the model's prose (no LLM)."""

    def test_model_asserted_wrong_page_is_overridden_by_chunk_page(self):
        grounding = [{
            "chunk_id": "C1", "source_filename": "nimbus_pemberton_msa.pdf",
            "page_number": 1, "char_start": 40, "char_end": 346,
            "text": "This Master Services Agreement ... effective as of March 14, 2024 ...",
        }]
        # Model asserts page 99 and the wrong filename, but points at chunk C1.
        answer_text = ('The effective date is March 14, 2024 [document: WRONG_FILE.pdf, '
                       'page: 99, section: X, chunk: C1, span: "effective as of March 14, 2024"].')
        cites = _parse_citations(answer_text, grounding)
        self.assertEqual(len(cites), 1)
        self.assertEqual(cites[0]["page"], 1, "page must be chunk-derived, not the model's 99")
        self.assertEqual(cites[0]["filename"], "nimbus_pemberton_msa.pdf", "filename must be chunk-derived")
        self.assertEqual(cites[0]["chunk_id"], "C1")


class TestLoopbackOnlyEgress(unittest.TestCase):
    def test_all_connections_during_answer_are_loopback(self):
        import socket
        original = socket.socket.connect
        seen = []

        def recording_connect(self, address, *a, **k):
            seen.append(address)
            return original(self, address, *a, **k)

        socket.socket.connect = recording_connect
        try:
            answer(_q("F-001"), matter=PEMBERTON)
        finally:
            socket.socket.connect = original
        self.assertTrue(seen, "answering must make loopback calls (embed + chat)")
        for addr in seen:
            host = addr[0] if isinstance(addr, tuple) else str(addr)
            self.assertIn(host, ("127.0.0.1", "::1", "localhost"), f"non-loopback egress: {addr}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
