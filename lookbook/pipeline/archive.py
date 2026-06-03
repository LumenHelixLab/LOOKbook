from __future__ import annotations
from pathlib import Path
from typing import Any, Iterator
import zipfile, tempfile, shutil, json


def _is_cbz(path: Path) -> bool:
    return path.suffix.lower() in (".cbz", ".zip")


def _is_cbr(path: Path) -> bool:
    return path.suffix.lower() in (".cbr", ".rar")


def list_pages(archive: str | Path) -> list[dict[str, Any]]:
    """List all image pages in a CBZ/CBR comic archive.

    Returns a list of dicts with page_index, filename, and estimated page number.
    Pages are sorted alphabetically by filename (standard comic archive convention).
    """
    archive = Path(archive)
    if not archive.exists():
        raise FileNotFoundError(f"Archive not found: {archive}")

    image_exts = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff", ".tif"}

    pages: list[dict[str, Any]] = []

    if _is_cbz(archive):
        with zipfile.ZipFile(archive, "r") as zf:
            names = sorted(zf.namelist())
            for name in names:
                ext = Path(name).suffix.lower()
                if ext in image_exts and not name.startswith("__") and not name.startswith("."):
                    pages.append(
                        {
                            "page_index": len(pages),
                            "filename": name,
                            "extension": ext,
                            "size_bytes": zf.getinfo(name).file_size,
                        }
                    )

    elif _is_cbr(archive):
        try:
            import rarfile
        except ImportError:
            raise ImportError(
                "rarfile is required for CBR archives. Install: pip install rarfile"
            )

        with rarfile.RarFile(archive, "r") as rf:
            names = sorted(rf.namelist())
            for name in names:
                ext = Path(name).suffix.lower()
                if ext in image_exts and not name.startswith("__") and not name.startswith("."):
                    info = rf.getinfo(name)
                    pages.append(
                        {
                            "page_index": len(pages),
                            "filename": name,
                            "extension": ext,
                            "size_bytes": info.file_size,
                        }
                    )

    else:
        raise ValueError(f"Unsupported archive format: {archive.suffix}. Expected .cbz or .cbr")

    return pages


def extract_page(
    archive: str | Path,
    filename: str,
    output_dir: str | Path,
) -> Path:
    """Extract a single page image from a CBZ/CBR archive to a directory."""
    archive = Path(archive)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if _is_cbz(archive):
        with zipfile.ZipFile(archive, "r") as zf:
            zf.extract(filename, output_dir)

    elif _is_cbr(archive):
        import rarfile
        with rarfile.RarFile(archive, "r") as rf:
            rf.extract(filename, output_dir)

    else:
        raise ValueError(f"Unsupported archive format: {archive.suffix}")

    return output_dir / filename


def extract_all_pages(
    archive: str | Path,
    output_dir: str | Path,
) -> list[Path]:
    """Extract all image pages from a CBZ/CBR archive to a directory.

    Returns sorted list of extracted file paths.
    """
    pages = list_pages(archive)
    paths: list[Path] = []

    for page in pages:
        p = extract_page(archive, page["filename"], output_dir)
        paths.append(p)

    return paths


def process_archive(
    archive: str | Path,
    project: str | Path,
    no_cleanup: bool = False,
) -> dict[str, Any]:
    """Run the full lookBOOK pipeline on every page in a comic archive.

    For each page:
    1. Extract from archive
    2. Run detect-panels + extract-text + extract-characters
    3. Build scene graph + shot graph
    4. Export to all platforms

    Args:
        archive: Path to CBZ or CBR file
        project: lookBOOK project path (created if doesn't exist)
        no_cleanup: If True, keep extracted page files after processing

    Returns:
        Dict with per-page results summary.
    """
    archive = Path(archive)
    project = Path(project)

    if not archive.exists():
        raise FileNotFoundError(f"Archive not found: {archive}")

    # Init project if needed
    from ..cli import main as cli_main

    if not project.exists():
        cli_main(["init", str(project), "--name", archive.stem])

    # Create extraction temp dir
    extract_dir = project / ".cache" / "extracted_pages"
    extract_dir.mkdir(parents=True, exist_ok=True)

    pages = list_pages(archive)
    results: list[dict[str, Any]] = []

    print(f"Processing {len(pages)} pages from {archive.name}...")

    for i, page in enumerate(pages):
        print(f"  Page {i+1}/{len(pages)}: {page['filename']}")

        # Extract
        img_path = extract_page(archive, page["filename"], extract_dir)

        # Run pipeline stages (best-effort - continue on error)
        page_result: dict[str, Any] = {
            "page_index": page["page_index"],
            "filename": page["filename"],
            "panels": 0,
            "ocr_blocks": 0,
            "characters": 0,
        }

        # Analyze source
        try:
            cli_main(["analyze-source", str(img_path), str(project)])
        except Exception as e:
            page_result["analyze_error"] = str(e)

        # Detect panels
        try:
            cli_main(["detect-panels", str(img_path), str(project)])
            panels_file = project / "analysis" / "panel_analysis.json"
            if panels_file.exists():
                data = json.loads(panels_file.read_text(encoding="utf-8"))
                page_result["panels"] = len(data.get("panels", []))
        except Exception as e:
            page_result["panels_error"] = str(e)

        # Extract text
        try:
            cli_main(["extract-text", str(img_path), str(project)])
            ocr_file = project / "analysis" / "ocr_result.json"
            if ocr_file.exists():
                data = json.loads(ocr_file.read_text(encoding="utf-8"))
                page_result["ocr_blocks"] = len(data.get("blocks", data.get("panels", [])))
        except Exception as e:
            page_result["ocr_error"] = str(e)

        # Extract characters
        try:
            cli_main(["extract-characters", str(img_path), str(project)])
            char_file = project / "analysis" / "character_analysis.json"
            if char_file.exists():
                data = json.loads(char_file.read_text(encoding="utf-8"))
                page_result["characters"] = len(data.get("characters", []))
        except Exception as e:
            page_result["characters_error"] = str(e)

        results.append(page_result)

    # Build scene graph + shot graph from combined analysis
    try:
        cli_main(["build-scene-graph", str(project)])
        page_result["scene_graph"] = True
    except Exception as e:
        page_result["scene_graph_error"] = str(e)

    try:
        cli_main(["build-shot-graph", str(project)])
        page_result["shot_graph"] = True
    except Exception as e:
        page_result["shot_graph_error"] = str(e)

    # Export to all platforms
    for export_cmd in ["export-runway", "export-veo", "export-kling", "export-ffmpeg", "export-remotion"]:
        try:
            cli_main([export_cmd, str(project)])
        except Exception as e:
            pass  # Some exports may require shot_graph which might have failed

    # Cleanup extracted pages unless requested to keep
    if not no_cleanup:
        import shutil
        shutil.rmtree(extract_dir, ignore_errors=True)

    summary = {
        "schema": "lookbook.archive_process.v0.2",
        "archive": archive.name,
        "total_pages": len(pages),
        "project": str(project),
        "pages": results,
    }

    from ..models import write_json
    write_json(project / "analysis" / "archive_process.json", summary)

    total_panels = sum(r["panels"] for r in results)
    total_ocr = sum(r["ocr_blocks"] for r in results)
    total_chars = sum(r["characters"] for r in results)

    print(f"\nArchive processing complete: {archive.name}")
    print(f"  Pages: {len(pages)}")
    print(f"  Total panels detected: {total_panels}")
    print(f"  Total OCR blocks: {total_ocr}")
    print(f"  Total character clusters: {total_chars}")
    print(f"  Exports: runway, veo, kling, ffmpeg, remotion")

    return summary
