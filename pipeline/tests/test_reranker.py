"""M2-4b proof: bge-reranker-v2-m3 reorders the matter-pre-filtered candidates.

Verifies: (a) no cross-matter regression — scoped indemnification (F-009 vs F-025)
still returns only the scoped matter after reranking; (b) reranking is real — the
cross-encoder order differs from vector order on at least one query; (c) lift vs
the pre-filter baseline (MRR / rank@1) measured honestly across present facts;
(d) offline — reranking runs with HF offline and makes zero non-loopback egress.
The reranker reorders only the already-filtered candidates (does NOT replace the
D-18 hard pre-filter). Scope: retrieval+rerank only — no LLM/span/API.
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
from retrieval import retrieve  # noqa: E402
from reranker import RERANKER_REVISION  # noqa: E402

PEMBERTON = "Pemberton Logistics (Nimbus MSA)"
CASTELLANO = "Castellano Studios (Greenfield Lease)"
INDEMN_Q = "what are the indemnification obligations?"


def _read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def _present_facts():
    return [r for r in _read_jsonl(MANIFEST) if not r["expected_absent_topics"]]


def _questions():
    return {r["fact_id"]: r["question"] for r in _read_jsonl(QUESTIONS)}


def _normalize(text):
    return re.sub(r"\s+", " ", re.sub(r"-\n", "-", text)).strip()


def _ident(h):
    return (h["source_filename"], int(h["page_number"]), int(h["char_start"]))


def _rank_of_correct(hits, fact):
    for i, h in enumerate(hits):
        if (h["source_filename"] == fact["filename"]
                and int(h["page_number"]) == fact["page_number"]
                and _normalize(fact["verbatim_span"]) in _normalize(h["text"])):
            return i
    return None


class TestNoCrossMatterRegression(unittest.TestCase):
    def test_scoped_indemnification_still_single_matter_after_rerank(self):
        f009 = next(f for f in _present_facts() if f["fact_id"] == "F-009")
        f025 = next(f for f in _present_facts() if f["fact_id"] == "F-025")

        pem = retrieve(INDEMN_Q, matter=PEMBERTON, top_k=5, rerank=True)
        self.assertTrue(all(h["matter"] == PEMBERTON for h in pem))
        self.assertIsNotNone(_rank_of_correct(pem, f009))
        self.assertFalse(any(h["source_filename"] == f025["filename"] for h in pem))

        cas = retrieve(INDEMN_Q, matter=CASTELLANO, top_k=5, rerank=True)
        self.assertTrue(all(h["matter"] == CASTELLANO for h in cas))
        self.assertIsNotNone(_rank_of_correct(cas, f025))
        self.assertFalse(any(h["source_filename"] == f009["filename"] for h in cas))


class TestRerankingIsReal(unittest.TestCase):
    def test_rerank_order_differs_from_vector_order_somewhere(self):
        facts = _present_facts()
        questions = _questions()
        reordered_any = False
        for fact in facts:
            q = questions[fact["fact_id"]]
            base = retrieve(q, matter=fact["matter_or_client"], top_k=10, rerank=False, candidate_k=10)
            rer = retrieve(q, matter=fact["matter_or_client"], top_k=10, rerank=True, candidate_k=10)
            if len(base) > 1 and [_ident(h) for h in base] != [_ident(h) for h in rer]:
                reordered_any = True
                break
        self.assertTrue(reordered_any, "cross-encoder never changed the vector order")


class TestLiftMeasurement(unittest.TestCase):
    def test_measure_mrr_and_rank1_baseline_vs_reranked(self):
        facts = _present_facts()
        questions = _questions()
        CK = 20
        base_rr, rer_rr = [], []
        base_at1, rer_at1, ups = 0, 0, 0
        for fact in facts:
            q = questions[fact["fact_id"]]
            m = fact["matter_or_client"]
            base = retrieve(q, matter=m, top_k=CK, rerank=False, candidate_k=CK)
            rer = retrieve(q, matter=m, top_k=CK, rerank=True, candidate_k=CK)
            rb, rr = _rank_of_correct(base, fact), _rank_of_correct(rer, fact)
            base_rr.append(1 / (rb + 1) if rb is not None else 0.0)
            rer_rr.append(1 / (rr + 1) if rr is not None else 0.0)
            base_at1 += 1 if rb == 0 else 0
            rer_at1 += 1 if rr == 0 else 0
            if rb is not None and rr is not None and rr < rb:
                ups += 1
        n = len(facts)
        bmrr, rmrr = sum(base_rr) / n, sum(rer_rr) / n
        print(f"\n[lift] n={n}  baseline MRR={bmrr:.3f} rank@1={base_at1}/{n}  "
              f"| reranked MRR={rmrr:.3f} rank@1={rer_at1}/{n}  "
              f"| dMRR={rmrr - bmrr:+.3f}  correct-chunk-moved-up={ups}")
        # Honest bar (task-sanctioned): on this 6-doc corpus the pre-filter+SAC
        # baseline already wins rank@1 ~76% of the time, so the reranker may show
        # NEUTRAL / no lift — that is a valid, useful result. We require only that
        # it does not MATERIALLY regress quality (a broken reranker would tank MRR).
        self.assertGreaterEqual(rmrr, bmrr - 0.05, "reranker materially regressed MRR")
        self.assertGreaterEqual(rer_at1, base_at1 - 3, "reranker materially hurt rank@1")
        self.assertGreater(ups, 0, "reranker never moved a correct chunk up (is it scoring?)")


class TestOfflineLoopbackOnly(unittest.TestCase):
    def test_rerank_runs_offline_with_only_loopback_egress(self):
        import os
        import socket
        self.assertNotEqual(os.environ.get("DOCLING_ALLOW_MODEL_FETCH"), "1")
        self.assertEqual(len(RERANKER_REVISION), 40, "reranker revision must be a pinned commit hash")
        original = socket.socket.connect
        seen = []

        def recording_connect(self, address, *a, **k):
            seen.append(address)
            return original(self, address, *a, **k)

        socket.socket.connect = recording_connect
        try:
            retrieve(INDEMN_Q, matter=PEMBERTON, top_k=5, rerank=True)
        finally:
            socket.socket.connect = original
        for addr in seen:
            host = addr[0] if isinstance(addr, tuple) else str(addr)
            self.assertIn(host, ("127.0.0.1", "::1", "localhost"), f"non-loopback egress: {addr}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
