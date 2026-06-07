from __future__ import annotations
from pathlib import Path
import json
import pytest


@pytest.fixture
def project_with_scenes(tmp_path: Path) -> Path:
    project = tmp_path / "test_project"
    project.mkdir(parents=True)
    (project / "analysis").mkdir()
    (project / "source").mkdir()
    (project / "exports").mkdir()
    (project / "manifest.json").write_text(json.dumps({"project": "Test", "format_version": "0.2"}))

    shot_graph = {
        "schema": "lookbook.shot_graph.v0.2",
        "source_file": "test.png",
        "total_shots": 2,
        "total_duration_seconds": 9.0,
        "fps": 24,
        "shots": [
            {
                "shot_index": 0,
                "scene_index": 0,
                "type": "establishing",
                "duration_seconds": 4.0,
                "start_time": 0.0,
                "end_time": 4.0,
                "panels": [0, 1],
                "panel_count": 2,
                "camera": "pan right",
                "transition_in": "fade in",
                "dialogue": [],
                "narration": ["The scene opens."],
                "characters": [],
                "motion_directive": "Slow pan across the scene.",
            },
            {
                "shot_index": 1,
                "scene_index": 0,
                "type": "dialogue",
                "duration_seconds": 5.0,
                "start_time": 4.0,
                "end_time": 9.0,
                "panels": [2],
                "panel_count": 1,
                "camera": "zoom in",
                "transition_in": "cut",
                "dialogue": ['"Hello."'],
                "narration": [],
                "characters": ["char_000"],
                "motion_directive": "Focus on character.",
            },
        ],
    }
    (project / "analysis" / "shot_graph.json").write_text(json.dumps(shot_graph))
    return project


class TestRemotionExport:
    def test_export_remotion(self, project_with_scenes):
        from lookbook.pipeline.remotion_export import export_remotion

        result = export_remotion(project_with_scenes)
        assert result["total_shots"] == 2
        assert result["total_duration_seconds"] == 9.0
        assert result["fps"] == 24

        export_dir = project_with_scenes / "exports" / "remotion"
        assert (export_dir / "src" / "Root.tsx").exists()
        assert (export_dir / "src" / "Shot000.tsx").exists()
        assert (export_dir / "src" / "Shot001.tsx").exists()
        assert (export_dir / "src" / "index.ts").exists()
        assert (export_dir / "package.json").exists()
        assert (export_dir / "tsconfig.json").exists()
        assert (export_dir / "README.md").exists()

        # Verify Root.tsx references both shots
        root = (export_dir / "src" / "Root.tsx").read_text()
        assert "Shot000" in root
        assert "Shot001" in root
        assert "RemotionRoot" in root

        # Verify package.json
        pkg = json.loads((export_dir / "package.json").read_text())
        assert pkg["name"] == "lookbook-remotion-export"
        assert "remotion" in pkg["dependencies"]

    def test_export_remotion_custom_fps(self, project_with_scenes):
        from lookbook.pipeline.remotion_export import export_remotion

        result = export_remotion(project_with_scenes, fps=30)
        assert result["fps"] == 30
        export_dir = project_with_scenes / "exports" / "remotion"
        pkg = json.loads((export_dir / "package.json").read_text())
        assert "remotion" in pkg["dependencies"]

    def test_export_remotion_no_sg(self, tmp_path):
        from lookbook.pipeline.remotion_export import export_remotion

        with pytest.raises(FileNotFoundError):
            export_remotion(tmp_path)

    def test_export_remotion_cli(self, project_with_scenes):
        from lookbook.cli import main

        main(["export-remotion", str(project_with_scenes)])
        assert (project_with_scenes / "exports" / "remotion" / "src" / "Root.tsx").exists()
