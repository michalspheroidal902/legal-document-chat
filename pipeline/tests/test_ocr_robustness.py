"""Task 4 proof: OCR robustness + routing fixes (SC-2 hardening, §8).

- Degraded scans (150-DPI + skew + noise + JPEG) still recover known spans on their
  correct pages above the confidence floor; a heavily-degraded page is FLAGGED
  (ocr_failed), not silently trusted.
- Routing fix 1 (sparse-but-digital): a page with a real but tiny text layer and NO
  full-page image stays on the PyMuPDF path (NOT misrouted to OCR).
- Routing fix 2 (mixed): a page with a real text layer AND a large embedded scanned
  image gets the embedded text OCR-merged (not dropped).
Synthetic degradations only — real-scan validation remains M6. Local, zero network."""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

import fitz

PIPELINE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = PIPELINE_DIR.parent
PDF_DIR = REPO_ROOT / "documents" / "synthetic_corpus" / "pdf"
MANIFEST = REPO_ROOT / "eval" / "golden_manifest.jsonl"

sys.path.insert(0, str(PIPELINE_DIR))
from ingestion import extract_pages, extract_pages_ocr  # noqa: E402
from make_scans import degrade_to_scanned_pdf  # noqa: E402

DOC = "greenfield_castellano_lease.pdf"
_SHARED = {}


def setUpModule():
    tmp = tempfile.mkdtemp()
    deg = Path(tmp) / DOC
    degrade_to_scanned_pdf(PDF_DIR / DOC, deg, dpi=150, rotate_deg=1.2, noise=0.04, jpeg_quality=60)
    _SHARED["deg_pages"] = extract_pages_ocr(deg)


def _norm(t):
    return re.sub(r"\s+", " ", re.sub(r"-\n", "-", t)).strip().lower()


def _coverage(haystack, span):
    ptoks = set(_norm(haystack).split())
    stoks = _norm(span).split()
    return sum(1 for w in stoks if w in ptoks) / len(stoks) if stoks else 0.0


def _present_spans(filename):
    return [json.loads(l) for l in MANIFEST.read_text().splitlines()
            if l.strip() and json.loads(l)["filename"] == filename
            and not json.loads(l)["expected_absent_topics"]]


class TestDegradedScanRecovers(unittest.TestCase):
    def test_degraded_pages_route_ocr_and_recover_spans_above_floor(self):
        pages = _SHARED["deg_pages"]
        self.assertTrue(pages and all(p["source"] == "tesseract" for p in pages))
        readable = [p for p in pages if not p["ocr_failed"]]
        self.assertTrue(readable, "no readable degraded page")
        for p in readable:
            self.assertGreaterEqual(p["ocr_confidence"], 50.0)  # above the floor
        by_page = {p["page_number"]: p["page_text"] for p in readable}
        spans = _present_spans(DOC)
        recovered = [s for s in spans if _coverage(by_page.get(s["page_number"], ""),
                                                   s["verbatim_span"]) >= 0.8]
        self.assertGreaterEqual(len(recovered), 3,
                                f"only {len(recovered)} spans recovered from degraded scan")


class TestHeavilyDegradedFlagged(unittest.TestCase):
    def test_heavy_noise_page_is_flagged_ocr_failed(self):
        with tempfile.TemporaryDirectory() as d:
            deg = Path(d) / DOC
            degrade_to_scanned_pdf(PDF_DIR / DOC, deg, dpi=80, rotate_deg=4.0,
                                   noise=0.7, jpeg_quality=15)
            pages = extract_pages_ocr(deg)
            self.assertTrue(
                any(p["ocr_failed"] for p in pages),
                f"expected >=1 flagged page; confidences={[p['ocr_confidence'] for p in pages]}",
            )


class TestSparseDigitalNotMisrouted(unittest.TestCase):
    def test_tiny_text_layer_no_image_stays_pymupdf(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sparse.pdf"
            with fitz.open() as doc:
                page = doc.new_page(width=612, height=792)
                page.insert_text((72, 100), "Exhibit A", fontsize=12)  # <20 chars, no image
                doc.save(p)
            pages = extract_pages_ocr(p)
            self.assertEqual(pages[0]["source"], "pymupdf")  # NOT routed to OCR
            self.assertFalse(pages[0]["ocr_failed"])
            self.assertIn("Exhibit A", pages[0]["page_text"])


class TestMixedPageOcrMerged(unittest.TestCase):
    def test_embedded_image_text_is_recovered(self):
        from PIL import Image, ImageDraw, ImageFont
        with tempfile.TemporaryDirectory() as d:
            # image aspect (0.9) matches the target rect aspect so it fills with no
            # letterbox AND no distortion (clean OCR); generous margin so nothing clips.
            img = Image.new("RGB", (1080, 1200), "white")
            font = ImageFont.load_default(size=56)
            ImageDraw.Draw(img).text((50, 560), "EMBEDDED SCANNED CLAUSE 12345", fill="black", font=font)
            imgp = Path(d) / "emb.png"
            img.save(imgp)
            p = Path(d) / "mixed.pdf"
            with fitz.open() as doc:
                page = doc.new_page(width=612, height=792)
                page.insert_textbox(fitz.Rect(72, 72, 540, 96),
                                    "VISIBLE TEXT LAYER: this page has a real text layer with many words.",
                                    fontsize=12)
                page.insert_image(fitz.Rect(36, 96, 576, 696), filename=str(imgp))  # 540x600, ~67% cover
                doc.save(p)
            pages = extract_pages_ocr(p)
            self.assertEqual(len(pages), 1)
            self.assertEqual(pages[0]["source"], "mixed")
            self.assertIn("VISIBLE TEXT LAYER", pages[0]["page_text"])  # text layer preserved
            self.assertIn("12345", pages[0]["page_text"])  # embedded image text OCR-merged


class TestBornDigitalStillByteIdentical(unittest.TestCase):
    def test_clean_born_digital_unchanged(self):
        # the routing fix must not regress the clean fast path
        base = extract_pages(PDF_DIR / DOC)
        routed = extract_pages_ocr(PDF_DIR / DOC)
        for b, r in zip(base, routed):
            self.assertEqual(r["source"], "pymupdf")
            self.assertEqual(r["page_text"], b["page_text"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
