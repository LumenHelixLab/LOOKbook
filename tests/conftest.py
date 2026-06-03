"""pytest configuration for lookBOOK tests."""
from __future__ import annotations
import os
from pathlib import Path

# Detect Tesseract on Windows and configure pytesseract
_tesseract_paths = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

for _p in _tesseract_paths:
    if Path(_p).exists():
        os.environ.setdefault("TESSERACT_CMD", _p)
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = _p
        except ImportError:
            pass
        break
