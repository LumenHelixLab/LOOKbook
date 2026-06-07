"""Tests for telemetry & cost tracking (M5)."""

import json
from pathlib import Path

from lookbook import telemetry


class TestLogVisionCall:
    def test_returns_cost(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(telemetry, "_LOG_PATH", tmp_path / "test.jsonl")
        cost = telemetry.log_vision_call("openai", "gpt-4o", input_tokens=1000, output_tokens=500)
        assert cost > 0
        assert isinstance(cost, float)

    def test_writes_event(self, tmp_path: Path, monkeypatch):
        log_path = tmp_path / "test.jsonl"
        monkeypatch.setattr(telemetry, "_LOG_PATH", log_path)
        telemetry.log_vision_call("gemini", "gemini-pro", input_tokens=2000, output_tokens=1000)
        lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        event = json.loads(lines[0])
        assert event["type"] == "vision_call"
        assert event["provider"] == "gemini"


class TestSessionSummary:
    def test_empty_session(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(telemetry, "_LOG_PATH", tmp_path / "empty.jsonl")
        summary = telemetry.session_summary()
        assert summary["events"] == 0

    def test_with_events(self, tmp_path: Path, monkeypatch):
        log_path = tmp_path / "test.jsonl"
        monkeypatch.setattr(telemetry, "_LOG_PATH", log_path)
        telemetry.log_vision_call("openai", "gpt-4o", 1000, 500)
        telemetry.log_export("runway", "/tmp/proj", 3)
        telemetry.log_cache_hit("openai", True)
        summary = telemetry.session_summary()
        assert summary["events"] == 3
        assert summary["vision_calls"] == 1
        assert summary["cache_hits"] == 1
        assert summary["exports"]["runway"] == 3


class TestTimedStage:
    def test_logs_timing(self, tmp_path: Path, monkeypatch):
        log_path = tmp_path / "test.jsonl"
        monkeypatch.setattr(telemetry, "_LOG_PATH", log_path)
        with telemetry.timed_stage("test_stage", "/tmp/proj"):
            pass
        lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        event = json.loads(lines[0])
        assert event["type"] == "timing"
        assert event["stage"] == "test_stage"
        assert event["elapsed_seconds"] >= 0
