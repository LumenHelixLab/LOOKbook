"""lookBOOK — Vision-Enhanced Pipeline Orchestrator
Runs vision LLM analysis over panels and produces enhanced JSON artifacts
that mirror classical outputs but with semantic understanding.
"""

import json
from pathlib import Path
from typing import Any

from ..config import get_config, get_api_key
from .vision_llm import get_analyzer
from .vision_cache import VisionCache
from ..models import write_json


def _get_cache(project: Path) -> VisionCache:
    return VisionCache(project / "analysis" / "vision_cache")


def analyze_source_vision(source: str | Path, project: str | Path, provider: str | None = None) -> dict[str, Any]:
    """Generate a rich vision-based description of the source page."""
    source = Path(source)
    project = Path(project)
    cache = _get_cache(project)

    cfg = get_config()
    p = provider or cfg["vision"]["provider"]
    analyzer = get_analyzer(p)

    prompt = (
        "Describe this comic/manga page in detail. Include: overall layout, panel arrangement, "
        "setting/atmosphere, key visual elements, and any text or sound effects visible."
    )

    cached = cache.get(source, prompt)
    if cached:
        return cached

    result = analyzer.describe_panel(str(source))
    cache.set(source, prompt, result)
    return result


def extract_characters_vision(
    project: str | Path,
    panel_analysis_path: str | Path | None = None,
    provider: str | None = None,
) -> list[dict[str, Any]]:
    """Extract characters using vision LLM instead of perceptual hashing."""
    project = Path(project)
    cache = _get_cache(project)

    if panel_analysis_path is None:
        panel_file = project / "analysis" / "panel_analysis.json"
    else:
        panel_file = Path(panel_analysis_path)

    if not panel_file.exists():
        raise FileNotFoundError(f"Panel analysis not found at {panel_file}")

    panel_data = json.loads(panel_file.read_text(encoding="utf-8"))
    panels = panel_data.get("panels", [])

    cfg = get_config()
    p = provider or cfg["vision"]["provider"]
    analyzer = get_analyzer(p)

    characters_map: dict[str, dict[str, Any]] = {}

    for panel in panels:
        panel_idx = panel["panel_index"]
        img_path = project / panel.get("image_path", f"analysis/panels/panel_{panel_idx:03d}.png")
        if not img_path.exists():
            continue

        prompt = (
            "List all visible characters in this panel. For each character: name (if known), "
            "description of appearance, clothing, expression, and approximate position in the frame."
        )

        cached = cache.get(img_path, prompt)
        if cached:
            result = cached
        else:
            result = analyzer.extract_characters(str(img_path))
            cache.set(img_path, prompt, result)

        raw = result.get("characters", "")
        # Parse simple list format from LLM
        char_entries = [line.strip("- •").strip() for line in str(raw).split("\n") if line.strip()]

        for entry in char_entries:
            # Use first few words as a naive character key
            key = entry.lower()[:40]
            if key not in characters_map:
                characters_map[key] = {
                    "character_id": f"char_vis_{len(characters_map):03d}",
                    "name": entry.split("(")[0].strip() or f"Character {len(characters_map)+1}",
                    "description": entry,
                    "appearances": 0,
                    "panels": [],
                }
            characters_map[key]["appearances"] += 1
            characters_map[key]["panels"].append({
                "panel_index": panel_idx,
                "bbox": panel.get("bbox", {}),
                "image_path": str(img_path),
            })

    characters = sorted(characters_map.values(), key=lambda c: c["appearances"], reverse=True)

    result = {
        "schema": "lookbook.characters.v0.2.vision",
        "method": "vision_llm",
        "provider": p,
        "total_characters": len(characters),
        "characters": characters,
        "vision_cost_usd": round(analyzer.cost_usd, 4),
        "vision_calls": analyzer.calls,
    }

    analysis_dir = project / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    write_json(analysis_dir / "character_analysis_vision.json", result)
    return characters


def build_scene_graph_vision(
    project: str | Path,
    provider: str | None = None,
) -> list[dict[str, Any]]:
    """Build a scene graph using vision LLM narrative understanding."""
    project = Path(project)
    cache = _get_cache(project)

    panel_file = project / "analysis" / "panel_analysis.json"
    if not panel_file.exists():
        raise FileNotFoundError("Panel analysis required")

    panel_data = json.loads(panel_file.read_text(encoding="utf-8"))
    panels = panel_data.get("panels", [])

    cfg = get_config()
    p = provider or cfg["vision"]["provider"]
    analyzer = get_analyzer(p)

    # Analyze first panel of each logical group for scene transitions
    scenes = []
    current_scene_panels = []

    for i, panel in enumerate(panels):
        panel_idx = panel["panel_index"]
        img_path = project / panel.get("image_path", f"analysis/panels/panel_{panel_idx:03d}.png")
        if not img_path.exists():
            continue

        # Only run vision on every Nth panel or panel transitions to save cost
        if i == 0 or i % 3 == 0:
            prompt = (
                "Describe the scene setting, characters present, and narrative context. "
                "Is this a continuation of the previous scene or a new scene? Reply with 'NEW' or 'CONTINUE'."
            )
            cached = cache.get(img_path, prompt)
            if cached:
                result = cached
            else:
                result = analyzer.describe_panel(str(img_path))
                cache.set(img_path, prompt, result)

            desc = result.get("description", "").lower()
            is_new = "new" in desc and "continue" not in desc

            if is_new and current_scene_panels:
                scenes.append(_build_vision_scene(len(scenes), current_scene_panels, panels))
                current_scene_panels = []

        current_scene_panels.append(panel)

    if current_scene_panels:
        scenes.append(_build_vision_scene(len(scenes), current_scene_panels, panels))

    result = {
        "schema": "lookbook.scene_graph.v0.2.vision",
        "method": "vision_llm",
        "provider": p,
        "total_scenes": len(scenes),
        "scenes": scenes,
        "vision_cost_usd": round(analyzer.cost_usd, 4),
        "vision_calls": analyzer.calls,
    }

    analysis_dir = project / "analysis"
    write_json(analysis_dir / "scene_graph_vision.json", result)
    return scenes


def _build_vision_scene(scene_index: int, scene_panels: list, all_panels: list) -> dict[str, Any]:
    panel_indices = [p["panel_index"] for p in scene_panels]
    return {
        "scene_index": scene_index,
        "panel_count": len(scene_panels),
        "panel_indices": panel_indices,
        "panels": [
            {
                "panel_index": p["panel_index"],
                "bbox": p.get("bbox", {}),
                "area": p.get("area", 0),
                "aspect_ratio": p.get("aspect_ratio", 0),
            }
            for p in scene_panels
        ],
        "characters": [],
        "dialogue": [],
        "narration": [],
    }


def build_shot_graph_vision(
    project: str | Path,
    provider: str | None = None,
) -> list[dict[str, Any]]:
    """Generate shot lists using vision LLM shot composition analysis."""
    project = Path(project)
    cache = _get_cache(project)

    scene_file = project / "analysis" / "scene_graph_vision.json"
    if not scene_file.exists():
        # Fallback to classical scene graph
        scene_file = project / "analysis" / "scene_graph.json"
    if not scene_file.exists():
        raise FileNotFoundError("Scene graph required")

    scene_data = json.loads(scene_file.read_text(encoding="utf-8"))
    scenes = scene_data.get("scenes", [])

    cfg = get_config()
    p = provider or cfg["vision"]["provider"]
    analyzer = get_analyzer(p)

    shots = []
    total_time = 0.0

    for scene in scenes:
        panel_indices = scene.get("panel_indices", [])
        if not panel_indices:
            continue

        # Use first panel of scene for shot generation
        first_panel_idx = panel_indices[0]
        panel_file = project / "analysis" / "panel_analysis.json"
        panel_img = project / f"analysis/panels/panel_{first_panel_idx:03d}.png"
        if not panel_img.exists():
            panel_img = project / f"analysis/panels/panel_{first_panel_idx:03d}.jpg"

        if panel_img.exists():
            prompt = (
                "Analyze this panel as an animation director. Suggest: shot type (close-up, wide, medium), "
                "camera movement, duration in seconds, and a motion directive for animators."
            )
            cached = cache.get(panel_img, prompt)
            if cached:
                result = cached
            else:
                result = analyzer.generate_shot_list(str(panel_img))
                cache.set(panel_img, prompt, result)

            shot_text = result.get("shot_list", "")
            # Parse rough duration from text
            duration = 3.0
            if "second" in shot_text.lower():
                for word in shot_text.lower().split():
                    if word.replace(".", "").replace(",", "").isdigit():
                        num = float(word.replace(",", ""))
                        if 0.5 <= num <= 30:
                            duration = num
                            break
        else:
            shot_text = "Standard scene shot."
            duration = 3.0

        shot = {
            "shot_index": len(shots),
            "scene_index": scene["scene_index"],
            "type": "vision_directed",
            "duration_seconds": round(duration, 1),
            "start_time": round(total_time, 1),
            "end_time": round(total_time + duration, 1),
            "panels": panel_indices,
            "panel_count": len(panel_indices),
            "camera": "director's choice",
            "transition_in": "cut",
            "dialogue": scene.get("dialogue", []),
            "narration": scene.get("narration", []),
            "characters": scene.get("characters", []),
            "motion_directive": shot_text,
        }
        shots.append(shot)
        total_time += duration

        # Transition shot between scenes
        if scene["scene_index"] < len(scenes) - 1:
            trans = {
                "shot_index": len(shots),
                "scene_index": scene["scene_index"],
                "type": "transition",
                "duration_seconds": 1.0,
                "start_time": round(total_time, 1),
                "end_time": round(total_time + 1.0, 1),
                "panels": [],
                "panel_count": 0,
                "camera": "static",
                "transition_in": "dissolve",
                "dialogue": [],
                "narration": [],
                "characters": [],
                "motion_directive": "Transition between scenes.",
            }
            shots.append(trans)
            total_time += 1.0

    result = {
        "schema": "lookbook.shot_graph.v0.2.vision",
        "method": "vision_llm",
        "provider": p,
        "total_shots": len(shots),
        "total_duration_seconds": round(total_time, 1),
        "fps": 24,
        "frames": int(total_time * 24),
        "shots": shots,
        "vision_cost_usd": round(analyzer.cost_usd, 4),
        "vision_calls": analyzer.calls,
    }

    analysis_dir = project / "analysis"
    write_json(analysis_dir / "shot_graph_vision.json", result)
    return shots
