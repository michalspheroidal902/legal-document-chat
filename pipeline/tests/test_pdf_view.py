"""Task 5 proof: retrieved-page thumbnails + cited-span highlight (PyMuPDF).

render_page_png -> a PNG thumbnail; find_span_rects locates a verbatim span via
page.search_for (non-empty for a real span); highlight_span_png returns a PNG and does
not crash when the span is absent. The /kb/thumb + /kb/highlight routes are path-locked
to documents/kb/ and NEVER modify the managed file on disk."""

import sys
import tempfile
import unittest
from pathlib import Path

import fitz
from fastapi.testclient import TestClient

PIPELINE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PIPELINE_DIR))
import pdf_view  # noqa: E402
import catalog  # noqa: E402
import routes_kb  # noqa: E402
import api  # noqa: E402

client = TestClient(api.app)
SPAN = "1147 Aldergrove Avenue"
PAGE_TEXT = ("SYNTHETIC — NOT REAL\n\nSECTION 1. The premises are at "
             "1147 Aldergrove Avenue, Unit 3B.\n\nThe monthly rent is $4,200.")


def _make_pdf(path):
    with fitz.open() as d:
        pg = d.new_page(width=612, height=792)
        pg.insert_textbox(fitz.Rect(72, 72, 540, 720), PAGE_TEXT, fontsize=13, fontname="helv")
        d.save(path)


class TestPdfViewUnit(unittest.TestCase):
    def setUp(self):
        self.pdf = Path(tempfile.mkdtemp()) / "lease.pdf"
        _make_pdf(self.pdf)

    def test_render_page_png_returns_png_bytes(self):
        png = pdf_view.render_page_png(self.pdf, 1)
        self.assertTrue(png.startswith(b"\x89PNG"))
        self.assertGreater(len(png), 500)

    def test_find_span_rects_locates_real_span(self):
        rects = pdf_view.find_span_rects(self.pdf, 1, SPAN)
        self.assertTrue(rects, "verbatim span not located via search_for")
        r = rects[0]
        self.assertGreater(r.width, 0)
        self.assertGreater(r.height, 0)

    def test_highlight_span_png_returns_png_and_does_not_mutate_file(self):
        before = self.pdf.read_bytes()
        png = pdf_view.highlight_span_png(self.pdf, 1, SPAN)
        self.assertTrue(png.startswith(b"\x89PNG"))
        self.assertEqual(self.pdf.read_bytes(), before, "highlight modified the managed file")

    def test_absent_span_returns_plain_page_no_crash(self):
        png = pdf_view.highlight_span_png(self.pdf, 1, "this phrase is not on the page at all")
        self.assertTrue(png.startswith(b"\x89PNG"))


class TestPdfViewRoutes(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._cat, catalog.DEFAULT_DB = catalog.DEFAULT_DB, self.tmp / "cat.db"
        self._docs, routes_kb.KB_DOCS = routes_kb.KB_DOCS, self.tmp / "kb"
        catalog.create_matter("Vis Matter")
        d = (routes_kb.KB_DOCS / "vis-matter")
        d.mkdir(parents=True)
        self.pdf = d / "lease.pdf"
        _make_pdf(self.pdf)
        self.doc = catalog.add_document("vis-matter", self.pdf)

    def tearDown(self):
        catalog.DEFAULT_DB = self._cat
        routes_kb.KB_DOCS = self._docs

    def test_thumb_and_highlight_return_png(self):
        t = client.get(f"/kb/thumb/{self.doc['id']}?page=1")
        self.assertEqual(t.status_code, 200)
        self.assertEqual(t.headers["content-type"], "image/png")
        h = client.get(f"/kb/highlight/{self.doc['id']}?page=1&span={SPAN}")
        self.assertEqual(h.status_code, 200)
        self.assertTrue(h.content.startswith(b"\x89PNG"))

    def test_routes_path_locked_unknown_doc_404(self):
        self.assertEqual(client.get("/kb/thumb/99999?page=1").status_code, 404)

    def test_route_rejects_doc_outside_kb_dir(self):
        outside = self.tmp / "outside.pdf"
        _make_pdf(outside)
        bad = catalog.add_document("vis-matter", outside)  # stored_path outside KB_DOCS
        self.assertEqual(client.get(f"/kb/thumb/{bad['id']}?page=1").status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
