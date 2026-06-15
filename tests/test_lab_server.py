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

    def test_serve_demo_lab_index(self, client):
        status, body = client("GET", "/")
        assert status == 200
        assert isinstance(body, dict) is False or "error" not in body
        # client JSON-parses all bodies; re-request raw for HTML
        import urllib.request
        from http.server import HTTPServer
        import threading

        server = HTTPServer(("127.0.0.1", 0), LabHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        resp = urllib.request.urlopen(f"http://{host}:{port}/", timeout=5)
        html = resp.read().decode("utf-8")
        server.shutdown()
        assert "Demo Lab" in html

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
