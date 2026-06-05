from pathlib import Path
from lookbook.project import init_project
from lookbook.pipeline.analyze import analyze_source
from lookbook.pipeline.true_animation_packet import create_true_animation_packet
from lookbook.pipeline.export_web import export_web
from lookbook.lab import install_demo_lab


def test_init_project(tmp_path: Path):
    project = init_project(tmp_path / "demo", "Demo")
    assert (project / "manifest.json").exists()
    assert (project / "RIGHTS.md").exists()
    assert (project / "source").is_dir()


def test_analyze_source_text(tmp_path: Path):
    project = init_project(tmp_path / "demo", "Demo")
    source = project / "source" / "sample.txt"
    source.write_text("hello", encoding="utf-8")
    result = analyze_source(source, project)
    assert result["source_type"] == "txt"
    assert (project / "analysis" / "source_analysis.json").exists()


def test_true_animation_packet(tmp_path: Path):
    project = init_project(tmp_path / "demo", "Demo")
    out = create_true_animation_packet(project, "runway")
    assert (out / "TRUE_ANIMATION_PROMPT.md").exists()
    assert (out / "SHOT_LIST.md").exists()
    assert (out / "QUALITY_GATE.md").exists()


def test_export_web(tmp_path: Path):
    project = init_project(tmp_path / "demo", "Demo")
    out = export_web(project, project / "exports" / "review.html")
    assert out.exists()
    assert "lookBOOK" in out.read_text(encoding="utf-8")


def test_install_demo_lab(tmp_path: Path):
    out = install_demo_lab(tmp_path)
    assert (out / "index.html").exists()
