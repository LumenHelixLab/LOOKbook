"""Tests for Director AI (M2)."""

import json
import pytest
from pathlib import Path

from lookbook.pipeline.director_ai import (
    generate_director_decisions,
    apply_director_to_shots,
    export_director_packet,
    NEGATIVE_PROMPTS,
)


@pytest.fixture
def project_with_shots(tmp_path: Path):
    project = tmp_path / "proj"
    project.mkdir()
    analysis = project / "analysis"
    analysis.mkdir()
    shot_data = {
        "schema": "lookbook.shot_graph.v0.3",
        "total_shots": 2,
        "total_duration_seconds": 7.0,
        "fps": 24,
        "shots": [
            {
                "shot_index": 0,
                "scene_index": 0,
                "type": "action",
                "duration_seconds": 4.0,
                "camera": "pan right",
                "characters": ["Hero"],
                "motion_directive": "Hero leaps forward.",
                "panels": [0],
            },
            {
                "shot_index": 1,
                "scene_index": 0,
                "type": "dialogue",
                "duration_seconds": 3.0,
                "camera": "static",
                "characters": ["Hero", "Villain"],
                "dialogue": ["You won't escape!"],
                "panels": [1],
            },
        ],
    }
    (analysis / "shot_graph.json").write_text(json.dumps(shot_data), encoding="utf-8")
    return project


class TestGenerateDirectorDecisions:
    def test_basic(self, project_with_shots: Path):
        d = generate_director_decisions(project_with_shots, target="runway")
        assert d.target == "runway"
        assert d.pacing_notes
        assert d.negative_prompt_override
        assert "runway" in d.camera_language.lower() or "cinematic" in d.camera_language.lower()

    def test_emotion_inference_action(self, project_with_shots: Path):
        d = generate_director_decisions(project_with_shots, target="veo")
        # With action + dialogue shots, should map to some emotion
        assert d.emotional_arc

    def test_missing_shot_graph(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            generate_director_decisions(tmp_path, target="runway")


class TestApplyDirectorToShots:
    def test_enriches_shots(self, project_with_shots: Path):
        enriched = apply_director_to_shots(project_with_shots, target="runway")
        assert len(enriched) == 2
        assert "director_notes" in enriched[0]
        assert enriched[0].get("negative_prompt")


class TestExportDirectorPacket:
    def test_writes_md(self, project_with_shots: Path):
        path = export_director_packet(project_with_shots, target="runway")
        assert path.exists()
        text = path.read_text(encoding="utf-8")
        assert "Director AI Packet" in text
        assert "runway" in text.lower() or "Runway" in text


class TestNegativePrompts:
    def test_all_targets_have_negative(self):
        for target in ["runway", "veo", "kling", "pika", "luma"]:
            assert target in NEGATIVE_PROMPTS
            assert len(NEGATIVE_PROMPTS[target]) > 10
