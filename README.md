<p align="center"><img src="assets/brand/lookbook-logo-horizontal.svg" alt="lookBOOK logo" width="860"></p>

<p align="center"><strong>Open-source book-to-animation compiler.</strong><br>Extract characters. Preserve scene intent. Generate true image-to-video handoff packets.</p>

<p align="center"><a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-F2C14E.svg"></a> <a href="ROADMAP.md"><img alt="Status" src="https://img.shields.io/badge/status-alpha-1AE0CF.svg"></a> <a href="docs/product/TRUE_ANIMATION_STANDARD.md"><img alt="True Animation" src="https://img.shields.io/badge/standard-true%20animation-7C5CFF.svg"></a></p>

## What is lookBOOK?

**lookBOOK** is an open-source compiler layer for turning books, comics, illustrated pages, and story material into structured animation projects.

It is not a video model. It is the missing layer between a source page and tools like Runway, Google Flow/Veo, Kling, Pika, Luma, or local generation stacks.

```text
book / comic / illustrated page
→ source analysis
→ character extraction
→ scene intent graph
→ shot list
→ dialogue + sound script
→ true image-to-video handoff packet
→ generated animated shots
```

## The core standard

lookBOOK is built around one hard distinction:

```text
Motion-comic preview:
  zooms, pans, overlays, particles, still-image movement

True animation:
  characters move inside the scene
  bodies and limbs act
  enemies react
  cloth/scarf/ribbon moves independently
  dialogue timing matters
```

**Not a slideshow. Real animation planning.**

## Quick start

```bash
git clone https://github.com/your-org/lookBOOK.git
cd lookBOOK
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,image]"
lookbook demo my-demo
lookbook true-animation-packet my-demo --target runway
lookbook export-web my-demo my-demo/exports/review.html
```

## Browser Demo Lab

Open `demo-lab/index.html`, or run:

```bash
python scripts/run_demo_lab.py
```

The lab lets users drop in a page or keyframe and generate a true-animation handoff packet locally.

## CLI

```bash
lookbook init my-project --name "My Animated Book"
lookbook analyze-source page.png my-project
lookbook true-animation-packet my-project --target runway
lookbook true-animation-packet my-project --target veo
lookbook export-web my-project my-project/exports/review.html
lookbook install-demo-lab ./lab-output
```

## MoneyPrinterTurbo Integration

lookBOOK embeds [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) as a submodule under `tools/moneyprinter/` for short-form stock-footage generation from book excerpts.

### One-command setup

```bash
# Unix / macOS
./scripts/init-moneyprinter.sh

# Windows
scripts\init-moneyprinter.bat
```

### Configuration

Project-specific defaults live in `config/moneyprinter.toml`. It disables voiceover and targets 15-second clips by default. Copy or symlink it to `tools/moneyprinter/config.toml` to activate.

### Using the bridge

```python
from tools.shared.mpt_bridge import get_bridge

bridge = get_bridge()
task = bridge.start_task(
    video_subject="A dragon landing on a castle tower",
    target_duration=15,
    voice_name="",
    subtitle_enabled=False,
)
print(task["task_id"])
```

Start the MPT API server locally:

```bash
cd tools/moneyprinter && python main.py
```

## Demo

See `examples/vector-bay7/` for original keyframes and a true-animation prompt pack.

## License

MIT for the software. Imported books, scans, artwork, voices, fonts, and generated assets have their own rights considerations.
