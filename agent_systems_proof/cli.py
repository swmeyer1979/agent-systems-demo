from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agent import ResearchAgent, SimulatedInterruption
from .evaluator import Evaluator
from .paths import (
    DEFAULT_DB_PATH,
    DEFAULT_EVAL_FIXTURE,
    DEFAULT_EVAL_RESULTS_DIR,
    DEFAULT_SOURCE_DIR,
    DEFAULT_TRACE_DIR,
    DEFAULT_WORKSPACE_DIR,
)
from .safety import validate_slug
from .storage import RunStore
from .tools import build_registry
from .tracing import JsonlTracer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agent-proof")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="run or resume the research agent")
    run_parser.add_argument("--run-id", required=True)
    run_parser.add_argument("--question")
    run_parser.add_argument("--resume", action="store_true")
    run_parser.add_argument("--stop-after-step", type=int)

    eval_parser = subparsers.add_parser("eval", help="run eval gates")
    eval_parser.add_argument("--fixture", default=str(DEFAULT_EVAL_FIXTURE))

    args = parser.parse_args(argv)

    if args.command == "run":
        return _run_command(args)
    if args.command == "eval":
        return _eval_command(args)
    raise AssertionError(args.command)


def _run_command(args: argparse.Namespace) -> int:
    try:
        run_id = validate_slug(args.run_id, "run_id")
        store = RunStore(DEFAULT_DB_PATH)
        tracer = JsonlTracer(DEFAULT_TRACE_DIR, run_id)
        agent = ResearchAgent(
            store=store,
            tools=build_registry(DEFAULT_SOURCE_DIR, DEFAULT_WORKSPACE_DIR),
            tracer=tracer,
            workspace_dir=DEFAULT_WORKSPACE_DIR,
        )
        result = agent.run(
            run_id=run_id,
            question=args.question,
            resume=args.resume,
            stop_after_step=args.stop_after_step,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except SimulatedInterruption as exc:
        print(f"INTERRUPTED: {exc}")
        print(f"Resume with: python3 -m agent_systems_proof run --run-id {args.run_id} --resume")
        return 75
    print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    return 0


def _eval_command(args: argparse.Namespace) -> int:
    store = RunStore(DEFAULT_DB_PATH)
    evaluator = Evaluator(
        fixture_path=Path(args.fixture),
        source_dir=DEFAULT_SOURCE_DIR,
        workspace_dir=DEFAULT_WORKSPACE_DIR,
        trace_dir=DEFAULT_TRACE_DIR,
        store=store,
        results_dir=DEFAULT_EVAL_RESULTS_DIR,
    )
    try:
        summary = evaluator.run()
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
