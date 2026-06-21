"""Task 1 proof: multi-format ingestion orchestrator (CE_PLAN §8). DOCX/TXT/MD + PDF
extraction; SHA-256 idempotent re-ingest; per-file JSONL report; fail-loud quarantine
(unreadable/unsupported -> failed/ + .error.txt); ocr_failed -> needs_review (not
indexed as authoritative). Synthetic-only, zero network. unittest (not pytest)."""

import json
import socket
import sys
import tempfile
import unittest
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PIPELINE_DIR))
from extractors import extract  # noqa: E402
from ingest_pipeline import ingest_dir  # noqa: E402


class TestExtractors(unittest.TestCase):
    def test_txt_extracts_single_page(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "memo.txt"
            p.write_text("SYNTHETIC — Retainer is $5,000.", encoding="utf-8")
            pages = extract(p)
            self.assertEqual(len(pages), 1)
            self.assertEqual(pages[0]["page_number"], 1)
            self.assertIn("$5,000", pages[0]["page_text"])
            self.assertEqual(pages[0]["source"], "txt")
            self.assertFalse(pages[0]["ocr_failed"])

    def test_docx_extracts_single_page(self):
        from docx import Document
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "agreement.docx"
            doc = Document()
            doc.add_paragraph("SYNTHETIC — Governing law is the State of Delaware.")
            doc.save(p)
            pages = extract(p)
            self.assertEqual(len(pages), 1)
            self.assertEqual(pages[0]["page_number"], 1)
            self.assertIn("Delaware", pages[0]["page_text"])
            self.assertEqual(pages[0]["source"], "docx")

    def test_normalized_record_shape(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "note.md"
            p.write_text("# SYNTHETIC\nClause 7 governs renewal.", encoding="utf-8")
            pages = extract(p)
            self.assertEqual(set(pages[0].keys()),
                             {"source_filename", "page_number", "page_text", "source", "ocr_failed"})

    def test_unsupported_suffix_raises(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "weird.xyz"
            p.write_text("nope", encoding="utf-8")
            with self.assertRaises(ValueError):
                extract(p)


class TestIngestPipeline(unittest.TestCase):
    def test_report_idempotent_and_quarantine(self):
        with tempfile.TemporaryDirectory() as d:
            src, q = Path(d) / "in", Path(d) / "failed"
            src.mkdir()
            q.mkdir()
            (src / "a.txt").write_text("SYNTHETIC alpha clause", encoding="utf-8")
            (src / "b.bin").write_bytes(b"\x00\x01not a document")
            report = Path(d) / "report.jsonl"
            r1 = ingest_dir(src, report, q)
            self.assertEqual(len(r1["ingested"]), 1)
            self.assertEqual(len(r1["quarantined"]), 1)
            self.assertTrue((q / "b.bin.error.txt").exists())
            # per-file JSONL report exists, one record per file
            recs = [json.loads(l) for l in report.read_text().splitlines() if l.strip()]
            self.assertEqual(len(recs), 2)
            self.assertEqual({r["status"] for r in recs}, {"ingested", "quarantined"})
            # idempotent: same checksums -> all duplicate, nothing re-ingested
            r2 = ingest_dir(src, report, q, seen_checksums={x["checksum"] for x in r1["ingested"]})
            self.assertEqual(len(r2["ingested"]), 0)
            self.assertEqual(len(r2["skipped_duplicate"]), 1)

    def test_ocr_failed_routes_to_needs_review(self):
        # A page whose OCR failed (low confidence/blank) must mark the doc needs_review,
        # not authoritative ingested. Drive via a blank image-only PDF (fail-loud OCR).
        import fitz
        with tempfile.TemporaryDirectory() as d:
            src, q = Path(d) / "in", Path(d) / "failed"
            src.mkdir()
            q.mkdir()
            blank = src / "blank_scan.pdf"
            with fitz.open() as doc:
                page = doc.new_page(width=612, height=792)
                pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 1000, 1294))
                pix.clear_with(255)
                page.insert_image(fitz.Rect(0, 0, 612, 792), stream=pix.tobytes("png"))
                doc.save(blank)
            r = ingest_dir(src, Path(d) / "report.jsonl", q)
            self.assertEqual(len(r["needs_review"]), 1)
            self.assertEqual(len(r["ingested"]), 0)


class TestIngestNoEgress(unittest.TestCase):
    def test_ingest_dir_makes_no_outbound_connection(self):
        original = socket.socket.connect

        def blocked(self, *a, **k):
            raise AssertionError(f"unexpected network egress to {a!r}")

        with tempfile.TemporaryDirectory() as d:
            src, q = Path(d) / "in", Path(d) / "failed"
            src.mkdir()
            q.mkdir()
            (src / "a.txt").write_text("SYNTHETIC local only", encoding="utf-8")
            socket.socket.connect = blocked
            try:
                r = ingest_dir(src, Path(d) / "report.jsonl", q)
                self.assertEqual(len(r["ingested"]), 1)
            finally:
                socket.socket.connect = original


if __name__ == "__main__":
    unittest.main(verbosity=2)
