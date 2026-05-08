from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNS_DIR = ROOT / ".runs"
DEFAULT_DB_PATH = DEFAULT_RUNS_DIR / "agent.db"
DEFAULT_SOURCE_DIR = ROOT / "docs" / "sources"
DEFAULT_WORKSPACE_DIR = ROOT / "workspace"
DEFAULT_TRACE_DIR = ROOT / "traces"
DEFAULT_EVAL_FIXTURE = ROOT / "evals" / "questions.jsonl"
DEFAULT_EVAL_RESULTS_DIR = ROOT / "eval_results"

