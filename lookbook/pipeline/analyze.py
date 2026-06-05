from __future__ import annotations
from pathlib import Path
from typing import Any
from ..models import write_json

def analyze_source(source: str | Path, project: str | Path) -> dict[str, Any]:
    source = Path(source)
    project = Path(project)
    payload: dict[str, Any] = {
        "schema": "lookbook.analysis.v0.2",
        "source_file": source.name,
        "source_type": source.suffix.lower().lstrip(".") or "unknown",
        "status": "scaffold",
        "notes": ["Local scaffold analysis.", "Use a multimodal model or Demo Lab for deeper panel/character extraction."],
        "recommended_next_step": "lookbook true-animation-packet PROJECT --target runway",
    }
    try:
        from PIL import Image
        with Image.open(source) as img:
            payload["image"] = {"width": img.width, "height": img.height, "mode": img.mode}
    except Exception as exc:
        payload["image_probe_error"] = str(exc)
    write_json(project / "analysis" / "source_analysis.json", payload)
    return payload
