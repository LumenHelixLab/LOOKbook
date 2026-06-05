from __future__ import annotations
from pathlib import Path
from .models import LookbookManifest, write_json

PROJECT_DIRS = [
    "source",
    "analysis",
    "characters",
    "shots",
    "keyframes",
    "prompts",
    "audio",
    "renders",
    "exports",
    "review",
]


def init_project(path: str | Path, name: str = "Untitled lookBOOK Project") -> Path:
    project_path = Path(path)
    project_path.mkdir(parents=True, exist_ok=True)
    for item in PROJECT_DIRS:
        (project_path / item).mkdir(exist_ok=True)
    write_json(
        project_path / "manifest.json",
        LookbookManifest(project=name, description="A lookBOOK true-animation project.").to_dict(),
    )
    (project_path / "RIGHTS.md").write_text(
        "# Rights\n\nDocument source ownership, license, and output rights here.\n",
        encoding="utf-8",
    )
    (project_path / "STYLE.md").write_text(
        "# Style Direction\n\nDescribe visual, motion, audio, and adaptation style here.\n",
        encoding="utf-8",
    )
    return project_path
