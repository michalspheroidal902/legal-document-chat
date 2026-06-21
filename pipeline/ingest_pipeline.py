"""Task 1 — the CE_PLAN §8 ingestion orchestrator.

scan -> identify -> extract -> SHA-256 dedup -> per-file JSONL report -> fail-loud
quarantine. One responsibility: turn a directory of mixed documents into a per-file
pass/fail ledger, without indexing anything (embedding/indexing is T3).

Statuses (one per file, written to the JSONL report):
  ingested        — extracted clean; authoritative text recovered
  duplicate       — SHA-256 already seen (idempotent re-ingest)
  quarantined     — unreadable / unsupported / corrupt -> moved to quarantine_dir +
                    <name>.error.txt (fail-loud, §8)
  needs_review    — extracted, but >=1 page had ocr_failed=True (low-confidence OCR):
                    flagged, NOT indexed as authoritative garbage (§8 below-threshold)

Local-only: extraction touches the filesystem + (for scans) the local Tesseract binary.
No network. Synthetic documents only.
"""

import hashlib
import json
import shutil
from pathlib import Path

from extractors import extract


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _quarantine(path, quarantine_dir, reason):
    quarantine_dir = Path(quarantine_dir)
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    dest = quarantine_dir / path.name
    shutil.copy2(path, dest)
    (quarantine_dir / f"{path.name}.error.txt").write_text(
        f"quarantined: {path.name}\nreason: {reason}\n", encoding="utf-8"
    )


def ingest_dir(src_dir, report_path, quarantine_dir, seen_checksums=None):
    """Ingest every file under ``src_dir`` (non-recursive over files), writing a per-file
    JSONL report to ``report_path``. Returns a summary dict:
      {ingested, skipped_duplicate, quarantined, needs_review, report_path}
    ``seen_checksums`` (a set) makes re-ingest idempotent: a previously-seen SHA-256 is a
    duplicate. Fail-loud: any extraction error quarantines the file."""
    src_dir = Path(src_dir)
    report_path = Path(report_path)
    seen = set(seen_checksums or set())

    ingested, skipped_duplicate, quarantined, needs_review = [], [], [], []
    records = []

    for path in sorted(p for p in src_dir.iterdir() if p.is_file()):
        checksum = _sha256(path)
        ftype = path.suffix.lower().lstrip(".")

        if checksum in seen:
            skipped_duplicate.append({"file": path.name, "checksum": checksum})
            records.append({"filename": path.name, "sha256": checksum, "type": ftype,
                            "page_count": None, "status": "duplicate", "reason": "checksum seen"})
            continue

        try:
            pages = extract(path)
        except Exception as e:  # unreadable / unsupported / corrupt -> fail loud
            _quarantine(path, quarantine_dir, f"{type(e).__name__}: {e}")
            quarantined.append({"file": path.name, "reason": f"{type(e).__name__}: {e}"})
            records.append({"filename": path.name, "sha256": checksum, "type": ftype,
                            "page_count": None, "status": "quarantined",
                            "reason": f"{type(e).__name__}: {e}"})
            continue

        seen.add(checksum)
        if any(pg.get("ocr_failed") for pg in pages):
            failed_pages = [pg["page_number"] for pg in pages if pg.get("ocr_failed")]
            needs_review.append({"file": path.name, "checksum": checksum,
                                 "ocr_failed_pages": failed_pages})
            records.append({"filename": path.name, "sha256": checksum, "type": ftype,
                            "page_count": len(pages), "status": "needs_review",
                            "reason": f"low-confidence OCR on pages {failed_pages}"})
            continue

        ingested.append({"file": path.name, "checksum": checksum, "pages": pages})
        records.append({"filename": path.name, "sha256": checksum, "type": ftype,
                        "page_count": len(pages), "status": "ingested", "reason": None})

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    return {
        "ingested": ingested,
        "skipped_duplicate": skipped_duplicate,
        "quarantined": quarantined,
        "needs_review": needs_review,
        "report_path": str(report_path),
    }
