"""T-TBL chunking + the keystone never-false-accept proof for TABLE chunks.

A table chunk's verbatim-span semantics (D-19/D-38): the chunk's ``text`` IS its Markdown
and ``char_start/char_end`` index into that Markdown (self-relative), so the existing
mechanical verifier checks a cited value by substring-overlap against the table chunk's own
text — no PyMuPDF page offsets are mixed in (offset-routing, D-51). The hard proof: a real
cell value verifies; a fabricated cell value is rejected with zero citations and surfaced.
Large tables split into multiple chunks, each repeating the header row.
"""

import sys
import tempfile
import unittest
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PIPELINE_DIR))

import build_table_corpus as btc  # noqa: E402
import table_extract  # noqa: E402
import table_ingest  # noqa: E402  (module under test)
from verifier import verify_answer  # noqa: E402


class TestTableChunking(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        pdf = btc.build_fee_schedule_exhibit(cls.tmp / "exhibit.pdf")
        cls.tables = table_extract.extract_tables(pdf)
        cls.chunks = table_ingest.chunk_tables(cls.tables, "tables-demo", "exhibit.pdf")

    def test_one_markdown_chunk_for_the_small_table(self):
        self.assertEqual(len(self.chunks), 1)
        c = self.chunks[0]
        self.assertEqual(c["source_filename"], "exhibit.pdf")
        self.assertEqual(c["matter"], "tables-demo")
        self.assertEqual(c["page_number"], btc.TABLE_PAGE)
        self.assertTrue(c["section"].startswith("[TABLE]"), "table chunk not tagged")

    def test_offsets_are_self_relative_into_markdown(self):
        c = self.chunks[0]
        self.assertEqual(c["char_start"], 0)
        self.assertEqual(c["char_end"], len(c["text"]))
        self.assertEqual(c["text"][c["char_start"]:c["char_end"]], c["text"])
        # the embedding text carries the markdown (so retrieval can hit a value)
        self.assertIn("$132,300", c["embedding_text"])

    def _grounding(self):
        c = self.chunks[0]
        return [{"chunk_id": "C1", "source_filename": c["source_filename"],
                 "page_number": c["page_number"], "char_start": c["char_start"],
                 "char_end": c["char_end"], "text": c["text"]}]

    def test_real_cell_value_verifies(self):
        answer = ('The 2026 annual license fee is $132,300 '
                  '[document: exhibit.pdf, page: 2, chunk: C1, span: "$132,300"].')
        verdict = verify_answer(answer, self._grounding())
        self.assertEqual(len(verdict["citations"]), 1, verdict)
        cite = verdict["citations"][0]
        self.assertEqual(cite["page"], 2)
        self.assertEqual(cite["filename"], "exhibit.pdf")
        self.assertEqual(cite["span"], "$132,300")

    def test_fabricated_cell_value_is_rejected_zero_citations(self):
        # $999,999 is NOWHERE in the table -> the verifier must reject it and surface
        # the rejection (never-false-accept for table chunks).
        answer = ('The 2026 annual license fee is $999,999 '
                  '[document: exhibit.pdf, page: 2, chunk: C1, span: "$999,999"].')
        verdict = verify_answer(answer, self._grounding())
        self.assertEqual(verdict["citations"], [], "fabricated table value accepted!")
        self.assertTrue(verdict["rejected_claims"], "rejection not surfaced")

    def test_large_table_splits_repeating_header(self):
        header = "| Year | Fee |"
        sep = "|------|-----|"
        rows = [f"| 20{i:02d} | ${i*1000:,} |" for i in range(60)]
        big = "\n".join([header, sep, *rows])
        tables = [{"source_filename": "big.pdf", "page_number": 4, "bbox": None,
                   "markdown": big}]
        chunks = table_ingest.chunk_tables(tables, "m", "big.pdf", max_chars=400)
        self.assertGreater(len(chunks), 1, "large table was not split")
        for c in chunks:
            self.assertTrue(c["text"].startswith(header), "split chunk missing header row")
            self.assertEqual(c["char_end"], len(c["text"]))
        # every data row is present across the pieces (no row dropped)
        joined = "\n".join(c["text"] for c in chunks)
        for r in rows:
            self.assertIn(r, joined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
