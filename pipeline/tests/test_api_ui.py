"""Demo UI (SC-5) proof: the source-viewer surface over the existing answer() API.

Closes CE_PLAN SC-5 ("expose retrieved snippets AND open the original at the cited
page"): GET / serves a thin read-only page and GET /source/{file} serves a corpus PDF
so a citation can open it at #page=N. The security-critical unit is the /source route:
it is PATH-LOCKED to the synthetic-corpus PDF dir (no traversal, .pdf only, must be an
existing file in the dir) — tested first. Loopback-only, synthetic docs only; /answer
is untouched (its M2-7 parity stands).
"""

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

PIPELINE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = PIPELINE_DIR.parent
CORPUS_PDF_DIR = REPO_ROOT / "documents" / "synthetic_corpus" / "pdf"

sys.path.insert(0, str(PIPELINE_DIR))
import api  # noqa: E402  (the module under test)

client = TestClient(api.app)
KNOWN_PDF = "nimbus_pemberton_msa.pdf"


class TestDemoPage(unittest.TestCase):
    def test_root_serves_html_with_query_surface(self):
        r = client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/html", r.headers["content-type"])
        self.assertIn("/answer", r.text)  # the page talks to the answer API


class TestMatters(unittest.TestCase):
    def test_matters_lists_store_allowlist(self):
        r = client.get("/eval/matters")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Pemberton Logistics (Nimbus MSA)", r.json()["matters"])


class TestSourceServesCorpusPdf(unittest.TestCase):
    def test_known_pdf_served_as_pdf_bytes(self):
        r = client.get(f"/source/{KNOWN_PDF}")
        self.assertEqual(r.status_code, 200)
        self.assertIn("application/pdf", r.headers["content-type"])
        self.assertEqual(r.content[:5], b"%PDF-")  # real PDF, not an HTML error


class TestSourceIsPathLocked(unittest.TestCase):
    """Security: the route must NEVER serve anything outside the corpus PDF dir."""

    def test_traversal_attempts_are_rejected(self):
        for bad in ["../answering.py", "../../CLAUDE.md", "....//answering.py",
                    "/etc/passwd", "%2e%2e/answering.py"]:
            r = client.get(f"/source/{bad}")
            self.assertEqual(r.status_code, 404, f"served a traversal target: {bad!r}")

    def test_non_pdf_in_dir_is_rejected(self):
        r = client.get("/source/answering.py")
        self.assertEqual(r.status_code, 404)

    def test_unknown_pdf_is_404(self):
        r = client.get("/source/no_such_doc.pdf")
        self.assertEqual(r.status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
