from __future__ import annotations
from pathlib import Path
import json
import pytest


# ---- Fixtures ----


@pytest.fixture
def project_with_scenes(tmp_path: Path) -> Path:
    """Create a project with mock scene_graph.json and shot_graph.json."""
    project = tmp_path / "test_project"
    project.mkdir(parents=True)
    (project / "analysis").mkdir()
    (project / "source").mkdir()
    (project / "exports").mkdir()

    # Write manifest
    (project / "manifest.json").write_text(
        json.dumps({"project": "Test", "format_version": "0.2"})
    )

    # Write mock shot graph
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
                "narration": ["The scene opens on a vast landscape."],
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
                "dialogue": ['"Hello, this is a test."'],
                "narration": [],
                "characters": ["char_000"],
                "motion_directive": "Focus on character interaction.",
            },
        ],
    }
    (project / "analysis" / "shot_graph.json").write_text(json.dumps(shot_graph))

    return project


# ---- Runway Export Tests ----


class TestRunwayExport:
    def test_export_runway(self, project_with_scenes):
        from lookbook.pipeline.runway_export import export_runway

        jobs = export_runway(project_with_scenes)
        assert len(jobs) == 2
        assert jobs[0]["job_index"] == 0
        assert jobs[0]["type"] == "establishing"
        assert jobs[0]["duration_seconds"] == 4.0
        assert "camera" in jobs[0]["prompt"].lower() or "pan" in jobs[0]["prompt"].lower()
        assert "negative_prompt" in jobs[0]

        # Check output files
        export_dir = project_with_scenes / "exports" / "runway"
        assert (export_dir / "runway_workflow.json").exists()
        assert (export_dir / "RUNWAY_WORKFLOW.md").exists()

    def test_export_runway_no_sg(self, tmp_path):
        from lookbook.pipeline.runway_export import export_runway

        with pytest.raises(FileNotFoundError):
            export_runway(tmp_path)


# ---- Veo Export Tests ----


class TestVeoExport:
    def test_export_veo(self, project_with_scenes):
        from lookbook.pipeline.veo_export import export_veo

        prompts = export_veo(project_with_scenes)
        assert len(prompts) == 2
        assert prompts[0]["shot_index"] == 0
        assert "camera" in prompts[0]["prompt"].lower()
        assert "duration_seconds" in prompts[0]

        # Shot with dialogue should reference it
        assert "Hello, this is a test" in prompts[1]["prompt"]

        # Check output files
        export_dir = project_with_scenes / "exports" / "veo"
        assert (export_dir / "veo_prompts.json").exists()
        assert (export_dir / "VEO_PROMPT_SEQUENCE.md").exists()


# ---- Kling/Pika/Luma Export Tests ----


class TestKlingExport:
    def test_export_kling(self, project_with_scenes):
        from lookbook.pipeline.kling_export import export_kling

        result = export_kling(project_with_scenes)
        assert set(result.keys()) == {"kling", "pika", "luma"}

        for platform, entries in result.items():
            assert len(entries) == 2
            assert all("prompt" in e for e in entries)
            assert all("negative_prompt" in e for e in entries)
            assert all("shot_index" in e for e in entries)

        # Kling should have keyword-style prompts
        assert len(result["kling"][0]["prompt"].split(",")) >= 2

        # Check output files
        for platform in ("kling", "pika", "luma"):
            export_dir = project_with_scenes / "exports" / platform
            assert (export_dir / f"{platform}_prompts.json").exists()
            assert (export_dir / f"{platform.upper()}_PROMPTS.md").exists()


# ---- ComfyUI Export Tests ----


class TestComfyUIExport:
    def test_export_comfyui(self, project_with_scenes):
        from lookbook.pipeline.comfyui_export import export_comfyui

        wfs = export_comfyui(project_with_scenes)
        assert len(wfs) == 2
        for wf in wfs:
            assert "workflow" in wf
            assert "positive_prompt" in wf
            assert "negative_prompt" in wf
            assert wf["model"] == "realisticVisionV51_v51VAE.safetensors"
            # Verify workflow structure
            workflow = wf["workflow"]
            assert "1" in workflow  # KSampler
            assert "3" in workflow  # CLIPTextEncode (positive)
            assert "4" in workflow  # CLIPTextEncode (negative)

        # Check individual workflow files
        export_dir = project_with_scenes / "exports" / "comfyui"
        assert (export_dir / "workflow_shot_000.json").exists()
        assert (export_dir / "workflow_shot_001.json").exists()
        assert (export_dir / "comfyui_workflow_pack.json").exists()

    def test_export_comfyui_custom_res(self, project_with_scenes):
        from lookbook.pipeline.comfyui_export import export_comfyui

        wfs = export_comfyui(project_with_scenes, width=1920, height=1080)
        workflow = wfs[0]["workflow"]
        assert workflow["5"]["inputs"]["width"] == 1920
        assert workflow["5"]["inputs"]["height"] == 1080


# ---- FFmpeg Export Tests ----


class TestFFmpegExport:
    def test_export_ffmpeg(self, project_with_scenes):
        from lookbook.pipeline.ffmpeg_export import export_ffmpeg

        result = export_ffmpeg(project_with_scenes)
        assert result["total_shots"] == 2
        assert result["total_duration_seconds"] == 9.0
        assert result["fps"] == 24
        assert "file_list.txt" in result["file_list"]

        # Check output files
        export_dir = project_with_scenes / "exports" / "ffmpeg"
        assert (export_dir / "assemble.bat").exists()
        assert (export_dir / "assemble.sh").exists()
        assert (export_dir / "file_list.txt").exists()
        assert (export_dir / "ffmpeg_assembly.json").exists()

        # Check file list content
        file_list = (export_dir / "file_list.txt").read_text()
        assert "shot_000.mp4" in file_list
        assert "shot_001.mp4" in file_list


# ---- CLI Integration Tests ----


class TestCLIIntegration:
    def test_export_runway_cli(self, project_with_scenes):
        from lookbook.cli import main

        main(["export-runway", str(project_with_scenes)])
        assert (project_with_scenes / "exports" / "runway" / "runway_workflow.json").exists()

    def test_export_veo_cli(self, project_with_scenes):
        from lookbook.cli import main

        main(["export-veo", str(project_with_scenes)])
        assert (project_with_scenes / "exports" / "veo" / "veo_prompts.json").exists()

    def test_export_kling_cli(self, project_with_scenes):
        from lookbook.cli import main

        main(["export-kling", str(project_with_scenes)])
        for p in ("kling", "pika", "luma"):
            assert (project_with_scenes / "exports" / p / f"{p}_prompts.json").exists()

    def test_export_comfyui_cli(self, project_with_scenes):
        from lookbook.cli import main

        main(["export-comfyui", str(project_with_scenes)])
        assert (project_with_scenes / "exports" / "comfyui" / "comfyui_workflow_pack.json").exists()

    def test_export_ffmpeg_cli(self, project_with_scenes):
        from lookbook.cli import main

        main(["export-ffmpeg", str(project_with_scenes)])
        assert (project_with_scenes / "exports" / "ffmpeg" / "assemble.bat").exists()
