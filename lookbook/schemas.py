"""lookBOOK — Pydantic schemas for pipeline data contracts.

Provides strict validation for panels, characters, scenes, and shots
so downstream exporters can rely on field presence and types.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any


class BBox(BaseModel):
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0


class Panel(BaseModel):
    panel_index: int
    bbox: BBox = Field(default_factory=BBox)
    area: float = 0.0
    aspect_ratio: float = 0.0
    image_path: str | None = None
    classification: str | None = None


class TextBlock(BaseModel):
    text: str
    classification: str = "unknown"
    bbox: BBox = Field(default_factory=BBox)


class CharacterAppearance(BaseModel):
    panel_index: int
    bbox: BBox = Field(default_factory=BBox)
    image_path: str | None = None


class Character(BaseModel):
    character_id: str
    name: str = "Unknown"
    description: str = ""
    appearances: int = 0
    panels: list[CharacterAppearance] = Field(default_factory=list)


class Scene(BaseModel):
    scene_index: int
    panel_count: int = 0
    panel_indices: list[int] = Field(default_factory=list)
    panels: list[Panel] = Field(default_factory=list)
    characters: list[str] = Field(default_factory=list)
    dialogue: list[str] = Field(default_factory=list)
    narration: list[str] = Field(default_factory=list)


class Shot(BaseModel):
    shot_index: int
    scene_index: int = 0
    type: str = "establishing"
    duration_seconds: float = 3.0
    start_time: float = 0.0
    end_time: float = 0.0
    panels: list[int] = Field(default_factory=list)
    panel_count: int = 0
    camera: str = "static"
    transition_in: str = "cut"
    dialogue: list[str] = Field(default_factory=list)
    narration: list[str] = Field(default_factory=list)
    characters: list[str] = Field(default_factory=list)
    motion_directive: str = ""
    negative_prompt: str = ""
    motion_score: float | None = None

    @property
    def frame_count(self) -> int:
        return int(self.duration_seconds * 24)


class ShotGraph(BaseModel):
    schema_version: str = Field(default="lookbook.shot_graph.v0.3", alias="schema")
    total_shots: int = 0
    total_duration_seconds: float = 0.0
    fps: int = 24
    frames: int = 0
    shots: list[Shot] = Field(default_factory=list)
    vision_cost_usd: float | None = None
    vision_calls: int | None = None


class SceneGraph(BaseModel):
    schema_version: str = Field(default="lookbook.scene_graph.v0.3", alias="schema")
    total_scenes: int = 0
    scenes: list[Scene] = Field(default_factory=list)
    vision_cost_usd: float | None = None
    vision_calls: int | None = None


class CharacterAnalysis(BaseModel):
    schema_version: str = Field(default="lookbook.characters.v0.3", alias="schema")
    method: str = "classical"
    provider: str | None = None
    total_characters: int = 0
    characters: list[Character] = Field(default_factory=list)
    vision_cost_usd: float | None = None
    vision_calls: int | None = None


class PanelAnalysis(BaseModel):
    schema_version: str = Field(default="lookbook.panels.v0.3", alias="schema")
    total_panels: int = 0
    panels: list[Panel] = Field(default_factory=list)
    source_width: int | None = None
    source_height: int | None = None


class DirectorDecision(BaseModel):
    """Director AI output — high-level creative decisions per scene or shot."""

    target: str  # e.g. "runway", "veo", "kling"
    pacing_notes: str = ""
    emotional_arc: str = ""
    camera_language: str = ""
    style_presets: list[str] = Field(default_factory=list)
    quality_threshold: str = "high"
    negative_prompt_override: str = ""
