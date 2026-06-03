from __future__ import annotations
from pathlib import Path
from typing import Any
from ..models import write_json


def detect_panels(
    source: str | Path,
    project: str | Path,
    output_dir: str | None = None,
) -> list[dict[str, Any]]:
    """Detect and segment comic panels from a full page image.

    Uses OpenCV contour detection with morphological operations to find
    panel boundaries, then orders them by Western reading direction
    (left→right, top→bottom).

    Returns a list of panel dicts with bbox and extracted image paths.
    """
    import cv2
    import numpy as np

    source = Path(source)
    project = Path(project)

    if not source.exists():
        raise FileNotFoundError(f"Source not found: {source}")

    # Read image
    img = cv2.imread(str(source))
    if img is None:
        raise ValueError(f"Could not read image: {source}")
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Binary threshold + invert so panel borders are black on white
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Morphological close to fill gaps in borders
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Find contours
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter and extract panel regions
    min_area = (w * h) * 0.01  # At least 1% of page area
    panels: list[dict[str, Any]] = []

    for i, cnt in enumerate(contours):
        x, y, pw, ph = cv2.boundingRect(cnt)
        area = pw * ph
        if area < min_area:
            continue
        # Skip regions that are too thin (likely gutters or noise)
        if pw < w * 0.02 or ph < h * 0.02:
            continue

        panels.append(
            {
                "panel_index": len(panels),
                "bbox": {"x": int(x), "y": int(y), "w": int(pw), "h": int(ph)},
                "area": int(area),
                "aspect_ratio": round(pw / max(ph, 1), 3),
            }
        )

    # Sort by reading order: top→bottom, left→right (tolerance = 1/3 page height)
    row_tolerance = h * 0.33
    panels.sort(key=lambda p: (p["bbox"]["y"] // max(int(row_tolerance), 1), p["bbox"]["x"]))

    # Re-number after sort
    for idx, p in enumerate(panels):
        p["panel_index"] = idx

    # Extract cropped panel images if output_dir provided
    panel_dir = None
    if output_dir:
        panel_dir = Path(output_dir)
    elif project:
        panel_dir = project / "analysis" / "panels"
        panel_dir.mkdir(parents=True, exist_ok=True)

    if panel_dir:
        for p in panels:
            bx = p["bbox"]
            crop = img[bx["y"] : bx["y"] + bx["h"], bx["x"] : bx["x"] + bx["w"]]
            panel_path = panel_dir / f"panel_{p['panel_index']:03d}{source.suffix}"
            cv2.imwrite(str(panel_path), crop)
            p["image_path"] = str(panel_path.relative_to(project))

    result = {
        "schema": "lookbook.panels.v0.2",
        "source_file": source.name,
        "image_dims": {"w": int(w), "h": int(h)},
        "total_panels": len(panels),
        "panels": panels,
    }

    analysis_dir = project / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    write_json(analysis_dir / "panel_analysis.json", result)

    return panels
