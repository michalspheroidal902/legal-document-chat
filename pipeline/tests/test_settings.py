"""Task 7 proof: read-only system/status for the Settings view + privacy badge.

GET /settings/status reports the pinned models, the loopback bind, loopback-only egress
posture (DERIVED from the real Ollama URL, not a blind hardcode), and integer KB store
counts — and exposes NO secret or filesystem path."""

import json
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

PIPELINE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PIPELINE_DIR))
import api  # noqa: E402

client = TestClient(api.app)


class TestSettingsStatus(unittest.TestCase):
    def test_status_is_truthful(self):
        s = client.get("/settings/status").json()
        self.assertEqual(s["bind"], "127.0.0.1")
        self.assertEqual(s["egress"], "loopback-only")
        self.assertEqual(s["models"]["chat"], "qwen3:14b")
        self.assertEqual(s["models"]["embed"], "bge-m3")
        self.assertIn("127.0.0.1:11434", s["ollama"])
        self.assertIsInstance(s["stores"]["kb_docs"], int)
        self.assertIsInstance(s["stores"]["kb_chunks"], int)

    def test_status_leaks_no_secret_or_path(self):
        blob = json.dumps(client.get("/settings/status").json())
        self.assertNotIn("/Users/", blob)
        self.assertNotIn(".db", blob)
        self.assertNotIn("key", blob.lower())
        self.assertNotIn(".lancedb", blob)


if __name__ == "__main__":
    unittest.main(verbosity=2)
