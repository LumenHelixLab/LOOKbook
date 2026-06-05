from __future__ import annotations
from pathlib import Path
from ..models import write_json

PROMPT = """# TRUE ANIMATION HANDOFF PROMPT

## Non-negotiable
Generate true character animation, not a pan-and-zoom motion comic.

Characters must move inside the scene:
- body motion
- limb motion
- head turns
- attacks / reactions
- cloth/scarf/ribbon motion
- speaking timing or dialogue pacing

## Negative prompt
Do not create a slideshow. Do not only move the camera. Do not alter character designs wildly. Do not add copyrighted superhero symbols, franchise motifs, or famous costume elements.
"""

SHOT_TEMPLATE = """# Shot List

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

QUALITY = """# True Animation Quality Gate

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

def create_true_animation_packet(project: str | Path, target: str = "runway") -> Path:
    project = Path(project)
    out = project / "prompts" / target
    out.mkdir(parents=True, exist_ok=True)
    (out / "TRUE_ANIMATION_PROMPT.md").write_text(PROMPT, encoding="utf-8")
    (out / "SHOT_LIST.md").write_text(SHOT_TEMPLATE, encoding="utf-8")
    (out / "QUALITY_GATE.md").write_text(QUALITY, encoding="utf-8")
    write_json(project / "analysis" / f"{target}_true_animation_packet.json", {"schema":"lookbook.true_animation_packet.v0.2","target":target,"files":[str((out/"TRUE_ANIMATION_PROMPT.md").relative_to(project)),str((out/"SHOT_LIST.md").relative_to(project)),str((out/"QUALITY_GATE.md").relative_to(project))]})
    return out
