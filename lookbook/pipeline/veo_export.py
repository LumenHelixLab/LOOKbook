from __future__ import annotations
from pathlib import Path
from typing import Any
import json
from ..models import write_json


def export_veo(
    project: str | Path,
    shot_graph_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Export shot graph to Veo 2 / Gemini-compatible prompt sequences.

    Veo 2 works best with structured natural-language prompts that describe
    camera motion, character action, and scene composition in sequence.

    Args:
        project: lookBOOK project path
        shot_graph_path: Path to shot_graph.json (auto-detected)

    Returns:
        List of Veo-friendly prompt dicts with keyframe references.
    """
    project = Path(project)

    if shot_graph_path is None:
        shot_graph_path = project / "analysis" / "shot_graph.json"
    if not shot_graph_path.exists():
        raise FileNotFoundError(f"Shot graph not found at {shot_graph_path}.")

    shot_data = json.loads(shot_graph_path.read_text(encoding="utf-8"))
    shots = shot_data.get("shots", [])

    if not shots:
        raise ValueError("No shots found in shot graph.")

    # Camera mapping for Veo-style natural language
    CAMERA_TO_VEO = {
        "pan right": "The camera slowly pans to the right",
        "pan left": "The camera slowly pans to the left",
        "zoom in": "The camera pushes in closer",
        "zoom out": "The camera pulls back to reveal the scene",
        "dolly in": "The camera moves forward into the scene",
        "dolly out": "The camera moves backward from the scene",
        "tilt up": "The camera tilts upward",
        "tilt down": "The camera tilts downward",
        "static": "The camera holds steady",
        "crane up": "The camera rises upward",
        "crane down": "The camera descends",
        "track right": "The camera moves sideways to the right",
        "track left": "The camera moves sideways to the left",
        "push in": "The camera pushes in for dramatic emphasis",
        "pull out": "The camera pulls out to reveal the full scene",
    }

    veo_prompts: list[dict[str, Any]] = []
    shot_dir = project / "exports" / "veo"
    shot_dir.mkdir(parents=True, exist_ok=True)

    for i, shot in enumerate(shots):
        camera_desc = CAMERA_TO_VEO.get(shot.get("camera", "static"), "The camera holds steady")
        dialogue_text = " ".join(shot.get("dialogue", []))
        narration_text = " ".join(shot.get("narration", []))

        # Veo needs natural, cinematic prose
        paragraphs: list[str] = []

        # Scene description
        char_str = ", ".join(shot.get("characters", [])) if shot.get("characters") else "figures"
        paragraphs.append(f"A cinematic shot featuring {char_str}.")

        # Action / motion
        motion = shot.get("motion_directive", "")
        if motion:
            paragraphs.append(motion)

        # Camera + duration
        dur = shot["duration_seconds"]
        paragraphs.append(f"{camera_desc} over {dur:.0f} seconds.")

        # Dialogue (Veo handles this well)
        if dialogue_text:
            paragraphs.append(f"Dialogue: {dialogue_text[:300]}")

        # Atmosphere
        if narration_text:
            paragraphs.append(f"Mood: {narration_text[:200]}")

        prompt_text = " ".join(paragraphs)

        entry = {
            "shot_index": shot["shot_index"],
            "type": shot.get("type", "establishing"),
            "duration_seconds": dur,
            "prompt": prompt_text,
            "negative_prompt": (
                "Slideshow effect, static image, pan and zoom only, "
                "character warping, morphing faces, unnatural movement"
            ),
            "panel_refs": shot.get("panels", []),
            "transition": shot.get("transition_in", "cut"),
        }
        veo_prompts.append(entry)

    export = {
        "schema": "lookbook.veo_export.v0.2",
        "total_prompts": len(veo_prompts),
        "total_duration_seconds": shot_data.get("total_duration_seconds", 0),
        "fps": shot_data.get("fps", 24),
        "model_recommendation": "Veo 2 or Gemini 2.0 Flash with image-to-video",
        "prompts": veo_prompts,
    }

    export_path = shot_dir / "veo_prompts.json"
    write_json(export_path, export)

    # Write readable prompt pack
    lines = ["# Veo 2 / Gemini Prompt Sequence", "", "## Shot Prompts", ""]
    for p in veo_prompts:
        lines.append(
            f"### Shot {p['shot_index']:03d} — {p['type'].title()} ({p['duration_seconds']}s)"
        )
        lines.append(p["prompt"])
        lines.append("")
    (shot_dir / "VEO_PROMPT_SEQUENCE.md").write_text("\n".join(lines), encoding="utf-8")

    return veo_prompts
