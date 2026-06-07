from __future__ import annotations
from pathlib import Path
from typing import Any
import json
from ..models import write_json
from .common import resolve_shot_graph
from .director_ai import NEGATIVE_PROMPTS


def export_kling(
    project: str | Path,
    shot_graph_path: str | Path | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Export shot graph to Kling, Pika, and Luma-optimized prompt formats.

    Each platform has different prompt style preferences:
    - Kling: short, keyword-heavy, motion-first
    - Pika: descriptive, cinematic, emoji-friendly
    - Luma: structured, technical, camera-specific
    Auto-detects vision-enhanced shot graph if available.

    Args:
        project: lookBOOK project path
        shot_graph_path: Path to shot_graph.json (auto-detected)

    Returns:
        Dict with keys 'kling', 'pika', 'luma', each containing prompt entries.
    """
    project = Path(project)
    _, shot_data = resolve_shot_graph(project, shot_graph_path)
    shots = shot_data.get("shots", [])

    if not shots:
        raise ValueError("No shots found in shot graph.")

    camera_keywords = {
        "pan right": "pan right",
        "pan left": "pan left",
        "zoom in": "zoom in, push in",
        "zoom out": "zoom out, pull back",
        "dolly in": "dolly forward",
        "dolly out": "dolly backward",
        "tilt up": "tilt up",
        "tilt down": "tilt down",
        "static": "static shot",
        "crane up": "crane up, rise",
        "crane down": "crane down, descend",
        "track right": "track right, lateral move",
        "track left": "track left, lateral move",
        "push in": "push in, dramatic zoom",
        "pull out": "pull out, reveal",
    }

    platforms = {
        "kling": {
            "style": "keyword",
            "negative": "static, slideshow, morphing, distortion, watermark",
        },
        "pika": {
            "style": "cinematic",
            "negative": "static image, slideshow, morphing, distorted faces, watermark",
        },
        "luma": {
            "style": "structured",
            "negative": "Still image, slideshow, morphing artifacts, inconsistent characters",
        },
    }

    result: dict[str, list[dict[str, Any]]] = {}

    for platform, config in platforms.items():
        platform_dir = project / "exports" / platform
        platform_dir.mkdir(parents=True, exist_ok=True)

        entries: list[dict[str, Any]] = []
        for i, shot in enumerate(shots):
            camera_kw = camera_keywords.get(shot.get("camera", "static"), "static shot")
            dialogue = " ".join(shot.get("dialogue", []))
            characters = (
                ", ".join(shot.get("characters", [])) if shot.get("characters") else "figures"
            )
            motion = shot.get("motion_directive", "")
            dur = shot["duration_seconds"]

            if platform == "kling":
                # Kling: short, keyword-heavy
                parts = [f"{characters}"]
                if dialogue:
                    parts.append(f"speaking: {dialogue[:100]}")
                parts.append(f"motion: {motion[:80]}")
                parts.append(f"camera: {camera_kw}")
                parts.append(f"duration: {dur}s")
                prompt = ", ".join(parts)

            elif platform == "pika":
                # Pika: descriptive, scenic
                lines = [f"{characters} in a cinematic scene."]
                if dialogue:
                    lines.append(f'Characters exchange: "{dialogue[:150]}"')
                lines.append(f"Camera {camera_kw}.")
                if motion:
                    lines.append(motion)
                lines.append(f"Duration: {dur:.0f} seconds.")
                prompt = " ".join(lines)

            else:  # luma
                # Luma: structured technical
                prompt = (
                    f"Shot: {characters}. "
                    f"Camera: {camera_kw}. "
                    f"Motion: {motion[:120]}. "
                    f"{'Dialogue: ' + dialogue[:150] + '. ' if dialogue else ''}"
                    f"Duration: {dur:.0f}s."
                )

            negative = shot.get("negative_prompt", "")
            if not negative:
                negative = NEGATIVE_PROMPTS.get(platform, NEGATIVE_PROMPTS["default"])

            entry = {
                "shot_index": shot["shot_index"],
                "type": shot.get("type", "establishing"),
                "duration_seconds": dur,
                "prompt": prompt,
                "negative_prompt": negative,
                "panel_refs": shot.get("panels", []),
                "director_notes": shot.get("director_notes", {}),
            }
            entries.append(entry)

        export = {
            "schema": f"lookbook.{platform}_export.v0.2",
            "total_prompts": len(entries),
            "total_duration_seconds": shot_data.get("total_duration_seconds", 0),
            "fps": shot_data.get("fps", 24),
            "prompts": entries,
        }

        export_path = platform_dir / f"{platform}_prompts.json"
        write_json(export_path, export)

        # Write readable prompt pack
        lines = [f"# {platform.title()} Prompt Export", "", "## Shot Prompts", ""]
        for e in entries:
            lines.append(
                f"### Shot {e['shot_index']:03d} — {e['type'].title()} ({e['duration_seconds']}s)"
            )
            lines.append(e["prompt"])
            lines.append("")
        (platform_dir / f"{platform.upper()}_PROMPTS.md").write_text(
            "\n".join(lines), encoding="utf-8"
        )

        result[platform] = entries

    return result
