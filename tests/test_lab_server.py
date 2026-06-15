"""Tests for Demo Lab Real Bridge HTTP server (M4)."""

import json
import tempfile
from pathlib import Path

import pytest

from lookbook.lab_server import LabHandler, PROJECTS_ROOT
from lookbook.project import init_project


class TestLabServer:
    @pytest.fixture
    def client(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(
            "lookbook.lab_server.PROJECTS_ROOT", tmp_path / "lab_projects"
        )
        from http.server import HTTPServer
        import threading
        import urllib.request

        server = HTTPServer(("127.0.0.1", 0), LabHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        base = f"http://{host}:{port}"

        def request(method, path, data=None, headers=None):
            url = base + path
            req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
            try:
                resp = urllib.request.urlopen(req, timeout=5)
                body = resp.read().decode("utf-8")
                if not body:
                    return resp.status, {}
                return resp.status, json.loads(body)
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8")
                try:
                    return e.code, json.loads(body)
                except Exception:
                    return e.code, {"raw": body}

        yield request
        server.shutdown()

    def test_api_project_not_found(self, client):
        status, body = client("GET", "/api/project/does_not_exist")
        assert status == 404
        assert "error" in body

    def test_api_export_not_found(self, client):
        status, body = client("GET", "/api/export/does_not_exist")
        assert status == 404

    def test_serve_demo_lab_index(self, tmp_path: Path, monkeypatch):
        import threading
        import urllib.request
        from http.server import HTTPServer

        monkeypatch.setattr(
            "lookbook.lab_server.PROJECTS_ROOT", tmp_path / "lab_projects"
        )
        server = HTTPServer(("127.0.0.1", 0), LabHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        resp = urllib.request.urlopen(f"http://{host}:{port}/", timeout=5)
        html = resp.read().decode("utf-8")
        server.shutdown()
        assert resp.status == 200
        assert "Demo Lab" in html

    def test_build_living_panels(self, client, tmp_path: Path, monkeypatch):
        import threading
        import urllib.request
        from http.server import HTTPServer
        from PIL import Image, ImageDraw

        monkeypatch.setattr(
            "lookbook.lab_server.PROJECTS_ROOT", tmp_path / "lab_projects"
        )
        project_id = "abc12345"
        project_dir = tmp_path / "lab_projects" / project_id
        project_dir.mkdir(parents=True)
        init_project(project_dir, "test")
        img = Image.new("RGB", (400, 300), "white")
        draw = ImageDraw.Draw(img)
        draw.rectangle([10, 10, 190, 290], outline="black", width=4)
        draw.rectangle([210, 10, 390, 290], outline="black", width=4)
        img.save(project_dir / "source.png")

        from lookbook.pipeline.panels import detect_panels

        detect_panels(project_dir / "source.png", project_dir)

        server = HTTPServer(("127.0.0.1", 0), LabHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        payload = json.dumps({"project_id": project_id}).encode()
        req = urllib.request.Request(
            f"http://{host}:{port}/api/build-living-panels",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=10)
        body = json.loads(resp.read().decode())
        server.shutdown()
        assert body["choreography_lines"] >= 1
        assert (project_dir / "analysis" / "choreography.json").exists()

    def test_options_cors(self, client):
        status, _ = client("OPTIONS", "/api/analyze")
        assert status == 204

    def test_post_analyze_no_file(self, client):
        status, body = client("POST", "/api/analyze", data=b"")
        assert status == 400
        assert "error" in body

    def test_api_director_missing_project(self, client):
        status, body = client(
            "POST",
            "/api/director",
            data=json.dumps({"project_id": "missing", "target": "runway"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        assert status == 404
