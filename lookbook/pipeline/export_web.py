from __future__ import annotations
from pathlib import Path
import html


def export_web(project: str | Path, output: str | Path) -> Path:
    project = Path(project)
    output = Path(output)
    manifest = project / "manifest.json"
    manifest_text = manifest.read_text(encoding="utf-8") if manifest.exists() else "{}"
    body = f"""<!doctype html><html><head><meta charset='utf-8'><title>lookBOOK Review</title><style>body{{background:#070a10;color:#fdf6d8;font-family:system-ui;margin:0}}main{{max-width:980px;margin:auto;padding:40px}}pre{{background:#121824;padding:20px;border-radius:16px;overflow:auto}}.badge{{color:#1ae0cf;text-transform:uppercase;letter-spacing:.18em;font-weight:800}}</style></head><body><main><p class='badge'>lookBOOK true-animation review</p><h1>Project Manifest</h1><pre>{html.escape(manifest_text)}</pre></main></body></html>"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(body, encoding="utf-8")
    return output
