"""M2-2 chunking proof: page/section-aware chunks with SAC, verified vs ground truth.

For each of the 63 present-fact manifest records, asserts the verbatim_span:
  (a) is contained in exactly one chunk,
  (b) that chunk's page_number == the manifest page_number,
  (c) char_start..char_end bound the span's location in the M2-1 page text.
Section is sanity-checked against the manifest (mismatches reported, not failed —
Docling/heading granularity may differ). Scope: chunking only (no embed/DB/LLM).

Offsets/pages come from M2-1's authoritative per-page text; Docling supplies only
the section-detection signal. char offsets are relative to the chunk's PAGE text.
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
from chunking import chunk_corpus  # noqa: E402

REQUIRED_KEYS = {
    "source_filename", "matter", "document_type", "page_number",
    "section", "char_start", "char_end", "text", "embedding_text",
    "section_detected_by_docling",
}


def _load_present_facts():
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


def _norm_map(text):
    """Normalize PDF layout artifacts AND keep a map back to raw char offsets.

    Drops the soft-wrap newline in a hyphenated compound (keeps the hyphen),
    collapses whitespace runs to one space. omap[i] = raw index of normalized
    char i. Mirrors M2-1's normalization so a manifest span can be located on its
    page and translated back to raw offsets (the M2-6 offset substrate).
    """
    out, omap, i, n = [], [], 0, len(text)
    while i < n:
        c = text[i]
        if c == "-" and i + 1 < n and text[i + 1] == "\n":
            out.append("-"); omap.append(i); i += 2; continue
        if c.isspace():
            j = i
            while j < n and text[j].isspace():
                j += 1
            out.append(" "); omap.append(i); i = j; continue
        out.append(c); omap.append(i); i += 1
    return "".join(out), omap


def _locate(page_text, span):
    """Raw [start, end) of span in page_text, or None. Whitespace/hyphen aware."""
    npage, omap = _norm_map(page_text)
    nspan, _ = _norm_map(span)
    k = npage.find(nspan)
    if k < 0:
        return None
    return omap[k], omap[k + len(nspan) - 1] + 1


def _normalize(text):
    return re.sub(r"\s+", " ", re.sub(r"-\n", "-", text)).strip()


class ChunkingFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chunks = chunk_corpus(PDF_DIR, MANIFEST)
        cls.pages = {
            pdf.name: {r["page_number"]: r["page_text"] for r in extract_pages(pdf)}
            for pdf in PDF_DIR.glob("*.pdf")
        }
        cls.facts = _load_present_facts()


class TestChunkStructure(ChunkingFixture):
    def test_chunks_have_required_metadata_and_valid_nonoverlapping_ranges(self):
        self.assertGreater(len(self.chunks), 0)
        by_page = {}
        for c in self.chunks:
            self.assertEqual(set(c.keys()), REQUIRED_KEYS, "chunk metadata keys")
            pt = self.pages[c["source_filename"]][c["page_number"]]
            self.assertTrue(0 <= c["char_start"] < c["char_end"] <= len(pt))
            self.assertEqual(c["text"], pt[c["char_start"]:c["char_end"]])
            by_page.setdefault((c["source_filename"], c["page_number"]), []).append(c)
        # within a (file, page), chunk ranges must not overlap
        for key, cs in by_page.items():
            cs = sorted(cs, key=lambda c: c["char_start"])
            for a, b in zip(cs, cs[1:]):
                self.assertLessEqual(a["char_end"], b["char_start"], f"overlap in {key}")


class TestSpanResolvesToExactlyOneChunk(ChunkingFixture):
    def test_every_present_fact_span_in_exactly_one_chunk_right_page_and_offsets(self):
        misses = []
        for fact in self.facts:
            fname, page, span = fact["filename"], fact["page_number"], fact["verbatim_span"]
            loc = _locate(self.pages[fname][page], span)
            if loc is None:
                misses.append((fact["fact_id"], "span-not-locatable-in-page"))
                continue
            s, e = loc
            holding = [
                c for c in self.chunks
                if c["source_filename"] == fname
                and c["page_number"] == page
                and c["char_start"] <= s and e <= c["char_end"]
            ]
            if len(holding) != 1:
                misses.append((fact["fact_id"], f"{len(holding)} chunks bound the span (want 1)"))
                continue
            if _normalize(span) not in _normalize(holding[0]["text"]):
                misses.append((fact["fact_id"], "chunk text does not contain span"))
        self.assertEqual(
            misses, [],
            "span/page/offset failures:\n" + "\n".join(f"  {fid}: {why}" for fid, why in misses),
        )


class TestSACDeterministic(ChunkingFixture):
    def test_sac_prefix_is_deterministic_and_carries_matter(self):
        again = chunk_corpus(PDF_DIR, MANIFEST)
        self.assertEqual(
            [c["embedding_text"] for c in self.chunks],
            [c["embedding_text"] for c in again],
            "SAC embedding text must be deterministic across runs",
        )
        for c in self.chunks:
            self.assertTrue(c["embedding_text"].startswith("[Matter: "))
            self.assertIn(c["matter"], c["embedding_text"])
            self.assertIn(c["text"], c["embedding_text"])


class TestSectionMatchRateReport(ChunkingFixture):
    def test_report_section_match_rate_against_manifest(self):
        # Informational only (D-note: Docling/heading granularity may differ).
        graded = matched = 0
        for fact in self.facts:
            if not fact.get("section"):
                continue
            loc = _locate(self.pages[fact["filename"]][fact["page_number"]], fact["verbatim_span"])
            if loc is None:
                continue
            s, e = loc
            holding = [
                c for c in self.chunks
                if c["source_filename"] == fact["filename"]
                and c["page_number"] == fact["page_number"]
                and c["char_start"] <= s and e <= c["char_end"]
            ]
            if not holding:
                continue
            graded += 1
            man = _normalize(fact["section"]).lower()
            chunk_sec = _normalize(holding[0]["section"]).lower()
            key = man.split("›")[-1].strip().split()[-1] if man else ""
            if key and key in chunk_sec:
                matched += 1
        rate = (matched / graded * 100) if graded else 0.0
        print(f"\n[section match] {matched}/{graded} manifest sections "
              f"echoed in chunk breadcrumb ({rate:.0f}%) — informational")
        self.assertGreater(graded, 0, "expected some facts to carry a manifest section")


class TestNoEgressDuringChunking(ChunkingFixture):
    def test_chunking_with_cached_structure_makes_no_outbound_connection(self):
        import socket
        original = socket.socket.connect

        def blocked(self, *a, **k):
            raise AssertionError(f"unexpected egress to {a!r}")

        socket.socket.connect = blocked
        try:
            # Structure cache is warm after setUpClass; re-chunking must not egress.
            chunks = chunk_corpus(PDF_DIR, MANIFEST)
            self.assertGreater(len(chunks), 0)
        finally:
            socket.socket.connect = original


if __name__ == "__main__":
    unittest.main(verbosity=2)
