from __future__ import annotations
from pathlib import Path
from typing import Any
import json
from ..models import write_json


def build_shot_graph(
    project: str | Path,
    scene_graph_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Generate a shot-by-shot breakdown for animation handoff.

    Converts each scene into a timed shot list with camera cues,
    motion directives, and panel transitions, ready for Runway/Veo/Kling
    integration.

    Args:
        project: lookBOOK project path
        scene_graph_path: Path to scene_graph.json (auto-detected)

    Returns:
        List of shot dicts, each with timing, camera instruction, and panel refs.
    """
    project = Path(project)

    if scene_graph_path is None:
        scene_graph_path = project / "analysis" / "scene_graph.json"

    if not scene_graph_path.exists():
        raise FileNotFoundError(
            f"Scene graph not found at {scene_graph_path}. Run 'lookbook build-scene-graph' first."
        )

    scene_data = json.loads(scene_graph_path.read_text(encoding="utf-8"))
    scenes = scene_data.get("scenes", [])

    if not scenes:
        raise ValueError("No scenes found in scene graph.")

    # Camera transition vocabulary
    CAMERA_MOVES = [
        "pan right",
        "pan left",
        "zoom in",
        "zoom out",
        "dolly in",
        "dolly out",
        "tilt up",
        "tilt down",
        "static",
        "crane up",
        "crane down",
        "track right",
        "track left",
        "push in",
        "pull out",
    ]

    TRANSITIONS = ["cut", "fade in", "fade out", "dissolve", "wipe left", "wipe right"]

    shot_timing = {
        "establishing": 4.0,  # seconds
        "dialogue": 3.5,
        "action": 2.5,
        "transition": 1.0,
    }

    shots: list[dict[str, Any]] = []
    total_time = 0.0

    for scene in scenes:
        panel_indices = scene.get("panel_indices", [])
        panel_count = scene.get("panel_count", len(panel_indices))
        dialogue = scene.get("dialogue", [])
        narration = scene.get("narration", [])

        if panel_count == 0:
            continue

        # Establishing shot for the scene

        # Deterministic camera move from scene index
        cam_idx = scene["scene_index"] % len(CAMERA_MOVES)
        trans_idx = (scene["scene_index"] + 1) % len(TRANSITIONS)

        # Determine shot type from content
        has_dialogue = len(dialogue) > 0
        has_action = len(narration) > 0

        if has_dialogue:
            shot_type = "dialogue"
        elif has_action:
            shot_type = "action"
        else:
            shot_type = "establishing"

        duration = shot_timing.get(shot_type, 3.0)

        # Adjust duration for dialogue-heavy scenes
        if has_dialogue:
            # Rough timing: ~3 words per second
            words = sum(len(d.split()) for d in dialogue)
            duration = max(duration, words / 3.0)

        shot = {
            "shot_index": len(shots),
            "scene_index": scene["scene_index"],
            "type": shot_type,
            "duration_seconds": round(duration, 1),
            "start_time": round(total_time, 1),
            "end_time": round(total_time + duration, 1),
            "panels": panel_indices,
            "panel_count": panel_count,
            "camera": CAMERA_MOVES[cam_idx],
            "transition_in": TRANSITIONS[trans_idx],
            "dialogue": dialogue,
            "narration": narration,
            "characters": scene.get("characters", []),
            "motion_directive": _generate_motion_directive(shot_type, panel_count, has_dialogue),
        }

        shots.append(shot)
        total_time += duration

        # Add a transition shot between scenes if not the last scene
        if scene["scene_index"] < len(scenes) - 1:
            trans_shot = {
                "shot_index": len(shots),
                "scene_index": scene["scene_index"],
                "type": "transition",
                "duration_seconds": shot_timing["transition"],
                "start_time": round(total_time, 1),
                "end_time": round(total_time + shot_timing["transition"], 1),
                "panels": [],
                "panel_count": 0,
                "camera": "static",
                "transition_in": "dissolve",
                "dialogue": [],
                "narration": [],
                "characters": [],
                "motion_directive": "Transition between scenes.",
            }
            shots.append(trans_shot)
            total_time += shot_timing["transition"]

    result = {
        "schema": "lookbook.shot_graph.v0.2",
        "source_file": scene_data.get("source_file", str(project / "source")),
        "total_shots": len(shots),
        "total_duration_seconds": round(total_time, 1),
        "fps": 24,
        "frames": int(total_time * 24),
        "shots": shots,
    }

    analysis_dir = project / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    write_json(analysis_dir / "shot_graph.json", result)

    return shots


def _generate_motion_directive(shot_type: str, panel_count: int, has_dialogue: bool) -> str:
    """Generate a human-readable motion directive for the shot."""
    if shot_type == "establishing":
        return (
            f"Slow establishing view across {panel_count} panel area. "
            "Gentle pan to reveal scene layout."
        )
    elif shot_type == "dialogue":
        return (
            "Focus on character interaction. "
            "Subtle zoom during dialogue exchange. "
            "Maintain eye-line continuity between speakers."
        )
    elif shot_type == "action":
        return (
            "Dynamic camera movement. "
            "Quick cuts between action beats. "
            "Emphasize motion with whip pans on impact."
        )
    return "Static frame with gentle micro-movement."
