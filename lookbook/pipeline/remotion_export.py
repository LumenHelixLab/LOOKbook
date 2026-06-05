from __future__ import annotations
from pathlib import Path
from typing import Any
import json
import textwrap
from ..models import write_json


def export_remotion(
    project: str | Path,
    shot_graph_path: str | Path | None = None,
    fps: int = 24,
) -> dict[str, Any]:
    """Export shot graph as a Remotion TypeScript project structure.

    Generates a complete Remotion comp directory including:
    - Root.tsx with Composition registrations
    - Per-shot scene components with timing, transitions, and dialogue
    - Package.json for the Remotion project
    - Dynamic metadata for each composition

    Args:
        project: lookBOOK project path
        shot_graph_path: Path to shot_graph.json (auto-detected)
        fps: Frames per second for Remotion compositions

    Returns:
        Dict with files created, metadata, and instructions.
    """
    project = Path(project)

    if shot_graph_path is None:
        shot_graph_path = project / "analysis" / "shot_graph.json"
    if not shot_graph_path.exists():
        raise FileNotFoundError(f"Shot graph not found at {shot_graph_path}.")

    shot_data = json.loads(shot_graph_path.read_text(encoding="utf-8"))
    shots = shot_data.get("shots", [])
    total_dur = shot_data.get("total_duration_seconds", 0)

    if not shots:
        raise ValueError("No shots found in shot graph.")

    export_dir = project / "exports" / "remotion"
    src_dir = export_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    # Generate per-shot scene components
    shot_components: list[str] = []
    for i, shot in enumerate(shots):
        idx = shot["shot_index"]
        dur_frames = int(shot["duration_seconds"] * fps)
        dialogue = " ".join(shot.get("dialogue", []))
        narration = " ".join(shot.get("narration", []))
        camera = shot.get("camera", "static")
        shot_type = shot.get("type", "establishing")
        motion = shot.get("motion_directive", "")

        shot_ts = textwrap.dedent(f"""\
        import {{ useCurrentFrame, interpolate, spring, useVideoConfig, AbsoluteFill }} from "remotion";

        interface Shot{idx:03d}Props {{
          readonly panelRefs: readonly number[];
          readonly dialogue?: string;
          readonly narration?: string;
        }}

        export const Shot{idx:03d}: React.FC<Shot{idx:03d}Props> = ({{
          panelRefs,
          dialogue = "",
          narration = "",
        }}) => {{
          const frame = useCurrentFrame();
          const {{fps}} = useVideoConfig();

          // Camera motion: {camera}
          // Shot type: {shot_type}
          // Motion directive: {motion}

          const opacity = interpolate(frame, [0, 10], [0, 1], {{
            extrapolateRight: "clamp",
            extrapolateLeft: "clamp",
          }});

          const scale = spring({{
            frame,
            fps,
            config: {{ damping: 200 }},
          }});

          return (
            <AbsoluteFill
              style={{
                opacity,
                transform: `scale(${{scale}})`,
                backgroundColor: "#1a1a2e",
                justifyContent: "center",
                alignItems: "center",
                color: "white",
                fontFamily: "sans-serif",
              }}
            >
              {"{"}dialogue && (
                <div style={{
                  position: "absolute",
                  bottom: "15%",
                  left: "10%",
                  right: "10%",
                  textAlign: "center",
                  fontSize: 24,
                  background: "rgba(0,0,0,0.6)",
                  padding: "12px 24px",
                  borderRadius: 8,
                }}>
                  {dialogue}
                </div>
              ){"}"}
              {"{"}narration && (
                <div style={{
                  position: "absolute",
                  top: "10%",
                  left: "10%",
                  fontStyle: "italic",
                  fontSize: 18,
                  opacity: 0.7,
                }}>
                  {narration}
                </div>
              ){"}"}
              <div style={{
                position: "absolute",
                bottom: "5%",
                right: "5%",
                fontSize: 14,
                opacity: 0.5,
              }}>
                Shot {idx:03d} · {camera}
              </div>
            </AbsoluteFill>
          );
        }};
        """)

        comp_path = src_dir / f"Shot{idx:03d}.tsx"
        comp_path.write_text(shot_ts, encoding="utf-8")
        shot_components.append(
            f'  {{ id: "Shot{idx:03d}", component: Shot{idx:03d}, durationInFrames: {dur_frames}, fps: {fps}, width: 1080, height: 1920 }}'
        )

    # Generate Root.tsx with all compositions
    import_lines = "\n".join(
        f'import {{ Shot{idx:03d} }} from "./Shot{idx:03d}";'
        for idx in [s["shot_index"] for s in shots]
    )

    comp_registrations = ",\n".join(shot_components)

    root_tsx = textwrap.dedent(f"""\
    import {{ Composition }} from "remotion";
    {import_lines}

    export const RemotionRoot: React.FC = () => {{
      const compositions = [
    {comp_registrations}
      ];

      return (
        <>
          {{compositions.map((comp) => (
            <Composition
              key={{comp.id}}
              id={{comp.id}}
              component={{comp.component}}
              durationInFrames={{comp.durationInFrames}}
              fps={{comp.fps}}
              width={{comp.width}}
              height={{comp.height}}
              defaultProps={{
                panelRefs: [],
                dialogue: "",
                narration: "",
              }}
            />
          ))}}
        </>
      );
    }};
    """)

    (src_dir / "Root.tsx").write_text(root_tsx, encoding="utf-8")

    # Generate Index.ts entry
    index_ts = 'export { RemotionRoot } from "./Root.tsx";\n'
    (src_dir / "index.ts").write_text(index_ts, encoding="utf-8")

    # Generate package.json
    package_json = {
        "name": "lookbook-remotion-export",
        "version": "0.1.0",
        "description": f"Remotion video project generated by lookBOOK — {len(shots)} shots, {total_dur:.1f}s",
        "scripts": {
            "start": "remotion studio",
            "build": "remotion render",
            "upgrade": "remotion upgrade",
        },
        "dependencies": {
            "react": "^18.3.1",
            "react-dom": "^18.3.1",
            "remotion": "^4.0.0",
            "@remotion/player": "^4.0.0",
            "@remotion/transitions": "^4.0.0",
        },
        "devDependencies": {
            "@types/react": "^18.3.0",
            "typescript": "^5.5.0",
        },
    }
    (export_dir / "package.json").write_text(
        json.dumps(package_json, indent=2), encoding="utf-8"
    )

    # Generate tsconfig.json
    tsconfig = {
        "compilerOptions": {
            "target": "ES2022",
            "module": "ES2022",
            "moduleResolution": "bundler",
            "jsx": "react-jsx",
            "strict": True,
            "esModuleInterop": True,
            "skipLibCheck": True,
            "forceConsistentCasingInFileNames": True,
        },
        "include": ["src"],
    }
    (export_dir / "tsconfig.json").write_text(json.dumps(tsconfig, indent=2), encoding="utf-8")

    # Generate README
    readme = textwrap.dedent(f"""\
    # lookBOOK Remotion Export

    Generated from {Path(shot_graph_path).name}
    {len(shots)} shots · {total_dur:.1f}s · {fps}fps

    ## Setup

    ```bash
    cd "{export_dir}"
    npm install
    ```

    ## Development

    ```bash
    npm start        # Opens Remotion Studio
    npm run build    # Renders all compositions
    ```

    ## Compositions

    {chr(10).join(f'- Shot{idx:03d}: {s["type"]} ({s["duration_seconds"]}s) — {s.get("camera", "static")}' for idx, s in enumerate(shots[:10]))}
    {"..." if len(shots) > 10 else ""}

    ## Transitions

    Install @remotion/transitions:
    ```bash
    npx remotion add @remotion/transitions
    ```

    Then wrap Sequence groups with TransitionSeries:
    ```tsx
    import {{TransitionSeries, linearTiming}} from "@remotion/transitions";
    import {{fade}} from "@remotion/transitions/fade";
    ```
    """)

    (export_dir / "README.md").write_text(readme, encoding="utf-8")

    result = {
        "schema": "lookbook.remotion_export.v0.2",
        "total_shots": len(shots),
        "total_duration_seconds": total_dur,
        "fps": fps,
        "resolution": {"width": 1080, "height": 1920},
        "files": {
            "root": "src/Root.tsx",
            "package_json": "package.json",
            "tsconfig": "tsconfig.json",
            "readme": "README.md",
            "shot_components": [
                f"src/Shot{idx:03d}.tsx"
                for idx in [s["shot_index"] for s in shots]
            ],
        },
        "setup_instructions": [
            f"cd {export_dir}",
            "npm install",
            "npm start",
        ],
    }

    write_json(export_dir / "remotion_export.json", result)

    return result
