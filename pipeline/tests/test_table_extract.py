"""T-TBL extraction proof: Docling TableFormer pulls a real table to Markdown with the
correct page + a bbox, and does NOT sweep in page-1 prose (page attribution).

Runs Docling offline (the TableFormer model is already cached; the one-time fetch is gated
by DOCLING_ALLOW_MODEL_FETCH). The model revision is pinned (D-11 style). Synthetic doc
only; the eval baseline is never touched.
"""

import sys
import tempfile
import unittest
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PIPELINE_DIR))

import build_table_corpus as btc  # noqa: E402
import table_extract  # noqa: E402  (module under test)


class TestTableExtraction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.pdf = btc.build_fee_schedule_exhibit(cls.tmp / "exhibit.pdf")
        cls.tables = table_extract.extract_tables(cls.pdf)

    def test_one_table_extracted_with_filename(self):
        self.assertEqual(len(self.tables), 1, "expected exactly one table")
        self.assertEqual(self.tables[0]["source_filename"], "exhibit.pdf")

    def test_table_on_correct_page(self):
        self.assertEqual(self.tables[0]["page_number"], btc.TABLE_PAGE)

    def test_known_cells_land_in_markdown(self):
        md = self.tables[0]["markdown"]
        for value, desc in btc.GROUND_TRUTH.items():
            self.assertIn(value, md, f"missing {desc} ({value}) from table markdown")

    def test_page1_prose_not_in_table(self):
        # The page-1-only marker must NOT appear in the page-2 table markdown — the
        # extractor attributes cells to their page and does not vacuum in prose.
        self.assertNotIn(btc.PAGE1_ONLY_MARKER, self.tables[0]["markdown"])

    def test_bbox_present_with_four_coords(self):
        bbox = self.tables[0]["bbox"]
        for k in ("l", "t", "r", "b"):
            self.assertIn(k, bbox)
            self.assertIsInstance(bbox[k], (int, float))

    def test_model_revision_is_pinned(self):
        self.assertTrue(table_extract.TABLEFORMER_REVISION)
        self.assertRegex(table_extract.TABLEFORMER_REVISION, r"^[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main(verbosity=2)
