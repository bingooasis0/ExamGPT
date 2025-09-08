# ocr.py
from __future__ import annotations
import numpy as np
from typing import Optional
from PIL import Image

# EasyOCR (and torch) are required; we keep it simple and fast.
import easyocr

try:
    import cv2  # optional but useful for adaptive threshold
except Exception:
    cv2 = None

# Cache the reader once
_READER: Optional[easyocr.Reader] = None

def _get_reader(lang: str):
    global _READER
    langs = [lang] if lang else ["en"]
    # EasyOCR expects "en" not "eng"
    langs = ["en" if x in ("eng","en-US","en-GB") else x for x in langs]
    if _READER is None:
        _READER = easyocr.Reader(langs, gpu=False)  # CPU ok; avoids surprise torch messages
    return _READER

def _to_numpy_gray(img: Image.Image) -> np.ndarray:
    if img.mode != "L":
        gray = img.convert("L")
    else:
        gray = img
    return np.array(gray)

def run_ocr(
    img: Image.Image,
    *,
    engine: str = "easy",          # ignored, kept for compatibility
    lang: str = "eng",
    math_mode: bool = False,
    adaptive: bool = False,
    block: int = 25,
    c: int = 10,
) -> str:
    """OCR with EasyOCR only. No Tesseract, no warnings."""
    arr = _to_numpy_gray(img)

    # Light denoise for math
    if math_mode and cv2 is not None:
        arr = cv2.GaussianBlur(arr, (3,3), 0)

    # Optional adaptive thresholding
    if adaptive and cv2 is not None:
        b = block if block % 2 == 1 else block + 1  # must be odd
        arr = cv2.adaptiveThreshold(arr, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                    cv2.THRESH_BINARY, b, c)

    reader = _get_reader(lang)
    lines = reader.readtext(arr, detail=False, paragraph=True)
    text = "\n".join(lines).strip()
    return text
