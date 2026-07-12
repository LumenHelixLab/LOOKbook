# LOOKbook

<p align="center">
  <a href="https://lumenhelix.com">
    <img src="docs/assets/lumenhelix-logo.svg" alt="LumenHelix Solutions" width="180">
  </a>
</p>

<h3 align="center">Open-source book-to-animation compiler.</h3>

<p align="center">
  <a href="https://lumenhelixsolutions.github.io/LOOKbook/">
    <img src="https://img.shields.io/badge/Launch_Page-LOOKbook-00D4FF?style=flat-square&logo=githubpages&logoColor=white" alt="Launch Page">
  </a>
  <a href="https://lumenhelix.com">
    <img src="https://img.shields.io/badge/Built_by-LumenHelix-7C3AED?style=flat-square" alt="Built by LumenHelix">
  </a>
  <img src="https://img.shields.io/badge/license-MIT-8A95A8?style=flat-square" alt="License">
</p>

---

**LOOKbook** is part of the [LumenHelix Solutions](https://lumenhelix.com) portfolio — applied symbolic dynamics & reversible computation for deterministic, traceable AI systems.

LOOKbook is the LumenHelix open-source compiler for turning books, comics, and illustrated pages into structured animation projects. It extracts characters, preserves scene intent, and emits true image-to-video handoff packets for generative video pipelines.

## Why this exists

- **Preserve creative intent.** Scene graphs and character consistency keep the story coherent across every generated shot.
- **Stay pipeline-agnostic.** Export to Runway, Veo, Kling, Pika, Luma, or local stacks from one source of truth.
- **Own your workflow.** Local-first Python CLI and browser lab. No mandatory cloud, no lock-in.

## Quick start

Install and run LOOKbook in under two minutes.

### macOS / Linux

```bash
# Clone
git clone https://github.com/lumenhelixsolutions/LOOKbook.git
cd LOOKbook

# Install & run
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[lab,dev]"
npm install
lookbook demo my-demo
```

### Windows (PowerShell)

```powershell
# Clone
git clone https://github.com/lumenhelixsolutions/LOOKbook.git
Set-Location LOOKbook

# Install & run
python -m venv .venv
.venv\Scripts\pip install -e ".[lab,dev]"
npm install
lookbook demo my-demo
```

### Windows (Git Bash / WSL)

```bash
git clone https://github.com/lumenhelixsolutions/LOOKbook.git
cd LOOKbook
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[lab,dev]"
npm install
lookbook demo my-demo
```

> **Device note:** LOOKbook is tested on Windows 11, macOS Sonoma, Ubuntu 22.04/24.04, and modern mobile browsers.

## Full documentation

Visit the launch page for architecture, API reference, and deployment guides:  
**https://lumenhelixsolutions.github.io/LOOKbook/**

## Features

| Feature | What it gives you |
|---------|-------------------|
| Source analysis | Ingest books, comics, and illustrated pages and break them into panels, characters, and scene intent. |
| True animation standard | Distinguish motion-comic previews from real animation where bodies, limbs, cloth, and dialogue timing matter. |
| Image-to-video handoff | Export structured shot packets ready for Runway, Veo, Kling, Pika, Luma, and local image-to-video stacks. |
| Demo Lab Gen 2 | A unified pipeline server with OCR, vision interpretation, and a browser review UI on port 8042. |

## Architecture at a glance

```
lookBOOK/
├── lookbook/       Python CLI + analysis engine
├── demo-lab/       Browser review lab (port 8042)
├── demo-lab-react/ Ant Design UI
├── examples/       Sample keyframes and prompt packs
└── tools/          MoneyPrinterTurbo bridge
```

## Development

```bash
# Start the unified pipeline lab
python -m lookbook.lab_server
# In another terminal, build the React UI
cd demo-lab-react && npm install && npm run build
```

## Roadmap

- [ ] Research-to-story portfolio E2E harness
- [ ] Vault import and Obsidian handoff polish
- [ ] CineForge live API push and review sync

## Support & consulting

Need deterministic AI systems with full traceability? LumenHelix builds reversible computation kernels, governance layers, and end-to-end AI integrations.

- **Website:** https://lumenhelix.com
- **Services:** AI diagnostics, B.Y.O. support packages, governance audits
- **Research:** TEN² kernel, R.U.B.I.C. boundary discipline, C.O.R.E. constraint lens

## License

Released under the MIT License. Imported books, scans, artwork, voices, fonts, and generated assets have their own rights considerations.

---

<p align="center">
  <sub>Engineered by <a href="https://lumenhelix.com">LumenHelix Solutions</a> — Applied Symbolic Dynamics & Reversible Computation.</sub>
</p>
