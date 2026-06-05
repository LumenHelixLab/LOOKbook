from __future__ import annotations
from pathlib import Path
from typing import Any
import json
import numpy as np
from dataclasses import dataclass, asdict


@dataclass
class FrameMetrics:
    """Per-frame analysis metrics."""
    frame_index: int
    timestamp: float
    mean_brightness: float
    color_histogram: list[float]
    edge_density: float
    optical_flow_magnitude: float | None = None
    optical_flow_angle: float | None = None


@dataclass
class ShotValidationResult:
    """Validation result for a single shot."""
    shot_index: int
    shot_type: str
    expected_duration: float
    actual_duration: float | None
    frame_count: int
    camera_motion_score: float
    character_motion_score: float
    limb_articulation_score: float
    cloth_dynamics_score: float
    dialogue_sync_score: float | None
    costume_consistency_score: float
    passes: bool
    failure_reasons: list[str]


@dataclass
class QualityReport:
    """Full quality gate report."""
    schema: str = "lookbook.quality_gate.v0.1"
    project: str = ""
    total_shots: int = 0
    passed_shots: int = 0
    failed_shots: int = 0
    overall_pass: bool = False
    shot_results: list[ShotValidationResult] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.shot_results is None:
            self.shot_results = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)