"""Tests for lookBOOK Pydantic schemas (M5)."""

import pytest
from lookbook.schemas import (
    BBox,
    Panel,
    Character,
    CharacterAppearance,
    Shot,
    ShotGraph,
    Scene,
    DirectorDecision,
)


class TestBBox:
    def test_defaults(self):
        b = BBox()
        assert b.x == 0
        assert b.width == 0

    def test_values(self):
        b = BBox(x=10, y=20, width=100, height=200)
        assert b.x == 10
        assert b.height == 200


class TestPanel:
    def test_panel(self):
        p = Panel(panel_index=0, bbox=BBox(x=0, y=0, width=100, height=100))
        assert p.panel_index == 0
        assert p.bbox.width == 100


class TestCharacter:
    def test_character(self):
        c = Character(
            character_id="char_001",
            name="Hero",
            appearances=2,
            panels=[
                CharacterAppearance(panel_index=0, image_path="p0.png"),
            ],
        )
        assert c.name == "Hero"
        assert c.appearances == 2
        assert len(c.panels) == 1


class TestShot:
    def test_defaults(self):
        s = Shot(shot_index=0)
        assert s.duration_seconds == 3.0
        assert s.frame_count == 72

    def test_frame_count(self):
        s = Shot(shot_index=0, duration_seconds=5.0)
        assert s.frame_count == 120


class TestShotGraph:
    def test_shot_graph(self):
        sg = ShotGraph(
            total_shots=1,
            shots=[Shot(shot_index=0, duration_seconds=4.0)],
        )
        assert sg.total_shots == 1
        assert sg.shots[0].frame_count == 96


class TestScene:
    def test_scene(self):
        sc = Scene(
            scene_index=0,
            panel_indices=[0, 1],
            characters=["Hero"],
        )
        assert sc.panel_count == 0  # default, not auto-calculated
        assert sc.characters == ["Hero"]


class TestDirectorDecision:
    def test_decision(self):
        d = DirectorDecision(
            target="runway",
            emotional_arc="Tense opening.",
            style_presets=["cinematic"],
        )
        assert d.target == "runway"
        assert d.quality_threshold == "high"
