from __future__ import annotations
import argparse, shutil
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
from .lab import install_demo_lab

def cmd_init(args): print(f"Created lookBOOK project: {init_project(args.path, args.name)}")
def cmd_analyze(args):
    project=Path(args.project); source=Path(args.source)
    if not project.exists(): init_project(project, project.name)
    target=project/'source'/source.name; target.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve()!=target.resolve(): shutil.copy2(source,target)
    payload=analyze_source(target, project); print(f"Analysis written: {project/'analysis'/'source_analysis.json'}")
    if 'image' in payload: print(f"Detected image: {payload['image']['width']}x{payload['image']['height']}")
def cmd_true_animation_packet(args): print(f"Created true-animation packet: {create_true_animation_packet(args.project,args.target)}")
def cmd_export_web(args): print(f"Exported review HTML: {export_web(args.project,args.output)}")
def cmd_demo(args):
    project=init_project(args.path, 'lookBOOK Vector Bay 7 Demo'); create_true_animation_packet(project,'runway'); export_web(project, project/'exports'/'review.html'); print(f"Created demo project: {project}")
def cmd_install_demo_lab(args): print(f"Installed demo lab: {install_demo_lab(args.output)}")
def cmd_extract_text(args):
    blocks=extract_text(args.source, args.project, lang=args.lang, psm=args.psm, preprocess=not args.no_preprocess)
    print(f"Extracted {len(blocks)} text blocks → project/analysis/ocr_result.json")
    for b in blocks[:5]: print(f"  [{b['classification']}] {b['text'][:60]}")
    if len(blocks)>5: print(f"  ... and {len(blocks)-5} more")
def cmd_detect_panels(args):
    panels=detect_panels(args.source, args.project)
    print(f"Detected {len(panels)} panels → project/analysis/panel_analysis.json")
    for p in panels[:5]: print(f"  Panel {p['panel_index']}: {p['bbox']}")
    if len(panels)>5: print(f"  ... and {len(panels)-5} more")
def cmd_extract_characters(args):
    chars=extract_characters(args.source, args.project, similarity_threshold=args.threshold)
    print(f"Extracted {len(chars)} character clusters → project/analysis/character_analysis.json")
    for c in chars[:5]: print(f"  {c['character_id']}: {c['appearances']} appearances")
    if len(chars)>5: print(f"  ... and {len(chars)-5} more")
def cmd_build_scene_graph(args):
    scenes=build_scene_graph(args.project)
    print(f"Built {len(scenes)} scenes → project/analysis/scene_graph.json")
    for s in scenes: print(f"  Scene {s['scene_index']}: {s['panel_count']} panels, {len(s['characters'])} characters")
def cmd_build_shot_graph(args):
    shots=build_shot_graph(args.project)
    if shots:
        total_dur = sum(s['duration_seconds'] for s in shots)
        print(f"Built {len(shots)} shots ({total_dur:.1f}s) → project/analysis/shot_graph.json")
        print(f"  Total duration: {total_dur:.1f}s @ {24}fps = {int(total_dur*24)} frames")
        for s in shots[:5]: print(f"  Shot {s['shot_index']}: {s['type']} ({s['duration_seconds']}s) — {s['camera']}")

def build_parser():
    parser=argparse.ArgumentParser(prog='lookbook', description='Open-source book-to-animation compiler.'); sub=parser.add_subparsers(dest='command', required=True)
    p=sub.add_parser('init'); p.add_argument('path'); p.add_argument('--name', default='Untitled lookBOOK Project'); p.set_defaults(func=cmd_init)
    p=sub.add_parser('analyze-source'); p.add_argument('source'); p.add_argument('project'); p.set_defaults(func=cmd_analyze)
    p=sub.add_parser('true-animation-packet'); p.add_argument('project'); p.add_argument('--target', default='runway', choices=['runway','veo','gemini','kling','pika','luma']); p.set_defaults(func=cmd_true_animation_packet)
    p=sub.add_parser('export-web'); p.add_argument('project'); p.add_argument('output'); p.set_defaults(func=cmd_export_web)
    p=sub.add_parser('demo'); p.add_argument('path'); p.set_defaults(func=cmd_demo)
    p=sub.add_parser('install-demo-lab'); p.add_argument('output'); p.set_defaults(func=cmd_install_demo_lab)
    # Phase C — Source Intelligence commands
    p=sub.add_parser('extract-text'); p.add_argument('source'); p.add_argument('project'); p.add_argument('--lang', default='eng'); p.add_argument('--psm', type=int, default=6); p.add_argument('--no-preprocess', action='store_true'); p.set_defaults(func=cmd_extract_text)
    p=sub.add_parser('detect-panels'); p.add_argument('source'); p.add_argument('project'); p.set_defaults(func=cmd_detect_panels)
    p=sub.add_parser('extract-characters'); p.add_argument('source'); p.add_argument('project'); p.add_argument('--threshold', type=float, default=0.3); p.set_defaults(func=cmd_extract_characters)
    p=sub.add_parser('build-scene-graph'); p.add_argument('project'); p.set_defaults(func=cmd_build_scene_graph)
    p=sub.add_parser('build-shot-graph'); p.add_argument('project'); p.set_defaults(func=cmd_build_shot_graph)
    return parser

def main(argv=None): args=build_parser().parse_args(argv); args.func(args)
if __name__ == '__main__': main()
