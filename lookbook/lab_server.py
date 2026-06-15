"""lookBOOK — Demo Lab Real Bridge (M4)

A lightweight HTTP API server that connects the browser demo lab
to the Python pipeline. Uses only stdlib (no FastAPI/Flask dep)
to keep the install footprint minimal.

Endpoints:
  POST /api/analyze       — run full pipeline on uploaded image
  POST /api/extract-text  — OCR on uploaded image
  POST /api/panels        — panel detection
  GET  /api/project/{id}  — read project analysis JSONs
  GET  /api/export/{id}   — list export artifacts
  POST /api/vision        — run vision LLM on uploaded image
  POST /api/director      — generate director decisions
  POST /api/animatic      — generate animatic MP4 from shot JSON
  GET  /api/animatic/{id} — download generated animatic MP4
  GET  /                  — demo-lab UI (index.html)
  GET  /health            — server health check
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from threading import Thread

from .project import init_project
from .pipeline.analyze import analyze_source
from .pipeline.ocr import extract_text
from .pipeline.panels import detect_panels
from .pipeline.vision_enhanced import analyze_source_vision
from .pipeline.director_ai import export_director_packet, generate_director_decisions
from .pipeline.living_panels_export import export_living_panels
from .pipeline.vault_import import import_vault_manifest
from .pipeline.choreography import build_choreography
from .models import write_json
from .video.animatic import build_animatic
from .schemas import DirectorRequest, AnimaticRequest, ShotGraph

logger = logging.getLogger("lookbook.lab_server")

PROJECTS_ROOT = Path(tempfile.gettempdir()) / "lookbook_lab_projects"
PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_LAB_ROOT = REPO_ROOT / "demo-lab"

MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB

_STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


def _resolve_demo_lab_file(url_path: str) -> Path | None:
    """Map a URL path to a file under demo-lab/ (path traversal safe)."""
    if not DEMO_LAB_ROOT.is_dir():
        return None
    clean = url_path.split("?", 1)[0]
    if clean in ("", "/"):
        clean = "/index.html"
    if clean.startswith("/demo-lab/"):
        clean = clean[len("/demo-lab") :]
    if not clean.startswith("/"):
        clean = "/" + clean
    rel = Path(clean.lstrip("/"))
    if ".." in rel.parts:
        return None
    candidate = (DEMO_LAB_ROOT / rel).resolve()
    try:
        candidate.relative_to(DEMO_LAB_ROOT.resolve())
    except ValueError:
        return None
    if candidate.is_file():
        return candidate
    return None


def _serve_static_file(handler, file_path: Path):
    body = file_path.read_bytes()
    handler.send_response(200)
    handler.send_header("Content-Type", _STATIC_TYPES.get(file_path.suffix.lower(), "application/octet-stream"))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _json_response(handler, status: int, payload: dict):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _safe_project_dir(project_id: str) -> Path:
    """Return a project directory inside PROJECTS_ROOT, rejecting path traversal."""
    if not project_id:
        raise ValueError("project_id is required")
    if ".." in project_id or "/" in project_id or "\\" in project_id:
        raise ValueError("Invalid project_id")
    project_dir = PROJECTS_ROOT / project_id
    try:
        resolved = project_dir.resolve()
        root_resolved = PROJECTS_ROOT.resolve()
        if not str(resolved).startswith(str(root_resolved)):
            raise ValueError("Path traversal detected")
    except (OSError, RuntimeError):
        raise ValueError("Invalid project path")
    return project_dir


def _check_body_size(handler):
    length = int(handler.headers.get("Content-Length", 0))
    if length > MAX_BODY_SIZE:
        raise ValueError(f"Request body too large: {length} bytes (max {MAX_BODY_SIZE})")
    return length


def _read_multipart_image(handler, project_id: str | None = None) -> tuple[Path, Path]:
    """Naive multipart parser that extracts the first file upload."""
    content_type = handler.headers.get("Content-Type", "")
    if "boundary=" not in content_type:
        raise ValueError("Missing boundary")
    boundary = content_type.split("boundary=")[1].encode()
    length = _check_body_size(handler)
    data = handler.rfile.read(length)

    parts = data.split(b"--" + boundary)
    for part in parts:
        if b'Content-Disposition: form-data; name="file"' in part or b"filename=" in part:
            header_end = part.find(b"\r\n\r\n")
            if header_end == -1:
                continue
            file_data = part[header_end + 4 :].rstrip(b"\r\n")
            if project_id:
                project_dir = _safe_project_dir(project_id)
                if not project_dir.exists():
                    raise ValueError("Project not found")
            else:
                project_id = str(uuid.uuid4())[:8]
                project_dir = PROJECTS_ROOT / project_id
                project_dir.mkdir(parents=True, exist_ok=True)
                init_project(project_dir, f"lab-{project_id}")
            img_path = project_dir / "source.png"
            img_path.write_bytes(file_data)
            return img_path, project_dir
    raise ValueError("No file found in upload")


def _synthesize_ocr_from_panels(project_dir: Path) -> list[dict]:
    """Create demo OCR blocks from panel bboxes when Tesseract output is missing."""
    panel_path = project_dir / "analysis" / "panel_analysis.json"
    if not panel_path.exists():
        return []
    panels = json.loads(panel_path.read_text(encoding="utf-8")).get("panels", [])
    samples = [
        ('"What happened here?"', "dialogue"),
        ('"We need answers."', "dialogue"),
        ("Meanwhile, the scene shifts…", "narration"),
        ("BOOM", "sfx"),
    ]
    blocks = []
    for i, panel in enumerate(panels):
        bbox = panel.get("bbox", {})
        text, cls = samples[i % len(samples)]
        blocks.append(
            {
                "text": text,
                "classification": cls,
                "bbox": bbox,
                "conf": 75,
                "block_num": i,
            }
        )
    write_json(
        project_dir / "analysis" / "ocr_result.json",
        {
            "schema": "lookbook.ocr.v0.2",
            "source_file": "source.png",
            "lang": "eng",
            "total_blocks": len(blocks),
            "full_text": " ".join(b["text"] for b in blocks),
            "blocks": blocks,
            "synthesized": True,
        },
    )
    return blocks


def _synthesize_characters_from_panels(project_dir: Path) -> list[dict]:
    """Minimal character map so choreography can assign speakers."""
    panel_path = project_dir / "analysis" / "panel_analysis.json"
    if not panel_path.exists():
        return []
    panels = json.loads(panel_path.read_text(encoding="utf-8")).get("panels", [])
    names = ["Hero", "Ally", "Narrator"]
    characters = []
    for i, name in enumerate(names[: max(1, min(3, len(panels)))]):
        panel_idx = i % len(panels)
        pb = panels[panel_idx].get("bbox", {})
        characters.append(
            {
                "character_id": f"char_{i:03d}",
                "name": name,
                "appearances": 1,
                "panels": [{"panel_index": panel_idx, "bbox": pb}],
            }
        )
    write_json(
        project_dir / "analysis" / "character_analysis.json",
        {"schema": "lookbook.characters.v0.2", "characters": characters, "synthesized": True},
    )
    return characters


def _ensure_choreography_inputs(project_dir: Path) -> None:
    """Guarantee analysis files exist before build_choreography."""
    ocr_path = project_dir / "analysis" / "ocr_result.json"
    blocks: list = []
    if ocr_path.exists():
        try:
            blocks = json.loads(ocr_path.read_text(encoding="utf-8")).get("blocks", [])
        except Exception:
            blocks = []
    if not blocks:
        _synthesize_ocr_from_panels(project_dir)
    char_path = project_dir / "analysis" / "character_analysis.json"
    if not char_path.exists():
        _synthesize_characters_from_panels(project_dir)


def _build_living_panels_review(project_dir: Path) -> Path:
    """Build choreography + living-panels HTML for a lab project."""
    _ensure_choreography_inputs(project_dir)
    build_choreography(project_dir)
    return export_living_panels(project_dir)


def _read_multipart_json(handler) -> dict:
    """Naive multipart parser that extracts the first JSON file upload."""
    content_type = handler.headers.get("Content-Type", "")
    if "boundary=" not in content_type:
        raise ValueError("Missing boundary")
    boundary = content_type.split("boundary=")[1].encode()
    length = _check_body_size(handler)
    data = handler.rfile.read(length)

    parts = data.split(b"--" + boundary)
    for part in parts:
        if b"filename=" in part:
            header_end = part.find(b"\r\n\r\n")
            if header_end == -1:
                continue
            file_data = part[header_end + 4 :].rstrip(b"\r\n")
            return json.loads(file_data.decode("utf-8"))
    raise ValueError("No JSON file found in upload")


def _placeholder_living_panels_html(project_dir: Path, message: str) -> Path:
    """In-iframe placeholder when review cannot be built yet."""
    out = project_dir / "exports" / "living_panels" / "review.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        f"""<!doctype html><html><head><meta charset="utf-8"><title>Living Panels</title>
<style>body{{font-family:system-ui;background:#12100e;color:#f5e6d0;padding:32px;text-align:center}}
.box{{max-width:420px;margin:40px auto;padding:24px;border:1px dashed #ffb04244;border-radius:16px}}
</style></head><body><div class="box"><h2>Living panels not ready</h2><p>{message}</p>
<p style="color:#f5e6d088;font-size:14px">Use <strong>Build &amp; play living panels</strong> in the lab above.</p></div></body></html>""",
        encoding="utf-8",
    )
    return out


def _seed_project_preset(project_dir: Path, preset: str) -> dict:
    """Seed analysis/ layout for demo-lab wizard presets."""
    analysis = project_dir / "analysis"
    analysis.mkdir(parents=True, exist_ok=True)
    scaffold = {
        "schema": "lookbook.project_scaffold.v1",
        "preset": preset,
        "folders": ["analysis", "source", "exports"],
    }
    scaffold_path = analysis / "project_scaffold.json"
    scaffold_path.write_text(json.dumps(scaffold, indent=2), encoding="utf-8")
    (project_dir / "source").mkdir(parents=True, exist_ok=True)
    (project_dir / "exports").mkdir(parents=True, exist_ok=True)
    return {"preset": preset, "scaffold_path": str(scaffold_path)}


def _read_json_body(handler) -> dict:
    """Read and validate a JSON body for non-multipart POSTs."""
    content_type = handler.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        raise ValueError("Content-Type must be application/json")
    length = _check_body_size(handler)
    data = handler.rfile.read(length)
    if not data:
        raise ValueError("Empty request body")
    try:
        return json.loads(data.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}")


class LabHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        logger.info(fmt % args)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == "/health":
                _json_response(self, 200, {"ok": True, "service": "lookbook-lab"})
                return

            if path.startswith("/api/director-preview/"):
                project_id = path.split("/")[-1]
                query = parse_qs(parsed.query)
                target = query.get("target", ["runway"])[0]
                project_dir = _safe_project_dir(project_id)
                if not project_dir.exists():
                    _json_response(self, 404, {"error": "Project not found"})
                    return
                out_dir = project_dir / "exports" / "director_ai"
                md_files = list(out_dir.glob("*.md")) if out_dir.exists() else []
                if not md_files:
                    try:
                        md_path = export_director_packet(project_dir, target=target)
                    except FileNotFoundError as exc:
                        _json_response(self, 404, {"error": str(exc)})
                        return
                else:
                    md_path = md_files[0]
                markdown = md_path.read_text(encoding="utf-8")
                _json_response(
                    self,
                    200,
                    {
                        "project_id": project_id,
                        "target": target,
                        "path": md_path.name,
                        "markdown": markdown,
                    },
                )
                return

            if path.startswith("/api/living-panels/"):
                project_id = path.split("/")[-1]
                project_dir = _safe_project_dir(project_id)
                if not project_dir.exists():
                    _json_response(self, 404, {"error": "Project not found"})
                    return
                review_path = project_dir / "exports" / "living_panels" / "review.html"
                if not review_path.exists():
                    panel_file = project_dir / "analysis" / "panel_analysis.json"
                    if not panel_file.exists():
                        review_path = _placeholder_living_panels_html(
                            project_dir, "Run the pipeline on an image first."
                        )
                    else:
                        try:
                            review_path = _build_living_panels_review(project_dir)
                        except Exception as exc:
                            logger.warning("Living panels build failed: %s", exc)
                            review_path = _placeholder_living_panels_html(
                                project_dir, "Could not build review yet. Try Build &amp; play again."
                            )
                body = review_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if path.startswith("/api/project/"):
                project_id = path.split("/")[-1]
                project_dir = _safe_project_dir(project_id)
                if not project_dir.exists():
                    _json_response(self, 404, {"error": "Project not found"})
                    return
                files = {}
                for json_file in (project_dir / "analysis").glob("*.json"):
                    try:
                        files[json_file.stem] = json.loads(json_file.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                _json_response(self, 200, {"project_id": project_id, "analysis": files})
                return

            if path.startswith("/api/export/"):
                project_id = path.split("/")[-1]
                project_dir = _safe_project_dir(project_id)
                if not project_dir.exists():
                    _json_response(self, 404, {"error": "Project not found"})
                    return
                artifacts = {}
                for platform_dir in (project_dir / "exports").iterdir():
                    if platform_dir.is_dir():
                        artifacts[platform_dir.name] = [f.name for f in platform_dir.iterdir()]
                _json_response(self, 200, {"project_id": project_id, "artifacts": artifacts})
                return

            if path.startswith("/api/animatic/"):
                project_id = path.split("/")[-1]
                project_dir = _safe_project_dir(project_id)
                if not project_dir.exists():
                    _json_response(self, 404, {"error": "Project not found"})
                    return
                animatic_path = project_dir / "animatic.mp4"
                if not animatic_path.exists():
                    _json_response(self, 404, {"error": "Animatic not found"})
                    return
                self.send_response(200)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(animatic_path.stat().st_size))
                self.end_headers()
                self.wfile.write(animatic_path.read_bytes())
                return

            static_file = _resolve_demo_lab_file(path)
            if static_file is not None:
                _serve_static_file(self, static_file)
                return

            _json_response(self, 404, {"error": "Not found"})
        except ValueError as exc:
            logger.warning("GET validation error: %s", exc)
            _json_response(self, 400, {"error": str(exc)})
        except Exception as exc:
            logger.exception("Unhandled GET error")
            _json_response(self, 500, {"error": "Internal server error"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == "/api/new-project":
                req = _read_json_body(self)
                name = str(req.get("name") or "lab-project").strip()[:60] or "lab-project"
                preset = str(req.get("preset") or "comic").strip()
                project_id = str(uuid.uuid4())[:8]
                project_dir = PROJECTS_ROOT / project_id
                project_dir.mkdir(parents=True, exist_ok=True)
                init_project(project_dir, name)
                seed = _seed_project_preset(project_dir, preset)
                _json_response(
                    self,
                    200,
                    {"project_id": project_id, "name": name, "seed": seed},
                )
                return

            if path == "/api/import-vault":
                req = _read_json_body(self)
                manifest = req.get("manifest")
                if not isinstance(manifest, dict):
                    raise ValueError("manifest object required")
                project_id = req.get("project_id")
                if project_id:
                    project_dir = _safe_project_dir(str(project_id))
                    if not project_dir.exists():
                        _json_response(self, 404, {"error": "Project not found"})
                        return
                else:
                    project_id = str(uuid.uuid4())[:8]
                    project_dir = PROJECTS_ROOT / project_id
                result = import_vault_manifest(
                    project_dir,
                    manifest,
                    init_if_missing=True,
                    project_name=manifest.get("title"),
                )
                _json_response(
                    self,
                    200,
                    {"project_id": project_dir.name, "import": result},
                )
                return

            query = parse_qs(parsed.query)
            existing_project = query.get("project_id", [None])[0]

            if path == "/api/build-living-panels":
                req = _read_json_body(self)
                project_id = str(req.get("project_id") or "")
                project_dir = _safe_project_dir(project_id)
                if not project_dir.exists():
                    _json_response(self, 404, {"error": "Project not found"})
                    return
                review_path = _build_living_panels_review(project_dir)
                choreo = json.loads(
                    (project_dir / "analysis" / "choreography.json").read_text(encoding="utf-8")
                )
                _json_response(
                    self,
                    200,
                    {
                        "project_id": project_id,
                        "choreography_lines": choreo.get("total_lines", 0),
                        "living_panels_url": f"/api/living-panels/{project_id}",
                        "review_path": str(review_path),
                    },
                )
                return

            if path.startswith("/api/project/") and path.endswith("/sync-analysis"):
                parts = [p for p in path.split("/") if p]
                if len(parts) < 4 or parts[0] != "api" or parts[1] != "project":
                    _json_response(self, 400, {"error": "Invalid sync path"})
                    return
                project_id = parts[2]
                project_dir = _safe_project_dir(project_id)
                if not project_dir.exists():
                    _json_response(self, 404, {"error": "Project not found"})
                    return
                req = _read_json_body(self)
                if req.get("ocr_blocks"):
                    write_json(
                        project_dir / "analysis" / "ocr_result.json",
                        {
                            "schema": "lookbook.ocr.v0.2",
                            "source_file": "source.png",
                            "lang": "eng",
                            "total_blocks": len(req["ocr_blocks"]),
                            "full_text": " ".join(
                                str(b.get("text", "")) for b in req["ocr_blocks"]
                            ),
                            "blocks": req["ocr_blocks"],
                            "synced_from_lab": True,
                        },
                    )
                if req.get("characters"):
                    chars = []
                    for i, c in enumerate(req["characters"]):
                        panel_indices = c.get("panels") or []
                        char_panels = []
                        panel_file = project_dir / "analysis" / "panel_analysis.json"
                        panel_list = []
                        if panel_file.exists():
                            panel_list = json.loads(
                                panel_file.read_text(encoding="utf-8")
                            ).get("panels", [])
                        for pidx in panel_indices:
                            bbox = {}
                            if panel_list and pidx < len(panel_list):
                                bbox = panel_list[pidx].get("bbox", {})
                            char_panels.append({"panel_index": pidx, "bbox": bbox})
                        chars.append(
                            {
                                "character_id": f"char_{i:03d}",
                                "name": c.get("name", f"Character {i + 1}"),
                                "appearances": len(char_panels),
                                "panels": char_panels,
                            }
                        )
                    write_json(
                        project_dir / "analysis" / "character_analysis.json",
                        {"schema": "lookbook.characters.v0.2", "characters": chars},
                    )
                _json_response(self, 200, {"project_id": project_id, "synced": True})
                return

            if path == "/api/analyze":
                img_path, project_dir = _read_multipart_image(self, project_id=existing_project)
                result = analyze_source(img_path, project_dir)
                _json_response(self, 200, {"project_id": project_dir.name, "result": result})
                return

            if path == "/api/extract-text":
                img_path, project_dir = _read_multipart_image(self, project_id=existing_project)
                try:
                    blocks = extract_text(img_path, project_dir)
                except Exception as exc:
                    logger.warning("OCR failed, will synthesize on build: %s", exc)
                    blocks = _synthesize_ocr_from_panels(project_dir)
                _json_response(
                    self,
                    200,
                    {"project_id": project_dir.name, "blocks": blocks, "ocr_fallback": not blocks},
                )
                return

            if path == "/api/panels":
                img_path, project_dir = _read_multipart_image(self, project_id=existing_project)
                panels = detect_panels(img_path, project_dir)
                _json_response(self, 200, {"project_id": project_dir.name, "panels": panels})
                return

            if path == "/api/vision":
                img_path, project_dir = _read_multipart_image(self, project_id=existing_project)
                provider = query.get("provider", [None])[0]
                result = analyze_source_vision(img_path, project_dir, provider=provider)
                _json_response(self, 200, {"project_id": project_dir.name, "result": result})
                return

            if path == "/api/director":
                req = _read_json_body(self)
                validated = DirectorRequest.model_validate(req)
                project_dir = _safe_project_dir(validated.project_id)
                if not project_dir.exists():
                    _json_response(self, 404, {"error": "Project not found"})
                    return
                decision = generate_director_decisions(project_dir, target=validated.target)
                _json_response(self, 200, decision.model_dump())
                return

            if path == "/api/animatic":
                content_type = self.headers.get("Content-Type", "")
                if "multipart/form-data" in content_type:
                    shot_data = _read_multipart_json(self)
                    ShotGraph.model_validate(shot_data)
                    clip_duration = shot_data.get("clip_duration", 3.0)
                else:
                    raw = _read_json_body(self)
                    req = AnimaticRequest.model_validate(raw)
                    if req.project_id:
                        project_dir = _safe_project_dir(req.project_id)
                        if not project_dir.exists():
                            _json_response(self, 404, {"error": "Project not found"})
                            return
                        shot_graph_path = project_dir / "analysis" / "shot_graph.json"
                        if not shot_graph_path.exists():
                            _json_response(self, 404, {"error": "Shot graph not found"})
                            return
                        shot_data = json.loads(shot_graph_path.read_text(encoding="utf-8"))
                        ShotGraph.model_validate(shot_data)
                    elif req.shot_graph:
                        shot_data = req.shot_graph
                        ShotGraph.model_validate(shot_data)
                    else:
                        _json_response(self, 400, {"error": "Missing shot_graph or project_id"})
                        return
                    clip_duration = req.clip_duration

                project_id = str(uuid.uuid4())[:8]
                project_dir = PROJECTS_ROOT / project_id
                project_dir.mkdir(parents=True, exist_ok=True)
                shot_graph_path = project_dir / "shot_graph.json"
                shot_graph_path.write_text(json.dumps(shot_data), encoding="utf-8")

                output_path = project_dir / "animatic.mp4"
                result = build_animatic(
                    shot_graph_path,
                    output_path,
                    clip_duration=clip_duration,
                )
                _json_response(
                    self,
                    200,
                    {
                        "project_id": project_id,
                        "animatic_path": str(output_path),
                        "preview_url": f"/api/animatic/{project_id}",
                        "total_shots": result["total_shots"],
                        "total_duration_seconds": result["total_duration_seconds"],
                    },
                )
                return

            _json_response(self, 404, {"error": "Not found"})
        except ValueError as exc:
            logger.warning("POST validation error: %s", exc)
            msg = str(exc)
            if "too large" in msg.lower():
                _json_response(self, 413, {"error": msg})
            else:
                _json_response(self, 400, {"error": msg})
        except PermissionError as exc:
            logger.warning("POST permission error: %s", exc)
            _json_response(self, 403, {"error": "Permission denied"})
        except Exception as exc:
            logger.exception("Unhandled POST error")
            _json_response(self, 500, {"error": "Internal server error"})


def run_lab_server(port: int = 8042):
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    server = HTTPServer(("", port), LabHandler)
    logger.info("lookBOOK Lab Server running at http://localhost:%s", port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down lab server.")
        server.shutdown()


if __name__ == "__main__":
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8042
    run_lab_server(port=port)


def start_lab_server_thread(port: int = 8042) -> Thread:
    """Start the lab server in a background thread."""
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    server = HTTPServer(("", port), LabHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("lookBOOK Lab Server running at http://localhost:%s", port)
    return thread
