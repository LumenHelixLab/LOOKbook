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
from .pipeline.director_ai import generate_director_decisions
from .video.animatic import build_animatic
from .schemas import DirectorRequest, AnimaticRequest, ShotGraph

logger = logging.getLogger("lookbook.lab_server")

PROJECTS_ROOT = Path(tempfile.gettempdir()) / "lookbook_lab_projects"
PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)

MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB


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


def _read_multipart_image(handler) -> tuple[Path, Path]:
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
            project_id = str(uuid.uuid4())[:8]
            project_dir = PROJECTS_ROOT / project_id
            project_dir.mkdir(parents=True, exist_ok=True)
            img_path = project_dir / "source.png"
            img_path.write_bytes(file_data)
            init_project(project_dir, f"lab-{project_id}")
            return img_path, project_dir
    raise ValueError("No file found in upload")


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
            if path == "/api/analyze":
                img_path, project_dir = _read_multipart_image(self)
                result = analyze_source(img_path, project_dir)
                _json_response(self, 200, {"project_id": project_dir.name, "result": result})
                return

            if path == "/api/extract-text":
                img_path, project_dir = _read_multipart_image(self)
                blocks = extract_text(img_path, project_dir)
                _json_response(self, 200, {"project_id": project_dir.name, "blocks": blocks})
                return

            if path == "/api/panels":
                img_path, project_dir = _read_multipart_image(self)
                panels = detect_panels(img_path, project_dir)
                _json_response(self, 200, {"project_id": project_dir.name, "panels": panels})
                return

            if path == "/api/vision":
                img_path, project_dir = _read_multipart_image(self)
                query = parse_qs(parsed.query)
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
