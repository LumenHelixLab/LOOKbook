"""lookBOOK — Telemetry & Cost Tracking (M5: Production Hardening)

Lightweight production instrumentation. Collects:
- Vision LLM API costs per provider
- Pipeline stage timings
- Export artifact counts
- Cache hit rates

No external dependencies; writes to local JSON logs.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from contextlib import contextmanager


TELEMETRY_DIR = Path.home() / ".lookbook" / "telemetry"
TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)

_SESSION_ID = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
_LOG_PATH = TELEMETRY_DIR / f"session_{_SESSION_ID}.jsonl"

# Provider pricing per 1K tokens (input / output) — rough estimates
_PROVIDER_RATES = {
    "openai": {"input": 0.005, "output": 0.015},      # gpt-4o vision
    "claude": {"input": 0.003, "output": 0.015},      # claude-3-opus vision
    "gemini": {"input": 0.001, "output": 0.004},      # gemini-1.5-pro vision
}


def _log(event: dict[str, Any]) -> None:
    event["ts"] = datetime.now(timezone.utc).isoformat()
    event["session"] = _SESSION_ID
    with _LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def log_vision_call(provider: str, model: str, input_tokens: int = 0, output_tokens: int = 0) -> float:
    """Log a vision LLM call and return estimated cost USD."""
    rates = _PROVIDER_RATES.get(provider, _PROVIDER_RATES["openai"])
    cost = (input_tokens / 1000) * rates["input"] + (output_tokens / 1000) * rates["output"]
    _log({
        "type": "vision_call",
        "provider": provider,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 6),
    })
    return cost


def log_pipeline_stage(stage: str, project: str | Path, details: dict[str, Any] | None = None) -> None:
    _log({
        "type": "pipeline_stage",
        "stage": stage,
        "project": str(project),
        "details": details or {},
    })


def log_export(platform: str, project: str | Path, count: int) -> None:
    _log({
        "type": "export",
        "platform": platform,
        "project": str(project),
        "artifact_count": count,
    })


def log_cache_hit(provider: str, hit: bool) -> None:
    _log({
        "type": "cache",
        "provider": provider,
        "hit": hit,
    })


@contextmanager
def timed_stage(stage: str, project: str | Path):
    """Context manager to time a pipeline stage."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        _log({
            "type": "timing",
            "stage": stage,
            "project": str(project),
            "elapsed_seconds": round(elapsed, 3),
        })


def session_summary() -> dict[str, Any]:
    """Read the current session log and return aggregate stats."""
    if not _LOG_PATH.exists():
        return {"session": _SESSION_ID, "events": 0}

    events = []
    with _LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))

    total_cost = sum(e.get("cost_usd", 0) for e in events if e["type"] == "vision_call")
    vision_calls = len([e for e in events if e["type"] == "vision_call"])
    cache_hits = len([e for e in events if e["type"] == "cache" and e["hit"]])
    cache_misses = len([e for e in events if e["type"] == "cache" and not e["hit"]])
    exports = {}
    for e in events:
        if e["type"] == "export":
            plat = e["platform"]
            exports[plat] = exports.get(plat, 0) + e.get("artifact_count", 0)

    return {
        "session": _SESSION_ID,
        "events": len(events),
        "vision_calls": vision_calls,
        "vision_cost_usd": round(total_cost, 4),
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "exports": exports,
        "log_path": str(_LOG_PATH),
    }
