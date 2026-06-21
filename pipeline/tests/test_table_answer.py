"""T-TBL embed + answer + API + UI proof (end-to-end, loopback Ollama).

Ingest the synthetic fee-schedule exhibit through the EXISTING Document Hub path
(kb_ingest.ingest_document), which now also runs the table pass on table-bearing PDFs and
appends Docling table chunks to the KB store. Then, over the existing /chat API + verifier:

- a table-value question retrieves the table chunk and returns a span-verified citation on
  the correct file + page (the capability prose-only ingestion can't deliver);
- a fabricated table value never comes back as a verified citation (never-false-accept,
  end to end);
- the cited page renders in the existing source viewer (/kb/highlight -> PNG) — the table
  citation is surfaced in the same viewer used for prose.

Writes ONLY to a temp KB store; the eval baseline is never touched.
"""

import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

PIPELINE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PIPELINE_DIR))
import build_table_corpus as btc  # noqa: E402
import catalog  # noqa: E402
import kb_ingest  # noqa: E402
import routes_kb  # noqa: E402
import api  # noqa: E402
from embed_store import open_table  # noqa: E402

client = TestClient(api.app)


class TestTableAnswerEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls._cat, catalog.DEFAULT_DB = catalog.DEFAULT_DB, cls.tmp / "cat.db"
        cls._db, routes_kb.KB_DB = routes_kb.KB_DB, cls.tmp / ".lancedb_kb"
        catalog.create_matter("Tables Demo")  # slug -> tables-demo
        # the exhibit must live where /kb/highlight can read it: under documents/kb/<slug>
        kb_dir = routes_kb.KB_DOCS / "tables-demo"
        kb_dir.mkdir(parents=True, exist_ok=True)
        cls.pdf = btc.build_fee_schedule_exhibit(kb_dir / "exhibit.pdf")
        cls.doc = catalog.add_document("tables-demo", cls.pdf, status="parsing")
        cls.status = kb_ingest.ingest_document(
            cls.doc["id"], cls.pdf, "tables-demo",
            db_path=routes_kb.KB_DB, catalog_db=catalog.DEFAULT_DB)

    @classmethod
    def tearDownClass(cls):
        catalog.DEFAULT_DB = cls._cat
        routes_kb.KB_DB = cls._db
        try:
            (routes_kb.KB_DOCS / "tables-demo" / "exhibit.pdf").unlink()
        except OSError:
            pass

    def test_table_chunk_indexed(self):
        self.assertEqual(self.status, "ready", "ingest did not complete")
        rows = open_table(str(routes_kb.KB_DB)).to_arrow().to_pylist()
        table_rows = [r for r in rows if r["section"].startswith("[TABLE]")]
        self.assertTrue(table_rows, "no table chunk was indexed")
        self.assertTrue(any("$132,300" in r["text"] for r in table_rows))
        self.assertTrue(all(r["page_number"] == btc.TABLE_PAGE for r in table_rows))

    def test_table_value_question_is_span_verified(self):
        r = client.post("/chat", json={
            "question": "In Exhibit A, what is the 2026 annual license fee?",
            "matter": "tables-demo"})
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertIn("$132,300", body["answer_text"], body["answer_text"])
        cites = body["citations"]
        self.assertTrue(cites, f"no citation: {body['answer_text']!r}")
        self.assertTrue(any(c["filename"] == "exhibit.pdf" and c["page"] == btc.TABLE_PAGE
                            for c in cites), cites)

    def test_fabricated_table_value_never_verified(self):
        # Ask about a value that is NOT in the table. The system must never return a
        # verified citation asserting $999,999 (never-false-accept, end to end).
        r = client.post("/chat", json={
            "question": "Does Exhibit A list an annual license fee of $999,999?",
            "matter": "tables-demo"})
        body = r.json()
        for c in body["citations"]:
            self.assertNotIn("999,999", c.get("span", ""), "fabricated value verified!")

    def test_cited_table_page_renders_in_source_viewer(self):
        r = client.post("/chat", json={
            "question": "In Exhibit A, what is the 2027 total annual fee?",
            "matter": "tables-demo"})
        cites = [c for c in r.json()["citations"] if c.get("doc_id")]
        self.assertTrue(cites, "no doc-linked citation to view")
        c = cites[0]
        h = client.get(f"/kb/highlight/{c['doc_id']}?page={c['page']}&span=$166,698")
        self.assertEqual(h.status_code, 200)
        self.assertEqual(h.headers["content-type"], "image/png")
        self.assertEqual(h.content[:8], b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
