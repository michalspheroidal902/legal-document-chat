"""T-TBL — Docling TableFormer table EXTRACTION (D-50/D-51).

Turn on Docling's table-structure model (`do_table_structure=True`) — already shipped in
our installed Docling — and pull each table to a Markdown grid carrying its page number
and bbox provenance. This is the EXTRACTION layer only: ``extract_tables(pdf)`` returns
per-table ``{source_filename, page_number, bbox, markdown}``. Chunking / embedding /
answering are downstream (table_ingest).

Offset-routing (D-51): this is the heavy Docling path, run ONLY on table-bearing docs.
The born-digital PROSE path (PyMuPDF, ingestion/chunking) is UNCHANGED — table chunks are
a separate, Docling-sourced chunk type whose offsets index their own Markdown (never mixed
with PyMuPDF page offsets on one chunk).

Air-gap (rule #4): by default the Docling models are served from the local HF cache with
the hub revision-check suppressed, so a conversion makes ZERO network egress. A fresh
machine performs the owner-approved one-time fetch by setting ``DOCLING_ALLOW_MODEL_FETCH=1``
for that run; afterwards it runs fully offline.

Model pin (D-11 style): the TableFormer weights live in ``docling-project/docling-models``,
pinned to ``TABLEFORMER_REVISION`` below — a revision change forces a table re-index.
"""

import os
from pathlib import Path

# docling-project/docling-models @ v2.3.0 (the snapshot cached on this machine; contains
# the TableFormer weights). Pinned D-11 style — a change forces table re-index.
TABLEFORMER_REVISION = "fc0f2d45e2218ea24bce5045f58a389aed16dc23"


def _bbox_dict(bbox):
    """JSON-serializable bbox from a Docling BoundingBox (page coordinates)."""
    return {
        "l": float(bbox.l), "t": float(bbox.t),
        "r": float(bbox.r), "b": float(bbox.b),
        "coord_origin": str(getattr(bbox, "coord_origin", "")),
    }


def extract_tables(pdf_path):
    """Extract every table in ``pdf_path`` to Markdown with page + bbox provenance.

    Returns a list of ``{source_filename, page_number, bbox, markdown}`` (one per table),
    in document order. An empty list means the doc has no detected tables (the caller
    skips the table path for it — latency, D-51). Loopback-only; never writes the file.
    """
    pdf_path = Path(pdf_path)

    # Loopback-only by default: serve cached models, suppress the hub revision-check, so a
    # conversion makes zero egress. The approved one-time fetch sets DOCLING_ALLOW_MODEL_FETCH=1.
    if os.environ.get("DOCLING_ALLOW_MODEL_FETCH") != "1":
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"

    # Lazy import so a caller that never extracts tables never loads Docling/torch.
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    opts = PdfPipelineOptions(do_ocr=False, do_table_structure=True)
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
    )
    doc = converter.convert(pdf_path).document

    tables = []
    for t in doc.tables:
        prov = t.prov[0] if t.prov else None
        tables.append({
            "source_filename": pdf_path.name,
            "page_number": int(prov.page_no) if prov else None,
            "bbox": _bbox_dict(prov.bbox) if prov else None,
            "markdown": t.export_to_markdown(doc).strip(),
        })
    return tables
