"""Task 4 — synthesize DEGRADED image-only PDFs approximating real scans.

Renders each page of a born-digital synthetic PDF to a raster and applies the
artifacts that separate a real scan from a clean render: lower DPI, page skew
(rotation), Gaussian sensor noise, and JPEG compression. Produces an image-only PDF
(no text layer) that exercises the OCR path harder than the clean 300-DPI rasters.

Local-only (PyMuPDF render + Pillow/numpy image ops). No network. Synthetic docs only;
this does NOT make synthetic data equal to real scans — real-scan validation is M6.
"""

import io
from pathlib import Path

import fitz
import numpy as np
from PIL import Image


def _degrade_image(img, rotate_deg, noise, jpeg_quality):
    """Apply skew -> Gaussian noise -> JPEG recompression to a PIL image."""
    if rotate_deg:
        img = img.rotate(rotate_deg, expand=True, fillcolor=(255, 255, 255), resample=Image.BICUBIC)
    if noise:
        arr = np.asarray(img).astype(np.float32)
        arr += np.random.normal(0.0, noise * 255.0, arr.shape)
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if jpeg_quality:
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=jpeg_quality)
        buf.seek(0)
        img = Image.open(buf)
        img.load()
    return img


def degrade_to_scanned_pdf(src_pdf, out_pdf, dpi=150, rotate_deg=1.2, noise=0.04, jpeg_quality=60):
    """Render each page of ``src_pdf`` at ``dpi``, degrade it (skew/noise/JPEG), and
    assemble an image-only PDF at ``out_pdf``. Returns the page count."""
    src_pdf, out_pdf = Path(src_pdf), Path(out_pdf)
    with fitz.open(src_pdf) as src, fitz.open() as out:
        for page in src:
            pix = page.get_pixmap(dpi=dpi)
            img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
            img = _degrade_image(img, rotate_deg, noise, jpeg_quality)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            w_pt = img.width * 72.0 / dpi
            h_pt = img.height * 72.0 / dpi
            opage = out.new_page(width=w_pt, height=h_pt)
            opage.insert_image(fitz.Rect(0, 0, w_pt, h_pt), stream=buf.getvalue())
        out.save(out_pdf)
        return src.page_count
