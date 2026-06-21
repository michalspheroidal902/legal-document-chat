"""T-TBL.1 — author a SYNTHETIC born-digital contract exhibit containing a real, ruled
table (a multi-year license-fee schedule) for the tables capability.

The PDF is built with PyMuPDF (already a dependency — no new install): page 1 is a short
prose preamble (born-digital text the existing PyMuPDF path handles unchanged), page 2 is
"EXHIBIT A — LICENSE FEE SCHEDULE", a visually ruled grid with selectable cell text that
Docling's TableFormer can recognize. All content is clearly SYNTHETIC — NOT REAL.

The document body is git-ignored (D-28); only this builder + the ground-truth cell list
(``GROUND_TRUTH``) are tracked, so tests rebuild the PDF deterministically and assert the
known cells land in the extracted table markdown on the correct page.
"""

from pathlib import Path

import fitz  # PyMuPDF

PIPELINE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PIPELINE_DIR.parent
TABLES_DIR = REPO_ROOT / "documents" / "synthetic_corpus" / "tables"
EXHIBIT_PDF = TABLES_DIR / "meridian_license_fee_schedule.pdf"

BANNER = "SYNTHETIC - NOT REAL - fabricated for local development (no real client data)."

# The fee schedule. Distinctive, internally-consistent values (Total = License + Support)
# so a retrieved value is unambiguous and a fabricated one is clearly absent.
HEADERS = ["Year", "Annual License Fee", "Annual Support Fee", "Total Annual Fee"]
ROWS = [
    ["2024", "$120,000", "$24,000", "$144,000"],
    ["2025", "$126,000", "$25,200", "$151,200"],
    ["2026", "$132,300", "$26,460", "$158,760"],
    ["2027", "$138,915", "$27,783", "$166,698"],
    ["2028", "$145,861", "$29,172", "$175,033"],
]
TABLE_PAGE = 2  # 1-based page the table lives on

# Ground-truth cells tests assert on (value -> human description). These are the exact
# strings that must appear in the extracted table markdown on page TABLE_PAGE.
GROUND_TRUTH = {
    "$132,300": "2026 Annual License Fee",
    "$166,698": "2027 Total Annual Fee",
    "$145,861": "2028 Annual License Fee",
    "$24,000": "2024 Annual Support Fee",
}
# A value that is NOT anywhere in the table — used to prove fabricated cells are rejected.
ABSENT_VALUE = "$999,999"
# A string that appears ONLY in the page-1 prose (not in the table) — used to prove the
# table extraction attributes cells to the correct page, not page 1.
PAGE1_ONLY_MARKER = "Meridian Software Systems, Inc."


def _draw_table(page, x0, y0, col_w, row_h, headers, rows):
    """Draw a ruled grid with selectable cell text; return the table bbox (fitz.Rect)."""
    n_cols = len(headers)
    n_rows = len(rows) + 1  # + header row
    width = sum(col_w)
    height = row_h * n_rows
    # horizontal rules
    for r in range(n_rows + 1):
        y = y0 + r * row_h
        page.draw_line((x0, y), (x0 + width, y), color=(0, 0, 0), width=0.8)
    # vertical rules
    x = x0
    for c in range(n_cols + 1):
        page.draw_line((x, y0), (x, y0 + height), color=(0, 0, 0), width=0.8)
        if c < n_cols:
            x += col_w[c]

    def put_row(cells, ry, bold):
        cx = x0
        for c, cell in enumerate(cells):
            page.insert_text((cx + 5, ry + row_h - 6), cell, fontsize=10,
                             fontname="helv" if not bold else "hebo")
            cx += col_w[c]

    put_row(headers, y0, bold=True)
    for i, row in enumerate(rows):
        put_row(row, y0 + (i + 1) * row_h, bold=False)
    return fitz.Rect(x0, y0, x0 + width, y0 + height)


def build_fee_schedule_exhibit(out_path=EXHIBIT_PDF):
    """Build the 2-page exhibit PDF (page 1 prose, page 2 ruled fee-schedule table)."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()

    # Page 1 — prose preamble (born-digital; the PyMuPDF prose path handles it unchanged).
    p1 = doc.new_page(width=612, height=792)
    p1.insert_text((72, 90), "SOFTWARE LICENSE AGREEMENT", fontsize=16, fontname="hebo")
    body1 = [
        BANNER,
        "",
        f"This Software License Agreement is entered into by and between {PAGE1_ONLY_MARKER},",
        "a Delaware corporation (the \"Licensor\"), and Pemberton Logistics Inc., an Ohio",
        "corporation (the \"Licensee\").",
        "",
        "1. License. Licensor grants Licensee a non-exclusive license to the Meridian",
        "   Logistics Platform for the term set forth herein.",
        "",
        "2. Fees. Licensee shall pay the annual license and support fees set forth in",
        "   Exhibit A (License Fee Schedule), attached hereto and incorporated by reference.",
        "",
        "3. Governing Law. This Agreement is governed by the laws of the State of Delaware.",
    ]
    y = 130
    for line in body1:
        p1.insert_text((72, y), line, fontsize=11, fontname="helv")
        y += 18

    # Page 2 — Exhibit A: the ruled fee-schedule table.
    p2 = doc.new_page(width=612, height=792)
    p2.insert_text((72, 90), "EXHIBIT A - LICENSE FEE SCHEDULE", fontsize=14, fontname="hebo")
    p2.insert_text((72, 112), BANNER, fontsize=9, fontname="helv")
    p2.insert_text((72, 140),
                   "The annual license and support fees payable by Licensee are:",
                   fontsize=11, fontname="helv")
    _draw_table(p2, x0=72, y0=160, col_w=[90, 140, 140, 140], row_h=26,
                headers=HEADERS, rows=ROWS)
    p2.insert_text((72, 360),
                   "All fees are stated in U.S. dollars and are due annually in advance.",
                   fontsize=11, fontname="helv")

    doc.save(str(out_path))
    doc.close()
    return out_path


if __name__ == "__main__":
    path = build_fee_schedule_exhibit()
    print(f"built table exhibit -> {path} ({path.stat().st_size} bytes)")
    print("ground-truth cells:", GROUND_TRUTH)
