from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib
from ..models import write_json


def _average_hash(img_path: Path, hash_size: int = 8) -> str:
    """Compute an average perceptual hash for an image.

    Pure-Pillow implementation — no numpy required.
    Returns a hex string of length hash_size**2 / 4.
    """
    from PIL import Image

    img = Image.open(img_path).convert("L").resize((hash_size, hash_size), Image.LANCZOS)
    pixels = list(img.get_flattened_data())
    avg = sum(pixels) / len(pixels)
    bits = "".join("1" if p > avg else "0" for p in pixels)
    # Convert binary string to hex
    h = hex(int(bits, 2))[2:]
    return h.zfill(hash_size * hash_size // 4)


def _hamming_distance(h1: str, h2: str) -> float:
    """Normalized Hamming distance between two hex perceptual hashes."""
    b1 = bin(int(h1, 16))[2:].zfill(len(h1) * 4)
    b2 = bin(int(h2, 16))[2:].zfill(len(h2) * 4)
    dist = sum(1 for a, b in zip(b1, b2) if a != b)
    return dist / max(len(b1), 1)


def extract_characters(
    source: str | Path,
    project: str | Path,
    panel_analysis_path: str | Path | None = None,
    similarity_threshold: float = 0.3,
) -> list[dict[str, Any]]:
    """Extract and match character appearances across comic panels.

    Uses perceptual hashing to identify visual similarity between panel
    regions, grouping visually similar panels into character tracks.

    Args:
        source: Original page image path
        project: lookBOOK project path
        panel_analysis_path: Path to panel_analysis.json (auto-detected if None)
        similarity_threshold: Max normalized distance for a match (0-1, lower = stricter)

    Returns:
        List of character entries with appearances tracked across panels.
    """
    import json

    source = Path(source)
    project = Path(project)

    # Load panel analysis
    if panel_analysis_path is None:
        panel_file = project / "analysis" / "panel_analysis.json"
    else:
        panel_file = Path(panel_analysis_path)

    if not panel_file.exists():
        raise FileNotFoundError(
            f"Panel analysis not found at {panel_file}. Run 'lookbook detect-panels' first."
        )

    panel_data = json.loads(panel_file.read_text(encoding="utf-8"))
    panels = panel_data.get("panels", [])

    if not panels:
        raise ValueError("No panels found in panel analysis.")

    # Compute perceptual hash for each panel image
    from PIL import Image

    panel_hashes: list[dict[str, Any]] = []
    for p in panels:
        panel_path_str = p.get("image_path")
        if panel_path_str:
            panel_img_path = project / panel_path_str
        else:
            # Fallback: attempt to find panel image in analysis/panels/
            panel_img_path = project / "analysis" / "panels" / f"panel_{p['panel_index']:03d}.png"
            if not panel_img_path.exists():
                panel_img_path = (
                    project / "analysis" / "panels" / f"panel_{p['panel_index']:03d}.jpg"
                )

        if panel_img_path.exists():
            phash = _average_hash(panel_img_path)
            panel_hashes.append(
                {
                    "panel_index": p["panel_index"],
                    "bbox": p["bbox"],
                    "phash": phash,
                    "image_path": str(panel_img_path),
                    "area": p.get("area", 0),
                }
            )

    if not panel_hashes:
        raise ValueError("No panel images found to analyze.")

    # Cluster panels by perceptual hash similarity (greedy)
    characters: list[dict[str, Any]] = []
    assigned: set[int] = set()

    for ph in panel_hashes:
        if ph["panel_index"] in assigned:
            continue
        # Start a new character cluster
        cluster = [ph]
        assigned.add(ph["panel_index"])

        for other in panel_hashes:
            if other["panel_index"] in assigned:
                continue
            dist = _hamming_distance(ph["phash"], other["phash"])
            if dist <= similarity_threshold:
                cluster.append(other)
                assigned.add(other["panel_index"])

        characters.append(
            {
                "character_id": f"char_{len(characters):03d}",
                "appearances": len(cluster),
                "primary_panel": cluster[0]["panel_index"],
                "panels": [
                    {
                        "panel_index": c["panel_index"],
                        "bbox": c["bbox"],
                        "image_path": c["image_path"],
                    }
                    for c in sorted(cluster, key=lambda x: x["panel_index"])
                ],
                "cluster_hash": ph["phash"],
            }
        )

    # Sort characters by most appearances first
    characters.sort(key=lambda c: c["appearances"], reverse=True)

    result = {
        "schema": "lookbook.characters.v0.2",
        "source_file": source.name,
        "total_characters": len(characters),
        "similarity_threshold": similarity_threshold,
        "characters": characters,
    }

    analysis_dir = project / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    write_json(analysis_dir / "character_analysis.json", result)

    return characters
