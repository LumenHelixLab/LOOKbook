"""Tests for NOTEtoolsLM vault → lookBOOK import."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lookbook.pipeline.vault_import import (
    SOURCE_MANIFEST_SCHEMA,
    import_vault_manifest,
)


@pytest.fixture
def sample_manifest() -> dict:
    return {
        "format": SOURCE_MANIFEST_SCHEMA,
        "title": "Deep Dive: AI Video",
        "source_type": "research",
        "files": [{
            "name": "deep-dive-ai-video.md",
            "kind": "md",
            "content": "# Overview\nNotebookLM research on AI video pipelines.\n",
        }],
        "metadata": {
            "artifactId": "art-1",
            "notebookId": "nb-1",
            "type": "briefing",
        },
    }


def test_import_writes_source_and_record(tmp_path: Path, sample_manifest: dict) -> None:
    project = tmp_path / "vault-demo"
    result = import_vault_manifest(project, sample_manifest)
    assert result["files_written"] == 1
    source_file = project / "source" / "deep-dive-ai-video.md"
    assert source_file.exists()
    assert "AI video" in source_file.read_text(encoding="utf-8")
    record = json.loads((project / "analysis" / "vault_import.json").read_text(encoding="utf-8"))
    assert record["metadata"]["artifactId"] == "art-1"


def test_import_rejects_empty_files(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="non-empty"):
        import_vault_manifest(tmp_path / "bad", {"format": SOURCE_MANIFEST_SCHEMA, "files": []})


def test_import_from_json_path(tmp_path: Path, sample_manifest: dict) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(sample_manifest), encoding="utf-8")
    project = tmp_path / "from-file"
    result = import_vault_manifest(project, manifest_path)
    assert result["files_written"] == 1