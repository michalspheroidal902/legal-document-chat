"""Task 2 proof: SQLite matters catalog + /matters routes (the D-18 spine).

Slugs are path-safe/validated (no injection); duplicates and empty names rejected;
list_matters carries doc_count. Catalog DB is overridable for tests (temp DB)."""

import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

PIPELINE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PIPELINE_DIR))
import catalog  # noqa: E402
import api  # noqa: E402

client = TestClient(api.app)


class TestCatalogMatters(unittest.TestCase):
    def setUp(self):
        self.db = Path(tempfile.mkdtemp()) / "cat.db"

    def test_create_matter_returns_path_safe_slug(self):
        m = catalog.create_matter("Pemberton Logistics", db_path=self.db)
        self.assertEqual(m["slug"], "pemberton-logistics")
        self.assertNotIn("/", m["slug"])
        self.assertNotIn("..", m["slug"])
        self.assertNotIn(" ", m["slug"])

    def test_slug_strips_unsafe_characters(self):
        m = catalog.create_matter("../../etc/passwd & Co.", db_path=self.db)
        self.assertNotIn("/", m["slug"])
        self.assertNotIn("..", m["slug"])
        self.assertNotIn("\\", m["slug"])
        self.assertTrue(m["slug"])

    def test_duplicate_display_name_rejected(self):
        catalog.create_matter("Acme Corp", db_path=self.db)
        with self.assertRaises(ValueError):
            catalog.create_matter("Acme Corp", db_path=self.db)

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            catalog.create_matter("   ", db_path=self.db)
        with self.assertRaises(ValueError):
            catalog.create_matter("///", db_path=self.db)  # slugs to empty

    def test_list_matters_includes_doc_count_zero(self):
        catalog.create_matter("Beta Case", db_path=self.db)
        ms = catalog.list_matters(db_path=self.db)
        self.assertTrue(any(m["slug"] == "beta-case" and m["doc_count"] == 0 for m in ms))

    def test_get_matter_by_slug(self):
        catalog.create_matter("Gamma Holdings", db_path=self.db)
        self.assertIsNotNone(catalog.get_matter("gamma-holdings", db_path=self.db))
        self.assertIsNone(catalog.get_matter("no-such-matter", db_path=self.db))


class TestMattersRoutes(unittest.TestCase):
    def setUp(self):
        self._saved = catalog.DEFAULT_DB
        catalog.DEFAULT_DB = Path(tempfile.mkdtemp()) / "routes_cat.db"

    def tearDown(self):
        catalog.DEFAULT_DB = self._saved

    def test_post_then_get_reflects_matter(self):
        r = client.post("/matters", json={"display_name": "Route Test Matter"})
        self.assertEqual(r.status_code, 200, r.text)
        slug = r.json()["slug"]
        g = client.get("/matters")
        self.assertEqual(g.status_code, 200)
        self.assertTrue(any(m["slug"] == slug for m in g.json()["matters"]))

    def test_empty_name_returns_400(self):
        self.assertEqual(client.post("/matters", json={"display_name": ""}).status_code, 400)

    def test_duplicate_returns_400(self):
        client.post("/matters", json={"display_name": "Dup Matter"})
        self.assertEqual(client.post("/matters", json={"display_name": "Dup Matter"}).status_code, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
