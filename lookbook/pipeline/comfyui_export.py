from __future__ import annotations
from pathlib import Path
from typing import Any
import json
from ..models import write_json


DEFAULT_COMFY_WORKFLOW = {
    "1": {
        "class_type": "KSampler",
        "inputs": {
            "seed": 42,
            "steps": 20,
            "cfg": 7.0,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 1.0,
            "model": ["2", 0],
            "positive": ["3", 0],
            "negative": ["4", 0],
            "latent_image": ["5", 0],
        },
    },
    "2": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "realisticVisionV51_v51VAE.safetensors"}},
    "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["2", 1]}},
    "4": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["2", 1]}},
    "5": {
        "class_type": "EmptyLatentImage",
        "inputs": {"width": 1024, "height": 576, "batch_size": 1},
    },
    "6": {"class_type": "VAEDecode", "inputs": {"samples": ["1", 0], "vae": ["2", 2]}},
    "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": "lookbook_shot", "images": ["6", 0]}},
    "8": {
        "class_type": "LoadImage",
        "inputs": {"image": "", "upload": "image"},
    },
    "9": {
        "class_type": "ImageScaleToTotalPixels",
        "inputs": {"upscale_method": "lanczos", "megapixels": 0.589824, "image": ["8", 0]},
    },
    "10": {
        "class_type": "VAEEncode",
        "inputs": {"pixels": ["9", 0], "vae": ["2", 2]},
    },
}


def export_comfyui(
    project: str | Path,
    shot_graph_path: str | Path | None = None,
    model: str = "realisticVisionV51_v51VAE.safetensors",
    width: int = 1024,
    height: int = 576,
) -> list[dict[str, Any]]:
    """Export shot graph as a ComfyUI workflow API JSON.

    Generates a ComfyUI workflow JSON for each shot, chaining
    image input → VAE encode → KSampler → VAE decode → save.
    Workflows can be imported directly into ComfyUI or
    submitted via the ComfyUI API.

    Args:
        project: lookBOOK project path
        shot_graph_path: Path to shot_graph.json (auto-detected)
        model: ComfyUI checkpoint model name
        width: Output video/image width
        height: Output video/image height

    Returns:
        List of per-shot ComfyUI workflow dicts.
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

    shot_dir = project / "exports" / "comfyui"
    shot_dir.mkdir(parents=True, exist_ok=True)

    camera_to_comfy = {
        "zoom in": "cinematic zoom in effect, dolly zoom style",
        "zoom out": "pull back reveal shot",
        "pan right": "lateral camera movement, pan right",
        "pan left": "lateral camera movement, pan left",
        "static": "static camera, subtle motion, cinematic",
        "push in": "dramatic push in, intensifying shot",
        "pull out": "revealing pull out shot",
    }

    workflows: list[dict[str, Any]] = []

    for i, shot in enumerate(shots):
        dialogue = " ".join(shot.get("dialogue", []))
        narration = " ".join(shot.get("narration", []))
        characters = ", ".join(shot.get("characters", [])) if shot.get("characters") else "figures"
        motion = shot.get("motion_directive", "")
        camera_hint = camera_to_comfy.get(shot.get("camera", ""), "cinematic shot")

        # Build positive prompt
        pos_parts = [f"{characters}"]
        if dialogue:
            pos_parts.append(f"dialogue scene: {dialogue[:150]}")
        if narration:
            pos_parts.append(f"mood: {narration[:120]}")
        if motion:
            pos_parts.append(motion)
        pos_parts.append(camera_hint)
        pos_parts.append("high quality, detailed, sharp focus, cinematic lighting")

        positive_prompt = ", ".join(pos_parts)
        negative_prompt = (
            "static image, slideshow, pan and zoom only, text, watermark, "
            "blurry, low quality, distorted faces, extra limbs, bad anatomy"
        )

        # Build workflow for this shot
        import copy

        wf = copy.deepcopy(DEFAULT_COMFY_WORKFLOW)
        wf["3"]["inputs"]["text"] = positive_prompt
        wf["4"]["inputs"]["text"] = negative_prompt
        wf["5"]["inputs"] = {"width": width, "height": height, "batch_size": 1}
        wf["7"]["inputs"]["filename_prefix"] = f"lookbook_shot_{shot['shot_index']:03d}"
        wf["8"]["inputs"]["image"] = ""

        workflow_entry = {
            "shot_index": shot["shot_index"],
            "type": shot.get("type", "establishing"),
            "duration_seconds": shot["duration_seconds"],
            "workflow": wf,
            "positive_prompt": positive_prompt,
            "negative_prompt": negative_prompt,
            "model": model,
            "panel_refs": shot.get("panels", []),
        }

        workflows.append(workflow_entry)

        # Write individual workflow JSON files
        wf_path = shot_dir / f"workflow_shot_{shot['shot_index']:03d}.json"
        wf_path.write_text(json.dumps(wf, indent=2), encoding="utf-8")

    # Write combined export
    export = {
        "schema": "lookbook.comfyui_export.v0.2",
        "total_workflows": len(workflows),
        "default_model": model,
        "default_resolution": {"width": width, "height": height},
        "instructions": (
            "Each workflow JSON can be loaded into ComfyUI via drag-and-drop. "
            "Connect an image input to node 8 (LoadImage) for each shot's keyframe. "
            "Alternatively, use the ComfyUI API to submit workflows programmatically."
        ),
        "workflows": [
            {
                "shot_index": w["shot_index"],
                "type": w["type"],
                "duration_seconds": w["duration_seconds"],
                "model": w["model"],
                "workflow_file": f"workflow_shot_{w['shot_index']:03d}.json",
                "panel_refs": w["panel_refs"],
            }
            for w in workflows
        ],
    }

    write_json(shot_dir / "comfyui_workflow_pack.json", export)

    return workflows
