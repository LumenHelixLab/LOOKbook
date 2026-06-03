from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json

@dataclass
class LookbookManifest:
    project: str
    format_version: str = "0.2"
    source_type: str = "unknown"
    rights_mode: str = "user_supplied_private"
    output_intent: str = "true_image_to_video_animation"
    description: str = ""
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
