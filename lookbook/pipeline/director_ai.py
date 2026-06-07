"""lookBOOK — Director AI (M2: Scene Understanding & Director AI)

Synthesizes vision-enhanced scene/shot graphs into director-level
creative decisions: pacing, emotional arc, camera language, and
platform-specific style presets.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import get_config
from ..schemas import Shot, ShotGraph, SceneGraph, DirectorDecision


EMOTIONAL_PALETTE = {
    "tense": "Tight framing, shallow focus, slightly faster cuts.",
    "action": "Dynamic camera, handheld feel, quick pans, impact frames.",
    "melancholy": "Slow dolly, desaturated tones, wide negative space.",
    "triumphant": "Crane up, warm lighting, sweeping wide reveals.",
    "mysterious": "Low-key lighting, slow push-in, hidden faces.",
    "dialogue": "Two-shot or over-shoulder, subtle breathing motion.",
}

CAMERA_LANGUAGE = {
    "runway": "Cinematic motion prompts with explicit camera verbs. Prefer gentle, continuous moves.",
    "veo": "Natural language cinematic prose. Emphasize atmosphere and character motivation.",
    "kling": "Keyword-heavy technical direction. Specify shot size, lens, and motion type.",
    "pika": "Vivid descriptive language with strong visual verbs.",
    "luma": "Structured scene description with clear spatial relationships.",
}

STYLE_PRESETS = {
    "runway": ["cinematic", "smooth camera", "character consistent"],
    "veo": ["photorealistic", "natural lighting", "cinematic color grade"],
    "kling": ["high detail", "stable motion", "professional composition"],
    "pika": ["vivid color", "expressive motion", "anime-friendly"],
    "luma": ["spatial accuracy", "temporal coherence", "clean edges"],
}

NEGATIVE_PROMPTS = {
    "default": (
        "slideshow, pan and zoom only, still image, static, "
        "character design changes, morphing, duplicated limbs, distorted faces"
    ),
    "runway": (
        "slideshow, pan and zoom only, still image, static, "
        "character design changes, morphing, duplicated limbs, distorted faces, "
        "watermark, text overlay, blurry motion"
    ),
    "veo": (
        "static image, no motion, camera only movement, "
        "character inconsistency, extra limbs, deformed anatomy, "
        "noise, oversaturated, flickering"
    ),
    "kling": (
        "low quality, blurry, jitter, unstable camera, "
        "character mutation, duplicated body parts, watermark"
    ),
    "pika": (
        "static frame, no character motion, only background moving, "
        "anatomical errors, inconsistent style"
    ),
    "luma": (
        "spatial inconsistency, temporal flicker, object popping, "
        "static camera with no parallax, morphing characters"
    ),
}


def _infer_emotion(shots: list[dict[str, Any]]) -> str:
    """Naive emotion inference from shot types and dialogue density."""
    types = [s.get("type", "") for s in shots]
    dialogue_count = sum(len(s.get("dialogue", [])) for s in shots)
    action_count = types.count("action")
    transition_count = types.count("transition")

    if action_count > len(shots) * 0.4:
        return "action"
    if transition_count > len(shots) * 0.3:
        return "mysterious"
    if dialogue_count > len(shots) * 2:
        return "dialogue"
    if "climax" in types or "resolution" in types:
        return "triumphant"
    return "tense"


def generate_director_decisions(
    project: str | Path,
    target: str = "runway",
    shot_graph_path: str | Path | None = None,
) -> DirectorDecision:
    """Generate director-level creative decisions from shot/scene data."""
    project = Path(project)

    # Prefer vision-enhanced shot graph
    if shot_graph_path is None:
        vision_path = project / "analysis" / "shot_graph_vision.json"
        classical_path = project / "analysis" / "shot_graph.json"
        shot_graph_path = vision_path if vision_path.exists() else classical_path

    if not shot_graph_path.exists():
        raise FileNotFoundError(f"Shot graph not found at {shot_graph_path}")

    data = json.loads(shot_graph_path.read_text(encoding="utf-8"))
    shots = data.get("shots", [])

    emotion = _infer_emotion(shots)
    pacing = EMOTIONAL_PALETTE.get(emotion, "")
    camera = CAMERA_LANGUAGE.get(target, "")
    presets = STYLE_PRESETS.get(target, [])
    negative = NEGATIVE_PROMPTS.get(target, NEGATIVE_PROMPTS["default"])

    # Build emotional arc text
    arc_parts = [f"Opening: {emotion.title()} atmosphere."]
    if len(shots) > 3:
        arc_parts.append("Rising action through mid-sequence shots.")
        arc_parts.append("Climax and resolution in final shots.")
    arc = " ".join(arc_parts)

    return DirectorDecision(
        target=target,
        pacing_notes=pacing,
        emotional_arc=arc,
        camera_language=camera,
        style_presets=presets,
        quality_threshold="high",
        negative_prompt_override=negative,
    )


def apply_director_to_shots(
    project: str | Path,
    target: str = "runway",
) -> list[dict[str, Any]]:
    """Enrich existing shots with director AI decisions."""
    project = Path(project)
    decision = generate_director_decisions(project, target=target)

    vision_path = project / "analysis" / "shot_graph_vision.json"
    classical_path = project / "analysis" / "shot_graph.json"
    shot_graph_path = vision_path if vision_path.exists() else classical_path

    data = json.loads(shot_graph_path.read_text(encoding="utf-8"))
    shots = data.get("shots", [])

    enriched = []
    for shot in shots:
        enriched_shot = dict(shot)
        enriched_shot["director_notes"] = {
            "pacing": decision.pacing_notes,
            "emotional_arc": decision.emotional_arc,
            "camera_language": decision.camera_language,
            "style_presets": decision.style_presets,
        }
        # Override negative prompt if not already set by vision
        if not enriched_shot.get("negative_prompt"):
            enriched_shot["negative_prompt"] = decision.negative_prompt_override
        enriched.append(enriched_shot)

    return enriched


def export_director_packet(project: str | Path, target: str = "runway") -> Path:
    """Write a director's packet (markdown) for manual review or handoff."""
    project = Path(project)
    decision = generate_director_decisions(project, target=target)
    enriched = apply_director_to_shots(project, target=target)

    out_dir = project / "exports" / "director_ai"
    out_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Director AI Packet — {target.upper()}",
        "",
        "## Creative Direction",
        f"**Emotional Arc:** {decision.emotional_arc}",
        f"**Pacing:** {decision.pacing_notes}",
        f"**Camera Language:** {decision.camera_language}",
        f"**Style Presets:** {', '.join(decision.style_presets)}",
        f"**Quality Threshold:** {decision.quality_threshold}",
        "",
        "## Negative Prompt",
        decision.negative_prompt_override,
        "",
        "## Shot Director Notes",
        "",
    ]
    for s in enriched[:20]:
        notes = s.get("director_notes", {})
        lines.append(f"### Shot {s['shot_index']:03d} — {s['type'].title()}")
        lines.append(f"- **Pacing:** {notes.get('pacing', 'N/A')}")
        lines.append(f"- **Motion:** {s.get('motion_directive', 'N/A')}")
        lines.append(f"- **Negative:** {s.get('negative_prompt', 'N/A')}")
        lines.append("")

    path = out_dir / f"DIRECTOR_PACKET_{target.upper()}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
