"""
CATEGORY 1: INPUT UNDERSTANDING LAYER
Runs BEFORE all other analysis.
Detects: file type, page count, DPI, resolution, quality score.
Bad quality affects all downstream checks — this layer flags it early.
"""
import os
import fitz
import cv2
import numpy as np
from PIL import Image

def analyse_input(file_path: str) -> dict:
    """
    Master input analysis — runs first before any forgery checks.
    Returns file metadata + quality score that adjusts downstream confidence.
    """
    ext = os.path.splitext(file_path)[1].lower()
    result = {
        "file_type":    "unknown",
        "sub_type":     "unknown",   # scanned_pdf / digital_pdf / photo / screenshot
        "page_count":   1,
        "width_px":     0,
        "height_px":    0,
        "dpi":          0,
        "file_size_kb": round(os.path.getsize(file_path) / 1024, 1),
        "quality_score": 100,        # 0-100, low = bad quality
        "quality_flags": [],
        "warnings":     [],
    }

    try:
        if ext == ".pdf":
            result["file_type"] = "pdf"
            result.update(_analyse_pdf(file_path))
        elif ext in {".jpg", ".jpeg", ".png"}:
            result["file_type"] = "image"
            result.update(_analyse_image(file_path))
    except Exception as e:
        result["warnings"].append(f"Input analysis error: {e}")

    # Compute quality score
    result["quality_score"] = _compute_quality_score(result)
    return result


def _analyse_pdf(path: str) -> dict:
    doc = fitz.open(path)
    info = {"page_count": len(doc)}
    page = doc[0]
    # Determine if scanned or digital
    text = page.get_text().strip()
    images = page.get_images()
    if text and not images:
        info["sub_type"] = "digital_pdf"
    elif images and not text:
        info["sub_type"] = "scanned_pdf"
    else:
        info["sub_type"] = "mixed_pdf"
    # Render first page to get dimensions
    pix = page.get_pixmap(dpi=150)
    info["width_px"]  = pix.width
    info["height_px"] = pix.height
    info["dpi"] = 150
    flags = []
    if pix.width < 800:
        flags.append("Low resolution PDF render ⚠️")
    if len(doc) > 20:
        flags.append(f"Large document: {len(doc)} pages")
    info["quality_flags"] = flags
    doc.close()
    return info


def _analyse_image(path: str) -> dict:
    img_pil = Image.open(path)
    w, h = img_pil.size
    # Try to get DPI from EXIF
    dpi = 72
    try:
        dpi_info = img_pil.info.get("dpi", (72, 72))
        dpi = int(dpi_info[0]) if dpi_info else 72
    except:
        pass
    # Detect screenshot vs photo (screenshots are usually exact pixel dimensions)
    is_screenshot = (w % 100 == 0 or h % 100 == 0) and dpi <= 72
    sub = "screenshot" if is_screenshot else "photo"
    flags = []
    if w < 600 or h < 400:
        flags.append("Very low resolution — analysis may be inaccurate ⚠️")
    if dpi < 100:
        flags.append(f"Low DPI ({dpi}) — may affect OCR accuracy ⚠️")
    # Blur detection
    img_cv = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    blurriness = 0.0
    if img_cv is not None:
        lap = cv2.Laplacian(img_cv, cv2.CV_64F)
        blurriness = float(np.var(lap))
        if blurriness < 100:
            flags.append(f"Image appears blurry (sharpness: {blurriness:.0f}) ⚠️")
    return {
        "sub_type":     sub,
        "width_px":     w,
        "height_px":    h,
        "dpi":          dpi,
        "blurriness":   round(blurriness, 1),
        "quality_flags": flags,
    }


def _compute_quality_score(info: dict) -> int:
    score = 100
    if info["width_px"] < 600:  score -= 25
    if info["dpi"] < 72:        score -= 15
    if info["dpi"] < 100:       score -= 10
    score -= len(info.get("quality_flags", [])) * 5
    return max(0, min(100, score))
