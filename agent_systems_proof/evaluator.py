from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .agent import ResearchAgent
from .judge import HeuristicReportJudge
from .safety import validate_slug
from .storage import RunStore
from .tools import build_registry
from .tracing import JsonlTracer


@dataclass(frozen=True)
class EvalGate:
    name: str
    passed: bool
    details: dict[str, Any]


class Evaluator:
    def __init__(
        self,
        *,
        fixture_path: Path,
        source_dir: Path,
        workspace_dir: Path,
        trace_dir: Path,
        store: RunStore,
        results_dir: Path,
    ) -> None:
        self.fixture_path = fixture_path
        self.source_dir = source_dir
        self.workspace_dir = workspace_dir
        self.trace_dir = trace_dir
        self.store = store
        self.results_dir = results_dir
        self.judge = HeuristicReportJudge()

    def run(self) -> dict[str, Any]:
        self.results_dir.mkdir(parents=True, exist_ok=True)
        fixtures = self._load_fixtures()
        gates: list[EvalGate] = []
        runs = []

        for fixture in fixtures:
            fixture_id = validate_slug(fixture["id"], "fixture.id")
            run_id = validate_slug(f"eval-{fixture_id}", "run_id")
            tracer = JsonlTracer(self.trace_dir, run_id)
            agent = ResearchAgent(
                store=self.store,
                tools=build_registry(self.source_dir, self.workspace_dir),
                tracer=tracer,
                workspace_dir=self.workspace_dir,
            )
            result = agent.run(run_id=run_id, question=fixture["question"], resume=False)
            if result.output_path is None:
                raise AssertionError("eval run produced no report")
            report = Path(result.output_path).read_text(encoding="utf-8")
            runs.append({"run_id": run_id, "report": result.output_path, "trace": result.trace_path})
            gates.extend(self._single_turn_gates(fixture, report))
            gates.append(self._judge_gate(run_id, report))
            gates.append(self._trajectory_gate(run_id, fixture))
            gates.append(self._end_state_gate(run_id, result.output_path, report))

        summary = {
            "passed": all(gate.passed for gate in gates),
            "gate_count": len(gates),
            "failed_gates": [gate.name for gate in gates if not gate.passed],
            "gates": [gate.__dict__ for gate in gates],
            "runs": runs,
        }
        (self.results_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return summary

    def _load_fixtures(self) -> list[dict[str, Any]]:
        fixtures = []
        for line in self.fixture_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                fixtures.append(json.loads(line))
        return fixtures

    def _single_turn_gates(self, fixture: dict[str, Any], report: str) -> list[EvalGate]:
        lower = report.lower()
        required_terms = fixture["required_terms"]
        missing_terms = [term for term in required_terms if term.lower() not in lower]
        return [
            EvalGate(
                name=f"single_turn.required_terms.{fixture['id']}",
                passed=not missing_terms,
                details={"missing_terms": missing_terms, "required_terms": required_terms},
            )
        ]

    def _judge_gate(self, run_id: str, report: str) -> EvalGate:
        result = self.judge.grade(report)
        return EvalGate(
            name=f"judge.report_quality.{run_id}",
            passed=result.passed,
            details={"score": result.score, "criteria": result.criteria},
        )

    def _trajectory_gate(self, run_id: str, fixture: dict[str, Any]) -> EvalGate:
        step_names = self.store.list_step_names(run_id)
        tool_calls = self.store.list_tool_calls(run_id)
        tool_names = [call["tool_name"] for call in tool_calls]
        expected_steps = ["plan", "search", "read_sources", "draft_report", "self_check", "write_report"]
        expected_tools = fixture["expected_tool_sequence"]
        expected_source_ids = fixture["expected_source_ids"]
        read_source_ids = [
            call["args"].get("source_id")
            for call in tool_calls
            if call["tool_name"] == "read_source"
        ]
        search_queries = [
            call["args"].get("query", "")
            for call in tool_calls
            if call["tool_name"] == "search_sources"
        ]
        write_run_ids = [
            call["args"].get("run_id")
            for call in tool_calls
            if call["tool_name"] == "write_report"
        ]
        wrong_order = tool_names != expected_tools
        wrong_sources = read_source_ids != expected_source_ids
        wrong_search = not search_queries or fixture["question"] not in search_queries[0]
        wrong_write_target = write_run_ids != [run_id]
        return EvalGate(
            name=f"trajectory.{run_id}",
            passed=not any(
                [
                    step_names != expected_steps,
                    wrong_order,
                    wrong_sources,
                    wrong_search,
                    wrong_write_target,
                ]
            ),
            details={
                "step_names": step_names,
                "expected_steps": expected_steps,
                "tool_names": tool_names,
                "expected_tool_sequence": expected_tools,
                "read_source_ids": read_source_ids,
                "expected_source_ids": expected_source_ids,
                "search_queries": search_queries,
                "write_run_ids": write_run_ids,
            },
        )

    def _end_state_gate(self, run_id: str, output_path: str, report: str) -> EvalGate:
        run = self.store.get_run(run_id)
        path = Path(output_path)
        passed = bool(
            run
            and run.status == "completed"
            and path.exists()
            and "[S1]" in report
            and "Acceptance Checks" in report
        )
        return EvalGate(
            name=f"end_state.{run_id}",
            passed=passed,
            details={
                "run_status": run.status if run else None,
                "output_path": output_path,
                "exists": path.exists(),
                "has_citation": "[S1]" in report,
            },
        )
