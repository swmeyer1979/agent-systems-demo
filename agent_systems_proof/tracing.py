from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .safety import safe_child_file, validate_slug


class JsonlTracer:
    """Small JSONL tracer with enough structure to inspect agent trajectories."""

    def __init__(self, trace_dir: Path, run_id: str) -> None:
        self.run_id = validate_slug(run_id, "run_id")
        self.trace_dir = trace_dir
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.path = safe_child_file(self.trace_dir, self.run_id, ".jsonl", "run_id")

    def event(self, event_type: str, **payload: Any) -> None:
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "run_id": self.run_id,
            "event": event_type,
            "estimated_cost_usd": payload.pop("estimated_cost_usd", 0.0),
            **payload,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")

    def timed(self, event_type: str, **payload: Any) -> "_TraceTimer":
        return _TraceTimer(self, event_type, payload)


class _TraceTimer:
    def __init__(self, tracer: JsonlTracer, event_type: str, payload: dict[str, Any]) -> None:
        self.tracer = tracer
        self.event_type = event_type
        self.payload = payload
        self.start = 0.0

    def __enter__(self) -> "_TraceTimer":
        self.start = time.perf_counter()
        self.tracer.event(f"{self.event_type}.start", **self.payload)
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        elapsed_ms = round((time.perf_counter() - self.start) * 1000, 3)
        status = "error" if exc else "ok"
        error = str(exc) if exc else None
        self.tracer.event(
            f"{self.event_type}.finish",
            **self.payload,
            elapsed_ms=elapsed_ms,
            status=status,
            error=error,
        )
