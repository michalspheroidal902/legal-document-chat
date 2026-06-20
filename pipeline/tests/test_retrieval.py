"""M2-4 proof: metadata-filter-before-similarity retrieval with an explicit matter.

Headline: the M1 cross-matter pull is killed. The shared indemnification clause
(F-009 Pemberton vs F-025 Castellano, same verbatim span, different matters) must
resolve to ONLY the scoped matter when a matter is given, while an explicit
matter=None search-all stays honest (may return both). The matter pre-filter is a
hard scope applied BEFORE similarity, and the matter value is validated against the
store's known matters (no raw-text injection). Scope: retrieval only — no reranker,
LLM, span verification, or API.
"""

import json
import re
import sys
import unittest
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = PIPELINE_DIR.parent
MANIFEST = REPO_ROOT / "eval" / "golden_manifest.jsonl"
QUESTIONS = REPO_ROOT / "eval" / "golden_questions.jsonl"

sys.path.insert(0, str(PIPELINE_DIR))
from retrieval import retrieve, known_matters  # noqa: E402

PEMBERTON = "Pemberton Logistics (Nimbus MSA)"
CASTELLANO = "Castellano Studios (Greenfield Lease)"
INDEMN_Q = "what are the indemnification obligations?"


def _read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def _fact(fid):
    return next(r for r in _read_jsonl(MANIFEST) if r["fact_id"] == fid)


def _question(fid):
    return next(r["question"] for r in _read_jsonl(QUESTIONS) if r["fact_id"] == fid)


def _normalize(text):
    return re.sub(r"\s+", " ", re.sub(r"-\n", "-", text)).strip()


def _has_span(hits, filename, page, span):
    return any(
        h["source_filename"] == filename and int(h["page_number"]) == page
        and _normalize(span) in _normalize(h["text"])
        for h in hits
    )


class TestCrossMatterScoping(unittest.TestCase):
    def test_scoped_indemnification_returns_only_that_matter_both_directions(self):
        f009, f025 = _fact("F-009"), _fact("F-025")

        pem = retrieve(INDEMN_Q, matter=PEMBERTON, top_k=5)
        self.assertTrue(pem)
        self.assertTrue(all(h["matter"] == PEMBERTON for h in pem), "leaked a non-Pemberton chunk")
        self.assertTrue(_has_span(pem, f009["filename"], f009["page_number"], f009["verbatim_span"]),
                        "F-009 clause missing from Pemberton-scoped result")
        self.assertFalse(any(h["source_filename"] == f025["filename"] for h in pem),
                         "Castellano (F-025) leaked into Pemberton scope")

        cas = retrieve(INDEMN_Q, matter=CASTELLANO, top_k=5)
        self.assertTrue(all(h["matter"] == CASTELLANO for h in cas), "leaked a non-Castellano chunk")
        self.assertTrue(_has_span(cas, f025["filename"], f025["page_number"], f025["verbatim_span"]),
                        "F-025 clause missing from Castellano-scoped result")
        self.assertFalse(any(h["source_filename"] == f009["filename"] for h in cas),
                         "Pemberton (F-009) leaked into Castellano scope")

    def test_search_all_is_honest_not_silently_filtering(self):
        allm = retrieve(INDEMN_Q, matter=None, top_k=10)
        matters = {h["matter"] for h in allm}
        self.assertIn(PEMBERTON, matters)
        self.assertIn(CASTELLANO, matters)  # both present -> not silently scoped


class TestPrefilterBeforeSimilarity(unittest.TestCase):
    def test_filtered_pool_is_full_matter_subset_not_topk_then_drop(self):
        # top_k far exceeds the matter's size: a hard pre-filter can only return the
        # matter's own rows (here 6), proving similarity ran over the filtered subset.
        ref = retrieve("copyright fair use", matter="Public Domain (Reference)", top_k=100)
        self.assertEqual(len(ref), 6, "scoped pool must equal the matter's chunk count")
        self.assertTrue(all(h["matter"] == "Public Domain (Reference)" for h in ref))

    def test_scope_yields_full_topk_even_when_global_nn_are_another_matter(self):
        # "indemnification" globally pulls both matters; a post-hoc drop at limit=3
        # would return <3 Castellano. Pre-filter guarantees 3 scoped hits.
        cas = retrieve(INDEMN_Q, matter=CASTELLANO, top_k=3)
        self.assertEqual(len(cas), 3)
        self.assertTrue(all(h["matter"] == CASTELLANO for h in cas))


class TestMatterNamedQueryStillHits(unittest.TestCase):
    def test_f001_effective_date_hits_under_its_matter(self):
        f = _fact("F-001")
        hits = retrieve(_question("F-001"), matter=PEMBERTON, top_k=5)
        self.assertTrue(_has_span(hits, f["filename"], f["page_number"], f["verbatim_span"]))


class TestMatterValidation(unittest.TestCase):
    def test_unknown_or_injection_matter_is_rejected(self):
        self.assertIn(PEMBERTON, known_matters())
        with self.assertRaises(ValueError):
            retrieve(INDEMN_Q, matter="Nonexistent Matter")
        with self.assertRaises(ValueError):
            retrieve(INDEMN_Q, matter="' OR '1'='1")


class TestLoopbackOnlyEgress(unittest.TestCase):
    def test_all_connections_during_retrieval_are_loopback(self):
        import socket
        original = socket.socket.connect
        seen = []

        def recording_connect(self, address, *a, **k):
            seen.append(address)
            return original(self, address, *a, **k)

        socket.socket.connect = recording_connect
        try:
            retrieve(INDEMN_Q, matter=PEMBERTON, top_k=5)
        finally:
            socket.socket.connect = original
        self.assertTrue(seen, "retrieval must make the loopback embedding call")
        for addr in seen:
            host = addr[0] if isinstance(addr, tuple) else str(addr)
            self.assertIn(host, ("127.0.0.1", "::1", "localhost"), f"non-loopback egress: {addr}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
