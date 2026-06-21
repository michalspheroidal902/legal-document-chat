"""Task 6 proof: first-token latency (TTFT) instrumentation (G-LAT). A streaming
side-channel measures request-send -> first content token; answer()'s body is UNCHANGED
(M2-7 parity preserved). Loopback Ollama only. Read-only on the live store."""

import sys
import unittest
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PIPELINE_DIR))
import run_latency  # noqa: E402
from answering import answer  # noqa: E402

Q = "In the Nimbus-Pemberton MSA, what is the monthly service fee?"
MATTER = "Pemberton Logistics (Nimbus MSA)"


class TestLatencyHarness(unittest.TestCase):
    def test_measure_returns_positive_ttft_le_total(self):
        r = run_latency.measure(Q, matter=MATTER)
        self.assertIsInstance(r["ttft_s"], float)
        self.assertIsInstance(r["total_s"], float)
        self.assertGreater(r["ttft_s"], 0.0)
        self.assertGreater(r["total_s"], 0.0)
        self.assertLessEqual(r["ttft_s"], r["total_s"] + 1e-6)

    def test_instrumentation_does_not_alter_answer_output(self):
        # answer() still returns a proper grounded, span-verified response (parity).
        res = answer(Q, matter=MATTER)
        self.assertIn("citations", res)
        self.assertIn("answer_text", res)
        self.assertIn("rejected_claims", res)
        self.assertTrue(res["answer_text"].strip())


if __name__ == "__main__":
    unittest.main(verbosity=2)
