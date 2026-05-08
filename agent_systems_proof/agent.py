from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .judge import HeuristicReportJudge
from .safety import validate_slug
from .storage import RunStore
from .tools import ToolRegistry
from .tracing import JsonlTracer


class SimulatedInterruption(RuntimeError):
    pass


@dataclass(frozen=True)
class AgentResult:
    run_id: str
    status: str
    output_path: str | None
    trace_path: str


@dataclass(frozen=True)
class AgentStep:
    name: str
    handler: Callable[[dict[str, Any]], dict[str, Any]]


class ResearchAgent:
    def __init__(
        self,
        *,
        store: RunStore,
        tools: ToolRegistry,
        tracer: JsonlTracer,
        workspace_dir: Path,
    ) -> None:
        self.store = store
        self.tools = tools
        self.tracer = tracer
        self.workspace_dir = workspace_dir
        self.judge = HeuristicReportJudge()

    def steps(self) -> list[AgentStep]:
        return [
            AgentStep("plan", self._plan),
            AgentStep("search", self._search),
            AgentStep("read_sources", self._read_sources),
            AgentStep("draft_report", self._draft_report),
            AgentStep("self_check", self._self_check),
            AgentStep("write_report", self._write_report),
        ]

    def run(
        self,
        *,
        run_id: str,
        question: str | None,
        resume: bool = False,
        stop_after_step: int | None = None,
    ) -> AgentResult:
        run_id = validate_slug(run_id, "run_id")
        steps = self.steps()
        if resume:
            run = self.store.get_run(run_id)
            if run is None:
                raise KeyError(f"cannot resume missing run_id: {run_id}")
            question = run.question
            self.tracer.event("run.resume", current_step=run.current_step, status=run.status)
        else:
            if not question:
                raise ValueError("question is required for a fresh run")
            self.store.create_run(run_id, question, len(steps), overwrite=True)
            self.tracer.event("run.create", question=question, total_steps=len(steps))

        context = self._rehydrate_context(run_id)
        context["run_id"] = run_id
        context["question"] = question

        completed_this_process = 0
        completed = self.store.completed_steps(run_id)
        start_index = len(completed)

        try:
            for step_index, step in enumerate(steps[start_index:], start=start_index):
                input_payload = self._step_input(context)
                self.store.start_step(run_id, step_index, step.name, input_payload)
                with self.tracer.timed("step", step_index=step_index, step_name=step.name):
                    output = step.handler(context)
                context[step.name] = output
                self.store.finish_step(run_id, step_index, output)
                self.store.update_run(run_id, current_step=step_index + 1, status="running")
                completed_this_process += 1
                if stop_after_step is not None and completed_this_process >= stop_after_step:
                    self.store.update_run(run_id, status="interrupted")
                    self.tracer.event("run.interrupted", after_step=step_index, reason="simulated stop")
                    raise SimulatedInterruption(f"simulated stop after {completed_this_process} step(s)")
        except SimulatedInterruption:
            raise
        except Exception as exc:
            self.store.update_run(run_id, status="failed")
            self.tracer.event("run.failed", error=str(exc))
            raise

        output_path = context.get("write_report", {}).get("path")
        self.store.update_run(run_id, status="completed", current_step=len(steps), output_path=output_path)
        self.tracer.event("run.completed", output_path=output_path)
        return AgentResult(run_id=run_id, status="completed", output_path=output_path, trace_path=str(self.tracer.path))

    def _rehydrate_context(self, run_id: str) -> dict[str, Any]:
        context: dict[str, Any] = {}
        for step in self.steps():
            output = self.store.get_step_output(run_id, step.name)
            if output is not None:
                context[step.name] = output
        return context

    def _step_input(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "question": context.get("question"),
            "available_context": sorted(key for key in context if key not in {"question", "run_id"}),
        }

    def _tool(self, step_index: int, active_run_id: str, name: str, **kwargs: Any) -> dict[str, Any]:
        start = time.perf_counter()
        status = "ok"
        try:
            output = self.tools.call(name, **kwargs)
            return output
        except Exception as exc:
            status = "error"
            output = {"error": str(exc)}
            raise
        finally:
            latency_ms = round((time.perf_counter() - start) * 1000, 3)
            self.store.record_tool_call(
                active_run_id,
                step_index,
                name,
                kwargs,
                output,
                status=status,
                latency_ms=latency_ms,
            )
            self.tracer.event(
                "tool.call",
                step_index=step_index,
                tool_name=name,
                args=kwargs,
                status=status,
                latency_ms=latency_ms,
            )

    def _plan(self, context: dict[str, Any]) -> dict[str, Any]:
        question = str(context["question"])
        focus_terms = [
            "tool use",
            "durability",
            "evals",
            "traces",
            "cost",
            "sandboxing",
            "human approval",
        ]
        return {
            "question": question,
            "focus_terms": focus_terms,
            "planned_tools": ["search_sources", "read_source", "write_report"],
            "subtasks": [
                "Find source evidence.",
                "Read only the top-ranked source files.",
                "Draft a cited answer.",
                "Score the answer against a rubric.",
                "Write the report to disk.",
            ],
            "budget_usd": 0.0,
        }

    def _search(self, context: dict[str, Any]) -> dict[str, Any]:
        query = f"{context['question']} {' '.join(context['plan']['focus_terms'])}"
        return self._tool(1, context["run_id"], "search_sources", query=query, limit=5)

    def _read_sources(self, context: dict[str, Any]) -> dict[str, Any]:
        results = context["search"]["results"][:5]
        docs = []
        for result in results:
            docs.append(self._tool(2, context["run_id"], "read_source", source_id=result["source_id"]))
        return {"sources": docs}

    def _draft_report(self, context: dict[str, Any]) -> dict[str, Any]:
        docs = context["read_sources"]["sources"]
        citation_map = {doc["source_id"]: f"S{idx}" for idx, doc in enumerate(docs, start=1)}
        source_lines = []
        evidence_lines = []
        for doc in docs:
            label = citation_map[doc["source_id"]]
            source_lines.append(f"- [{label}] {doc['title']} ({doc['source_id']})")
            for point in doc["key_points"][:2]:
                evidence_lines.append(f"- [{label}] {point}")

        report = f"""# Agent Systems Proof Report

Question: {context['question']}

## Bottom Line

Production-ready agent systems are harness problems before they are model problems. The core is a loop that can choose tools, preserve useful context, recover state, emit traces, enforce guardrails, and prove quality with evals. No network is used in this demo; the point is to make the harness behavior inspectable.

## Evidence

{chr(10).join(evidence_lines)}

## What This Demo Proves

- Tool use: the agent searches a local corpus, reads selected sources, and writes a report through explicit tools rather than hidden helper calls.
- Durability: every step is checkpointed in SQLite before the next step starts, so a process stop can resume from the last completed step.
- Traceability: every step and tool call is written to JSONL with status and latency, making the trajectory reviewable.
- Eval discipline: the repository includes single-turn, trajectory, judge-style, and end-state checks. Vibes are not an acceptance criterion.
- Cost control: this offline version has zero model spend, and the plan records a budget field so a real model adapter has a place to enforce cost.
- Guardrails: the write surface is narrow, source reads are constrained to the local corpus, and the self-check fails reports without citations.

## Failure Modes

- A real LLM adapter could choose poor tools unless tool descriptions and schemas are tested with trajectory evals.
- A larger source corpus would need retrieval quality measurement; vector search would be premature until recall failure is observed.
- A production deployment would need sandboxed code execution and credential brokering before touching private systems.
- A hosted trace URL is not included because this repo is intentionally offline. The local trace file is the evidence artifact.

## Acceptance Checks

- Run `make demo` to produce this report.
- Run `make resume-proof` to stop a run mid-flight and resume it.
- Run `make eval` to gate the harness on quality, trajectory, and final state.
- Inspect `.runs/agent.db` and `traces/*.jsonl` to verify the claims.

## Sources Used

{chr(10).join(source_lines)}
"""
        return {"content": report, "citations": citation_map}

    def _self_check(self, context: dict[str, Any]) -> dict[str, Any]:
        report = context["draft_report"]["content"]
        result = self.judge.grade(report)
        return {"score": result.score, "criteria": result.criteria, "passed": result.passed}

    def _write_report(self, context: dict[str, Any]) -> dict[str, Any]:
        check = context["self_check"]
        if not check["passed"]:
            raise ValueError(f"self-check failed: {check}")
        return self._tool(5, context["run_id"], "write_report", run_id=context["run_id"], content=context["draft_report"]["content"])
