"""lookBOOK pipeline — shared utilities for exporter routing and shot graph resolution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def resolve_shot_graph(project: str | Path, shot_graph_path: str | Path | None = None) -> tuple[Path, dict[str, Any]]:
    """Return the best available shot graph path and its parsed data.

    Prefers vision-enhanced shot graph if present, otherwise falls back
    to classical shot_graph.json.
    """
    project = Path(project)
    if shot_graph_path is not None:
        path = Path(shot_graph_path)
    else:
        vision = project / "analysis" / "shot_graph_vision.json"
        classical = project / "analysis" / "shot_graph.json"
        path = vision if vision.exists() else classical

    if not path.exists():
        raise FileNotFoundError(f"Shot graph not found at {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    return path, data
