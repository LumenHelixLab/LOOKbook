from __future__ import annotations
import argparse, shutil
from pathlib import Path
from .project import init_project
from .pipeline.analyze import analyze_source
from .pipeline.true_animation_packet import create_true_animation_packet
from .pipeline.export_web import export_web
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

def build_parser():
    parser=argparse.ArgumentParser(prog='lookbook', description='Open-source book-to-animation compiler.'); sub=parser.add_subparsers(dest='command', required=True)
    p=sub.add_parser('init'); p.add_argument('path'); p.add_argument('--name', default='Untitled lookBOOK Project'); p.set_defaults(func=cmd_init)
    p=sub.add_parser('analyze-source'); p.add_argument('source'); p.add_argument('project'); p.set_defaults(func=cmd_analyze)
    p=sub.add_parser('true-animation-packet'); p.add_argument('project'); p.add_argument('--target', default='runway', choices=['runway','veo','gemini','kling','pika','luma']); p.set_defaults(func=cmd_true_animation_packet)
    p=sub.add_parser('export-web'); p.add_argument('project'); p.add_argument('output'); p.set_defaults(func=cmd_export_web)
    p=sub.add_parser('demo'); p.add_argument('path'); p.set_defaults(func=cmd_demo)
    p=sub.add_parser('install-demo-lab'); p.add_argument('output'); p.set_defaults(func=cmd_install_demo_lab)
    return parser

def main(argv=None): args=build_parser().parse_args(argv); args.func(args)
if __name__ == '__main__': main()
