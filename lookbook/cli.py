from __future__ import annotations
import argparse
import shutil
from pathlib import Path
from .project import init_project
from .pipeline.analyze import analyze_source
from .pipeline.true_animation_packet import create_true_animation_packet
from .pipeline.export_web import export_web
from .pipeline.ocr import extract_text
from .pipeline.panels import detect_panels
from .pipeline.characters import extract_characters
from .pipeline.scene_graph import build_scene_graph
from .pipeline.shot_graph import build_shot_graph
from .pipeline.runway_export import export_runway
from .pipeline.veo_export import export_veo
from .pipeline.kling_export import export_kling
from .pipeline.comfyui_export import export_comfyui
from .pipeline.ffmpeg_export import export_ffmpeg
from .pipeline.remotion_export import export_remotion
from .pipeline.archive import list_pages, process_archive
from .pipeline.vision_enhanced import (
    analyze_source_vision,
    extract_characters_vision,
    build_scene_graph_vision,
    build_shot_graph_vision,
)
from .pipeline.vision_cache import VisionCache
from .pipeline.director_ai import export_director_packet
from .pipeline.docs_export import export_docs
from .lab import install_demo_lab
from .lab_server import run_lab_server
from .telemetry import session_summary
from .video.animatic import build_animatic


def cmd_init(args):
    print(f"Created lookBOOK project: {init_project(args.path, args.name)}")


def cmd_analyze(args):
    project = Path(args.project)
    source = Path(args.source)
    if not project.exists():
        init_project(project, project.name)
    target = project / "source" / source.name
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    payload = analyze_source(target, project)
    print(f"Analysis written: {project / 'analysis' / 'source_analysis.json'}")
    if "image" in payload:
        print(f"Detected image: {payload['image']['width']}x{payload['image']['height']}")


def cmd_true_animation_packet(args):
    print(
        f"Created true-animation packet: {create_true_animation_packet(args.project, args.target)}"
    )


def cmd_export_web(args):
    print(f"Exported review HTML: {export_web(args.project, args.output)}")


def cmd_demo(args):
    project = init_project(args.path, "lookBOOK Vector Bay 7 Demo")
    create_true_animation_packet(project, "runway")
    export_web(project, project / "exports" / "review.html")
    print(f"Created demo project: {project}")


def cmd_install_demo_lab(args):
    print(f"Installed demo lab: {install_demo_lab(args.output)}")


def cmd_lab_server(args):
    run_lab_server(port=args.port)


def cmd_director_ai(args):
    path = export_director_packet(args.project, target=args.target)
    print(f"Director AI packet exported: {path}")


def cmd_telemetry(args):
    stats = session_summary()
    print(f"Session: {stats['session']}")
    print(f"  Events: {stats['events']}")
    print(f"  Vision calls: {stats['vision_calls']}")
    print(f"  Vision cost: ~${stats['vision_cost_usd']} USD")
    print(f"  Cache hits/misses: {stats['cache_hits']}/{stats['cache_misses']}")
    if stats['exports']:
        print("  Exports:")
        for platform, count in stats['exports'].items():
            print(f"    {platform}: {count}")


def cmd_export_docs(args):
    path = export_docs(args.project, output_name=args.output)
    print(f"Exported news & docs page: {path}")


def cmd_extract_text(args):
    blocks = extract_text(
        args.source,
        args.project,
        lang=args.lang,
        psm=args.psm,
        preprocess=not args.no_preprocess,
    )
    print(f"Extracted {len(blocks)} text blocks → project/analysis/ocr_result.json")
    for b in blocks[:5]:
        print(f"  [{b['classification']}] {b['text'][:60]}")
    if len(blocks) > 5:
        print(f"  ... and {len(blocks) - 5} more")


def cmd_detect_panels(args):
    panels = detect_panels(args.source, args.project)
    print(f"Detected {len(panels)} panels → project/analysis/panel_analysis.json")
    for p in panels[:5]:
        print(f"  Panel {p['panel_index']}: {p['bbox']}")
    if len(panels) > 5:
        print(f"  ... and {len(panels) - 5} more")


def cmd_extract_characters(args):
    if args.use_vision:
        chars = extract_characters_vision(args.project, provider=args.vision_provider)
        path = Path(args.project) / "analysis" / "character_analysis_vision.json"
        print(f"Extracted {len(chars)} vision characters → {path}")
        cost = path.read_text(encoding="utf-8") if path.exists() else "{}"
        cost_data = __import__("json").loads(cost)
        print(f"  Vision calls: {cost_data.get('vision_calls', '?')}, cost: ~${cost_data.get('vision_cost_usd', '?')} USD")
    else:
        chars = extract_characters(args.source, args.project, similarity_threshold=args.threshold)
        print(f"Extracted {len(chars)} character clusters → project/analysis/character_analysis.json")
    for c in chars[:5]:
        print(f"  {c.get('character_id', c.get('name', '?'))}: {c['appearances']} appearances")
    if len(chars) > 5:
        print(f"  ... and {len(chars) - 5} more")


def cmd_build_scene_graph(args):
    if args.use_vision:
        scenes = build_scene_graph_vision(args.project, provider=args.vision_provider)
        path = Path(args.project) / "analysis" / "scene_graph_vision.json"
        print(f"Built {len(scenes)} vision scenes → {path}")
    else:
        scenes = build_scene_graph(args.project)
        print(f"Built {len(scenes)} scenes → project/analysis/scene_graph.json")
    for s in scenes:
        print(
            f"  Scene {s['scene_index']}: {s['panel_count']} panels, {len(s.get('characters', []))} characters"
        )


def cmd_build_shot_graph(args):
    if args.use_vision:
        shots = build_shot_graph_vision(args.project, provider=args.vision_provider)
        path = Path(args.project) / "analysis" / "shot_graph_vision.json"
        print(f"Built {len(shots)} vision shots → {path}")
    else:
        shots = build_shot_graph(args.project)
        print(f"Built {len(shots)} shots → project/analysis/shot_graph.json")
    if shots:
        total_dur = sum(s["duration_seconds"] for s in shots)
        print(f"  Total duration: {total_dur:.1f}s @ 24fps = {int(total_dur * 24)} frames")
        for s in shots[:5]:
            print(
                f"  Shot {s['shot_index']}: {s['type']} ({s['duration_seconds']}s) — {s.get('camera', 'N/A')}"
            )


def cmd_vision_cache(args):
    cache = VisionCache(Path(args.project) / "analysis" / "vision_cache")
    if args.clear:
        n = cache.clear()
        print(f"Cleared {n} cached vision entries")
    else:
        stats = cache.stats()
        print(f"Vision cache: {stats['entries']} entries, {stats['total_size_bytes'] / 1024:.1f} KB")


def cmd_analyze_vision(args):
    result = analyze_source_vision(args.source, args.project, provider=args.vision_provider)
    print("Vision analysis complete → project/analysis/source_analysis_vision.json")
    print(result.get("description", "")[:500])
    print(f"\nCost: ~${result.get('cost_usd', '?')} USD")


def cmd_export_runway(args):
    jobs = export_runway(args.project)
    print(f"Exported {len(jobs)} Runway jobs → project/exports/runway/")
    for j in jobs[:3]:
        print(f"  Shot {j['shot_index']}: {j['type']} ({j['duration_seconds']}s)")
    if len(jobs) > 3:
        print(f"  ... and {len(jobs) - 3} more")


def cmd_export_veo(args):
    prompts = export_veo(args.project)
    print(f"Exported {len(prompts)} Veo prompts → project/exports/veo/")
    for p in prompts[:3]:
        print(f"  Shot {p['shot_index']}: {p['type']} ({p['duration_seconds']}s)")
    if len(prompts) > 3:
        print(f"  ... and {len(prompts) - 3} more")


def cmd_export_kling(args):
    result = export_kling(args.project)
    for platform, entries in result.items():
        print(f"Exported {len(entries)} {platform} prompts → project/exports/{platform}/")


def cmd_export_comfyui(args):
    wfs = export_comfyui(args.project, model=args.model, width=args.width, height=args.height)
    print(f"Exported {len(wfs)} ComfyUI workflows → project/exports/comfyui/")
    print(f"  Model: {args.model}")
    for w in wfs[:3]:
        print(f"  Shot {w['shot_index']}: {w['type']} ({w['duration_seconds']}s)")
    if len(wfs) > 3:
        print(f"  ... and {len(wfs) - 3} more")


def cmd_export_ffmpeg(args):
    result = export_ffmpeg(
        args.project,
        input_pattern=args.pattern,
        output_name=args.output,
        fps=args.fps,
    )
    print("Generated FFmpeg assembly → project/exports/ffmpeg/")
    print(f"  Script: {result['assembly_script']}")
    print(f"  Output: {result['output_file']}")
    print(f"  Shots: {result['total_shots']}")


def cmd_export_remotion(args):
    result = export_remotion(args.project, fps=args.fps)
    n = result["total_shots"]
    print(f"Generated Remotion project with {n} shots → project/exports/remotion/")
    print(f"  Duration: {result['total_duration_seconds']:.1f}s @ {result['fps']}fps")
    print(f"  Resolution: {result['resolution']['width']}x{result['resolution']['height']}")
    print("  Setup: cd project/exports/remotion/ && npm install && npm start")


def cmd_list_pages(args):
    pages = list_pages(args.archive)
    print(f"Found {len(pages)} pages in {Path(args.archive).name}:")
    for p in pages:
        size_kb = p["size_bytes"] / 1024
        print(f"  Page {p['page_index']:03d}: {p['filename']} ({size_kb:.0f}KB)")


def cmd_process_archive(args):
    result = process_archive(args.archive, args.project, no_cleanup=args.keep)
    print(f"\nDone. Project: {result['project']}")
    print("  Exports ready in project/exports/*/")


def cmd_generate_animatic(args):
    result = build_animatic(
        args.shot_graph,
        args.output,
        clip_duration=args.duration,
        width=args.width,
        height=args.height,
        fps=args.fps,
        font_path=args.font,
        keep_clips=args.keep_clips,
    )
    print(f"Animatic generated: {result['output_path']}")
    print(f"  Shots: {result['total_shots']}")
    print(f"  Duration: {result['total_duration_seconds']:.1f}s @ {result['fps']}fps")
    print(f"  Resolution: {result['width']}x{result['height']}")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="lookbook",
        description="Open-source book-to-animation compiler.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init")
    p.add_argument("path")
    p.add_argument("--name", default="Untitled lookBOOK Project")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("analyze-source")
    p.add_argument("source")
    p.add_argument("project")
    p.set_defaults(func=cmd_analyze)

    p = sub.add_parser("true-animation-packet")
    p.add_argument("project")
    p.add_argument(
        "--target",
        default="runway",
        choices=["runway", "veo", "gemini", "kling", "pika", "luma"],
    )
    p.set_defaults(func=cmd_true_animation_packet)

    p = sub.add_parser("lab-server")
    p.add_argument("--port", type=int, default=8042)
    p.set_defaults(func=cmd_lab_server)

    p = sub.add_parser("director-ai")
    p.add_argument("project")
    p.add_argument(
        "--target",
        default="runway",
        choices=["runway", "veo", "kling", "pika", "luma"],
    )
    p.set_defaults(func=cmd_director_ai)

    p = sub.add_parser("telemetry")
    p.set_defaults(func=cmd_telemetry)

    p = sub.add_parser("export-web")
    p.add_argument("project")
    p.add_argument("output")
    p.set_defaults(func=cmd_export_web)

    p = sub.add_parser("demo")
    p.add_argument("path")
    p.set_defaults(func=cmd_demo)

    p = sub.add_parser("install-demo-lab")
    p.add_argument("output")
    p.set_defaults(func=cmd_install_demo_lab)

    # Phase C — Source Intelligence commands
    p = sub.add_parser("extract-text")
    p.add_argument("source")
    p.add_argument("project")
    p.add_argument("--lang", default="eng")
    p.add_argument("--psm", type=int, default=6)
    p.add_argument("--no-preprocess", action="store_true")
    p.set_defaults(func=cmd_extract_text)

    p = sub.add_parser("detect-panels")
    p.add_argument("source")
    p.add_argument("project")
    p.set_defaults(func=cmd_detect_panels)

    p = sub.add_parser("extract-characters")
    p.add_argument("source")
    p.add_argument("project")
    p.add_argument("--threshold", type=float, default=0.3)
    p.add_argument("--use-vision", action="store_true", help="Use vision LLM instead of perceptual hashing")
    p.add_argument("--vision-provider", default=None, choices=["openai", "claude", "gemini"])
    p.set_defaults(func=cmd_extract_characters)

    p = sub.add_parser("build-scene-graph")
    p.add_argument("project")
    p.add_argument("--use-vision", action="store_true", help="Use vision LLM for narrative scene grouping")
    p.add_argument("--vision-provider", default=None, choices=["openai", "claude", "gemini"])
    p.set_defaults(func=cmd_build_scene_graph)

    p = sub.add_parser("build-shot-graph")
    p.add_argument("project")
    p.add_argument("--use-vision", action="store_true", help="Use vision LLM for director-level shot analysis")
    p.add_argument("--vision-provider", default=None, choices=["openai", "claude", "gemini"])
    p.set_defaults(func=cmd_build_shot_graph)

    p = sub.add_parser("analyze-vision")
    p.add_argument("source")
    p.add_argument("project")
    p.add_argument("--vision-provider", default=None, choices=["openai", "claude", "gemini"])
    p.set_defaults(func=cmd_analyze_vision)

    p = sub.add_parser("vision-cache")
    p.add_argument("project")
    p.add_argument("--clear", action="store_true", help="Clear all cached vision results")
    p.set_defaults(func=cmd_vision_cache)

    # Phase D — Generation Integration commands
    p = sub.add_parser("export-runway")
    p.add_argument("project")
    p.set_defaults(func=cmd_export_runway)

    p = sub.add_parser("export-veo")
    p.add_argument("project")
    p.set_defaults(func=cmd_export_veo)

    p = sub.add_parser("export-kling")
    p.add_argument("project")
    p.set_defaults(func=cmd_export_kling)

    p = sub.add_parser("export-comfyui")
    p.add_argument("project")
    p.add_argument("--model", default="realisticVisionV51_v51VAE.safetensors")
    p.add_argument("--width", type=int, default=1024)
    p.add_argument("--height", type=int, default=576)
    p.set_defaults(func=cmd_export_comfyui)

    p = sub.add_parser("export-ffmpeg")
    p.add_argument("project")
    p.add_argument("--pattern", default="shot_{index:03d}.mp4")
    p.add_argument("--output", default="lookbook_assembly.mp4")
    p.add_argument("--fps", type=int, default=24)
    p.set_defaults(func=cmd_export_ffmpeg)

    p = sub.add_parser("export-remotion")
    p.add_argument("project")
    p.add_argument("--fps", type=int, default=24)
    p.set_defaults(func=cmd_export_remotion)

    # Batch archive commands
    p = sub.add_parser("list-pages")
    p.add_argument("archive")
    p.set_defaults(func=cmd_list_pages)

    p = sub.add_parser("process-archive")
    p.add_argument("archive")
    p.add_argument("project")
    p.add_argument(
        "--keep",
        action="store_true",
        help="Keep extracted page files after processing",
    )
    p.add_argument("--use-vision", action="store_true", help="Run vision-enhanced pipeline stages")
    p.add_argument("--vision-provider", default=None, choices=["openai", "claude", "gemini"])
    p.set_defaults(func=cmd_process_archive)

    # M5 — Animatic Generator
    p = sub.add_parser("generate-animatic")
    p.add_argument("shot_graph", help="Path to shot_graph.json")
    p.add_argument("--output", "-o", required=True, help="Output MP4 path")
    p.add_argument(
        "--duration",
        type=float,
        default=3.0,
        help="Seconds per shot (default 3.0)",
    )
    p.add_argument("--width", type=int, default=640, help="Width (default 640)")
    p.add_argument("--height", type=int, default=360, help="Height (default 360)")
    p.add_argument("--fps", type=int, default=24, help="FPS (default 24)")
    p.add_argument("--font", default=None, help="Path to a TTF font")
    p.add_argument("--keep-clips", action="store_true", help="Keep intermediate shot MP4s")
    p.set_defaults(func=cmd_generate_animatic)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
