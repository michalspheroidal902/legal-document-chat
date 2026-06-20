"""M2-1 — PyMuPDF page-accurate ingestion.

Recovers per-page text with correct 1-based page numbers from born-digital PDFs.
This closes the page-metadata gap of the M1 turnkey stack (D-29) at the ingestion
layer. Text is returned RAW (verbatim, no normalization) so downstream stages can
compute character offsets for mechanical span-level citation verification (M2-6).

Scope (M2-1): page-accurate text extraction only. No OCR (born-digital corpus),
no chunking, embeddings, vector DB, reranker, LLM, or HTTP surface.
"""

from pathlib import Path

import fitz  # PyMuPDF


def extract_pages(pdf_path):
    """Extract text from a born-digital PDF, organized by page.

    Returns a list of dicts (one per physical page, in order):
        {"source_filename": str, "page_number": int (1-based), "page_text": str}
    """
    pdf_path = Path(pdf_path)
    records = []
    with fitz.open(pdf_path) as doc:
        for index, page in enumerate(doc):
            records.append(
                {
                    "source_filename": pdf_path.name,
                    "page_number": index + 1,  # 1-based, matches the manifest
                    "page_text": page.get_text(),
                }
            )
    return records
