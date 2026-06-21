"""Task 1 — per-type text extraction, normalized to one page-record shape.

Dispatches on file suffix:
  .pdf        -> ingestion per-page routing (born-digital text layer vs OCR for scans)
  .docx       -> python-docx paragraphs (single page_number=1; DOCX has no fixed pages)
  .txt / .md  -> read_text (single page_number=1)
  anything else -> ValueError (the orchestrator quarantines it, fail-loud, §8)

Every record is normalized to:
  {source_filename, page_number, page_text, source, ocr_failed}
so the orchestrator and downstream chunking see one shape regardless of format. PDFs
preserve real page numbers; DOCX/TXT/MD are best-effort single-page (§8 step 5) — we do
NOT fake page splits.
"""

from pathlib import Path

from ingestion import extract_pages_ocr

_TEXT_SUFFIXES = {".txt", ".md"}


def _pdf(path):
    """Per-page route: born-digital pages use PyMuPDF text, image-only pages OCR.
    extract_pages_ocr already tags source ('pymupdf'|'tesseract') and ocr_failed."""
    out = []
    for r in extract_pages_ocr(path):
        out.append({
            "source_filename": r["source_filename"],
            "page_number": r["page_number"],
            "page_text": r["page_text"],
            "source": r["source"],
            "ocr_failed": r["ocr_failed"],
        })
    return out


def _docx(path):
    from docx import Document
    doc = Document(str(path))
    text = "\n".join(p.text for p in doc.paragraphs)
    return [{
        "source_filename": Path(path).name,
        "page_number": 1,  # DOCX has no fixed page model (§8 step 5)
        "page_text": text,
        "source": "docx",
        "ocr_failed": False,
    }]


def _text(path):
    return [{
        "source_filename": Path(path).name,
        "page_number": 1,
        "page_text": Path(path).read_text(encoding="utf-8"),
        "source": Path(path).suffix.lstrip(".").lower(),  # "txt" | "md"
        "ocr_failed": False,
    }]


def extract(path):
    """Extract normalized page records from a supported document. Raises ValueError on
    an unsupported suffix (so the orchestrator quarantines it)."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _pdf(path)
    if suffix == ".docx":
        return _docx(path)
    if suffix in _TEXT_SUFFIXES:
        return _text(path)
    raise ValueError(f"unsupported document type: {suffix!r} ({path.name})")
