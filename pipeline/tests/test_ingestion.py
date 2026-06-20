"""M2-1 ingestion proof: PyMuPDF recovers per-page text with correct page numbers.

Verifies against the existing M1 ground truth (eval/golden_manifest.jsonl): every
present-fact verbatim_span must be recoverable on the page whose number == the
record's page_number. This is the page-accuracy proof the turnkey stack could not
provide (D-29). Scope is PyMuPDF text extraction only — no chunking/embeddings/DB.
"""

import json
import re
import sys
import unittest
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = PIPELINE_DIR.parent
PDF_DIR = REPO_ROOT / "documents" / "synthetic_corpus" / "pdf"
MANIFEST = REPO_ROOT / "eval" / "golden_manifest.jsonl"

sys.path.insert(0, str(PIPELINE_DIR))
from ingestion import extract_pages  # noqa: E402


def _load_present_facts():
    """Present facts = records with an empty expected_absent_topics (per eval/README)."""
    facts = []
    with open(MANIFEST, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if not rec["expected_absent_topics"]:
                facts.append(rec)
    return facts


def _normalize(text):
    """Collapse PDF-layout artifacts so a manifest span can be located on its page.

    PDF text extraction injects a layout newline wherever a line wraps. When a wrap
    lands on a hyphenated compound (e.g. "twenty-four" -> "twenty-\nfour", F-019),
    only the NEWLINE is an artifact; the hyphen is real and is present in the
    manifest span. So we drop the wrap-newline but KEEP the hyphen, then collapse
    whitespace runs. extract_pages returns RAW text (verbatim, for the M2-6 offset
    check); this normalization is applied ONLY for this page-containment test.
    """
    text = re.sub(r"-\n", "-", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


class TestExtractPagesStructure(unittest.TestCase):
    def test_each_pdf_yields_contiguous_1based_pages_with_text(self):
        pdfs = sorted(PDF_DIR.glob("*.pdf"))
        self.assertEqual(len(pdfs), 6, "expected the 6 synthetic corpus PDFs")
        for pdf in pdfs:
            records = extract_pages(pdf)
            self.assertGreater(len(records), 0, f"{pdf.name}: no pages extracted")
            page_numbers = [r["page_number"] for r in records]
            self.assertEqual(
                page_numbers,
                list(range(1, len(records) + 1)),
                f"{pdf.name}: page numbers must be contiguous and 1-based",
            )
            for r in records:
                self.assertEqual(set(r.keys()), {"source_filename", "page_number", "page_text"})
                self.assertEqual(r["source_filename"], pdf.name)
                self.assertTrue(r["page_text"].strip(), f"{pdf.name} p{r['page_number']}: empty text")


class TestPresentFactSpansLandOnCorrectPage(unittest.TestCase):
    def test_every_present_fact_span_is_on_its_manifest_page(self):
        facts = _load_present_facts()
        self.assertEqual(len(facts), 63, "expected 63 present-fact records")

        # Cache: filename -> {page_number -> normalized page_text}
        pages_by_file = {}
        for pdf in PDF_DIR.glob("*.pdf"):
            pages_by_file[pdf.name] = {
                r["page_number"]: _normalize(r["page_text"]) for r in extract_pages(pdf)
            }

        misses = []
        for fact in facts:
            fname = fact["filename"]
            page = fact["page_number"]
            span = _normalize(fact["verbatim_span"])
            page_text = pages_by_file.get(fname, {}).get(page, "")
            if span not in page_text:
                misses.append((fact["fact_id"], fname, page, fact["verbatim_span"]))

        self.assertEqual(
            misses,
            [],
            "spans not found on their manifest page:\n"
            + "\n".join(f"  {fid} {fn} p{pg}: {sp!r}" for fid, fn, pg, sp in misses),
        )


class TestNoEgressDuringIngestion(unittest.TestCase):
    def test_extraction_attempts_no_outbound_connection(self):
        """SC-6 / loopback-only: ingestion must make zero network egress.

        PyMuPDF is a local C library and needs no network. We prove the code path
        attempts no outbound connection by failing socket.connect for the duration
        of a full 6-PDF extraction: any attempt would raise here.
        """
        import socket

        original_connect = socket.socket.connect

        def blocked_connect(self, *args, **kwargs):
            raise AssertionError(f"unexpected network egress to {args!r}")

        socket.socket.connect = blocked_connect
        try:
            total = 0
            for pdf in sorted(PDF_DIR.glob("*.pdf")):
                total += len(extract_pages(pdf))
            self.assertGreater(total, 0)
        finally:
            socket.socket.connect = original_connect


if __name__ == "__main__":
    unittest.main(verbosity=2)
