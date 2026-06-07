"""lookBOOK — True Animation Packet Generator (M3: Export Pipeline 2.0)

Generates dynamic true-animation handoff documents from actual shot graph data
instead of static templates. Produces per-project, per-target prompt packs,
shot lists, and quality gates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from ..models import write_json
from .common import resolve_shot_graph
from .director_ai import generate_director_decisions


_STATIC_SHOT_LIST_FALLBACK = """# Shot List

## Shot 01 — Setup
Input keyframe: opening/standoff image.
Duration: 3-5 seconds.
Motion: characters step forward, environment moves, cloth/scarf moves, protagonist prepares to launch.

## Shot 02 — Breakout
Input keyframe: first action image.
Duration: 4-6 seconds.
Motion: protagonist dodges, strikes, disarms or redirects one attacker. Opponents react physically.

## Shot 03 — Climax
Input keyframe: takedown/restraint image.
Duration: 4-6 seconds.
Motion: protagonist restrains or defeats the heavy opponent. Secondary characters recoil.

## Shot 04 — Resolution
Input keyframe: final/climax image.
Duration: 2-4 seconds.
Motion: energy settles, opponent struggles weakly, protagonist holds final pose, dialogue resolves.
"""

_STATIC_QUALITY_FALLBACK = """# True Animation Quality Gate

Accept only if:
- at least two characters physically move
- the protagonist performs an action inside the frame
- the antagonist reacts or changes posture
- costume continuity is preserved
- motion is not merely camera movement
- dialogue or action timing is clear

Reject if:
- it is just still-image sliding
- only smoke/particles move
- the model changes the hero into a famous franchise character
- bodies melt, duplicate, or become unreadable
"""

_TRUE_ANIMATION_PROMPT_HEADER = """# TRUE ANIMATION HANDOFF PROMPT

## Non-negotiable
Generate true character animation, not a pan-and-zoom motion comic.

Characters must move inside the scene:
- body motion
- limb motion
- head turns
- attacks / reactions
- cloth/scarf/ribbon motion
- speaking timing or dialogue pacing
"""


def _build_dynamic_shot_list(shot_data: dict[str, Any]) -> str:
    lines = ["# Shot List", ""]
    shots = shot_data.get("shots", [])
    for shot in shots:
        idx = shot["shot_index"]
        stype = shot.get("type", "establishing").title()
        dur = shot["duration_seconds"]
        camera = shot.get("camera", "static")
        motion = shot.get("motion_directive", "")
        panels = shot.get("panels", [])
        chars = ", ".join(shot.get("characters", [])) or "figures"
        lines.append(f"## Shot {idx:03d} — {stype} ({dur}s)")
        lines.append(f"Input keyframe: panel(s) {panels}.")
        lines.append(f"Characters: {chars}.")
        lines.append(f"Camera: {camera}.")
        if motion:
            lines.append(f"Motion directive: {motion}.")
        lines.append("")
    return "\n".join(lines)


def _build_quality_gate(shot_data: dict[str, Any], target: str) -> str:
    total_shots = len(shot_data.get("shots", []))
    total_dur = shot_data.get("total_duration_seconds", 0)
    lines = [
        "# True Animation Quality Gate",
        "",
        f"Target platform: **{target.upper()}**",
        f"Total shots: {total_shots} | Total duration: {total_dur:.1f}s",
        "",
        "Accept only if:",
        "- at least two characters physically move",
        "- the protagonist performs an action inside the frame",
        "- the antagonist reacts or changes posture",
        "- costume continuity is preserved",
        "- motion is not merely camera movement",
        "- dialogue or action timing is clear",
        "",
        "Reject if:",
        "- it is just still-image sliding",
        "- only smoke/particles move",
        "- the model changes the hero into a famous franchise character",
        "- bodies melt, duplicate, or become unreadable",
    ]
    return "\n".join(lines)


def create_true_animation_packet(
    project: str | Path,
    target: str = "runway",
    shot_graph_path: str | Path | None = None,
) -> Path:
    """Generate a true-animation packet from actual shot graph data.

    Args:
        project: lookBOOK project path
        target: export target platform (runway, veo, kling, etc.)
        shot_graph_path: optional explicit shot graph path

    Returns:
        Path to the generated prompts directory.
    """
    project = Path(project)

    # Attempt to use actual shot graph; fall back to static template if absent
    try:
        _, shot_data = resolve_shot_graph(project, shot_graph_path)
    except FileNotFoundError:
        shot_data = None

    out = project / "prompts" / target
    out.mkdir(parents=True, exist_ok=True)

    # 1. True Animation Prompt
    prompt_text = _TRUE_ANIMATION_PROMPT_HEADER
    try:
        decision = generate_director_decisions(project, target=target)
        prompt_text += f"\n\n## Platform-Specific Direction\n\n{decision.camera_language}\n"
        prompt_text += f"\n## Style Presets\n\n- {'\n- '.join(decision.style_presets)}\n"
        prompt_text += f"\n## Negative Prompt\n\n{decision.negative_prompt_override}\n"
    except FileNotFoundError:
        prompt_text += (
            "\n\n## Platform-Specific Direction\n\n"
            "Cinematic motion prompts with explicit camera verbs.\n"
        )
        prompt_text += "\n## Negative Prompt\n\n"
        prompt_text += "slideshow, pan and zoom only, still image, static, "
        prompt_text += "character design changes, morphing, duplicated limbs, distorted faces\n"
    (out / "TRUE_ANIMATION_PROMPT.md").write_text(prompt_text, encoding="utf-8")

    # 2. Shot List
    if shot_data is not None:
        shot_list = _build_dynamic_shot_list(shot_data)
    else:
        shot_list = _STATIC_SHOT_LIST_FALLBACK
    (out / "SHOT_LIST.md").write_text(shot_list, encoding="utf-8")

    # 3. Quality Gate
    if shot_data is not None:
        quality = _build_quality_gate(shot_data, target)
    else:
        quality = _STATIC_QUALITY_FALLBACK
    (out / "QUALITY_GATE.md").write_text(quality, encoding="utf-8")

    # 4. JSON manifest
    write_json(
        project / "analysis" / f"{target}_true_animation_packet.json",
        {
            "schema": "lookbook.true_animation_packet.v0.3",
            "target": target,
            "total_shots": len(shot_data.get("shots", [])) if shot_data else 0,
            "total_duration_seconds": shot_data.get("total_duration_seconds", 0) if shot_data else 0,
            "files": [
                str((out / "TRUE_ANIMATION_PROMPT.md").relative_to(project)),
                str((out / "SHOT_LIST.md").relative_to(project)),
                str((out / "QUALITY_GATE.md").relative_to(project)),
            ],
        },
    )
    return out
