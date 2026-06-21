"""Task 6 proof (server contract): /chat returns everything the client-side rich
formatter needs — answer_text plus structured, chunk-derived citations with
filename/page/span/char_start/char_end (and doc_id for the highlight link). The actual
markdown/chip/Sources rendering is client-side JS, verified by the documented manual
visual check (and the final browser smoke). Temp KB only."""

import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

PIPELINE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PIPELINE_DIR))
import catalog  # noqa: E402
import routes_kb  # noqa: E402
import kb_ingest  # noqa: E402
import api  # noqa: E402

client = TestClient(api.app)


class TestAnswerFormatContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls._cat, catalog.DEFAULT_DB = catalog.DEFAULT_DB, cls.tmp / "cat.db"
        cls._db, routes_kb.KB_DB = routes_kb.KB_DB, cls.tmp / ".lancedb_kb"
        catalog.create_matter("Fmt Matter")
        p = cls.tmp / "fees.txt"
        p.write_text("SYNTHETIC. The arbitration fee is $2,750 per filing.", encoding="utf-8")
        d = catalog.add_document("fmt-matter", p)
        kb_ingest.ingest_document(d["id"], p, "fmt-matter", db_path=routes_kb.KB_DB,
                                  catalog_db=catalog.DEFAULT_DB)

    @classmethod
    def tearDownClass(cls):
        catalog.DEFAULT_DB = cls._cat
        routes_kb.KB_DB = cls._db

    def test_chat_carries_fields_the_formatter_needs(self):
        body = client.post("/chat", json={"question": "What is the arbitration fee?",
                                          "matter": "fmt-matter"}).json()
        self.assertIsInstance(body["answer_text"], str)
        self.assertTrue(body["citations"])
        c = body["citations"][0]
        for field in ("filename", "page", "span", "char_start", "char_end", "doc_id"):
            self.assertIn(field, c, f"citation missing {field} (formatter needs it)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
