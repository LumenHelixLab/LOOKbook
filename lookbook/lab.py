from __future__ import annotations
from pathlib import Path
import shutil


def install_demo_lab(output: str | Path) -> Path:
    repo_root = Path(__file__).resolve().parent.parent
    src = repo_root / "demo-lab"
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    target = output / "demo-lab"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(src, target)
    return target
