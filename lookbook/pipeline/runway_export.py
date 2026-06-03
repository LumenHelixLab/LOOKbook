from __future__ import annotations
from pathlib import Path
from typing import Any
import json
from ..models import write_json


def export_runway(
    project: str | Path,
    shot_graph_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Export shot graph to Runway ML Gen-3/Gen-4 compatible workflow.

    Generates a list of image-to-video job configurations, one per shot,
    compatible with Runway's API and web UI drag-and-drop.

    Args:
        project: lookBOOK project path
        shot_graph_path: Path to shot_graph.json (auto-detected)

    Returns:
        List of Runway job configs with prompts, durations, and keyframe refs.
    """
    project = Path(project)

    if shot_graph_path is None:
        shot_graph_path = project / "analysis" / "shot_graph.json"
    if not shot_graph_path.exists():
        raise FileNotFoundError(f"Shot graph not found at {shot_graph_path}. Run 'lookbook build-shot-graph' first.")

    shot_data = json.loads(shot_graph_path.read_text(encoding="utf-8"))
    shots = shot_data.get("shots", [])

    if not shots:
        raise ValueError("No shots found in shot graph.")

    # Camera move mapping to Runway motion prompts
    CAMERA_TO_RUNWAY = {
        "pan right": "Camera pans right across scene",
        "pan left": "Camera pans left across scene",
        "zoom in": "Camera slowly zooms in",
        "zoom out": "Camera slowly zooms out",
        "dolly in": "Camera dollies forward",
        "dolly out": "Camera pulls back",
        "tilt up": "Camera tilts upward",
        "tilt down": "Camera tilts downward",
        "static": "Static camera, gentle micro-movement only",
        "crane up": "Camera cranes upward",
        "crane down": "Camera descends",
        "track right": "Camera tracks right alongside action",
        "track left": "Camera tracks left alongside action",
        "push in": "Camera pushes in for emphasis",
        "pull out": "Camera pulls out to reveal context",
    }

    runway_jobs: list[dict[str, Any]] = []
    shot_dir = project / "exports" / "runway"
    shot_dir.mkdir(parents=True, exist_ok=True)

    for i, shot in enumerate(shots):
        camera_desc = CAMERA_TO_RUNWAY.get(shot.get("camera", "static"), "Static camera")
        dialogue_text = " ".join(shot.get("dialogue", []))
        narration_text = " ".join(shot.get("narration", []))

        # Build a rich motion prompt
        prompt_parts = [camera_desc]
        if shot.get("type") == "transition":
            prompt_parts.insert(0, "Soft transition between scenes.")
        elif shot.get("type") == "dialogue" and dialogue_text:
            prompt_parts.append(f"Character speaking: {dialogue_text[:200]}")
            prompt_parts.append("Subtle mouth and body motion during dialogue.")
        elif shot.get("type") == "action":
            prompt_parts.append("Dynamic action sequence with physical motion.")

        characters = shot.get("characters", [])
        if characters:
            prompt_parts.append(f"Characters: {', '.join(characters)}.")

        if narration_text:
            prompt_parts.append(f"Scene atmosphere: {narration_text[:150]}")

        # Add motion directive
        motion = shot.get("motion_directive", "")
        if motion:
            prompt_parts.append(motion)

        job = {
            "job_index": i,
            "shot_index": shot["shot_index"],
            "type": shot.get("type", "establishing"),
            "duration_seconds": shot["duration_seconds"],
            "frame_count": int(shot["duration_seconds"] * 24),
            "prompt": " ".join(prompt_parts),
            "negative_prompt": (
                "slideshow, pan and zoom only, still image, static, "
                "character design changes, morphing, duplicated limbs, distorted faces"
            ),
            "panel_refs": shot.get("panels", []),
            "transition": shot.get("transition_in", "cut"),
            "characters": characters,
        }
        runway_jobs.append(job)

    export = {
        "schema": "lookbook.runway_export.v0.2",
        "total_jobs": len(runway_jobs),
        "total_duration_seconds": shot_data.get("total_duration_seconds", 0),
        "fps": shot_data.get("fps", 24),
        "jobs": runway_jobs,
    }

    export_path = shot_dir / "runway_workflow.json"
    write_json(export_path, export)

    # Also write a readable summary
    lines = ["# Runway ML Workflow Export", "", "## Shot-by-Shot Breakdown", ""]
    for j in runway_jobs:
        lines.append(f"### Shot {j['shot_index']:03d} — {j['type'].title()} ({j['duration_seconds']}s)")
        lines.append(f"Prompt: {j['prompt'][:120]}...")
        lines.append(f"Panels: {j['panel_refs']}")
        lines.append("")
    (shot_dir / "RUNWAY_WORKFLOW.md").write_text("\n".join(lines), encoding="utf-8")

    return runway_jobs
