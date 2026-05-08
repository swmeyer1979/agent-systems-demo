# Agent Systems Proof - Build Spec

Date: 2026-05-08

## Objective

Build a small offline harness for checkpointed agent runs:
tool use, stateful execution, durable resume, trace output, and eval coverage.

This is not a chatbot and not a framework tour. It is a compact harness that can be cloned, run, inspected, and extended.

## Files

- `README.md` - technical explanation and commands.
- `Makefile` - stable entry points: `make demo`, `make resume-proof`, `make eval`, `make test`, `make clean`.
- `pyproject.toml` - package metadata and Python version.
- `agent_systems_proof/` - CLI, harness, agent, tools, storage, tracing, eval logic.
- `docs/sources/` - local source corpus for the research agent.
- `docs/postmortem.md` - harness trade-off writeup.
- `evals/questions.jsonl` - golden eval fixture.
- `tests/` - focused regression tests.

Generated runtime artifacts:

- `.runs/agent.db` - SQLite durable state.
- `workspace/reports/` - generated Markdown reports.
- `traces/*.jsonl` - step/tool/eval traces.
- `eval_results/summary.json` - eval summary.

## Inputs

- Research question string.
- Local Markdown source corpus in `docs/sources/`.
- Optional `--run-id` and `--resume` arguments.
- Optional `--stop-after-step` argument to simulate a checkpointed process stop.

## Outputs

- Markdown research report with inline source citations.
- SQLite state that can resume after a checkpointed forced stop.
- JSONL trace containing step, tool, latency, `estimated_cost_usd`, and status events.
- Eval summary covering single-turn, trajectory, judge-style report quality, and end-state checks.

## Acceptance Criteria

- `make demo` runs end to end with no network and no API keys.
- `make resume-proof` intentionally stops mid-run, then resumes the same run id and produces the final report.
- `make eval` runs all eval types and exits non-zero if any gate fails.
- `make test` passes.
- README explains what the harness proves and what it deliberately does not prove.
- Durable state is explicit and inspectable in SQLite.
- Trace output is explicit and inspectable as JSONL.

## Risks

- A deterministic offline model can look less impressive than a real LLM demo. Mitigation: frame it as harness proof, with a clean adapter boundary for real models.
- Overbuilding would dilute the signal. Mitigation: keep the code small and commands boring.
- Public claims can overreach. Mitigation: state that this demonstrates agent-systems engineering patterns, not frontier model research.

## Verification

Run:

```bash
make clean
make demo
make resume-proof
make eval
make test
```

Then inspect:

```bash
sqlite3 .runs/agent.db '.tables'
ls traces workspace/reports eval_results
```

## Review Remediation Addendum

Subagent review found two proof-breaking path traversal bugs and two overclaim/coverage gaps. Before release:

- `run_id` and eval IDs must be constrained to a portable slug format before they touch trace, report, or database paths.
- `source_id` must be constrained to local source slugs and resolved inside `docs/sources`.
- Trajectory evals must check ordered tool calls and expected arguments, not just the presence of tool names.
- The repo must describe the resume demo as checkpointed stop/resume unless a subprocess kill test is implemented.
- Trace records must either include explicit cost estimates or the spec must stop promising them. For this offline harness, add explicit `estimated_cost_usd: 0.0`.

## Positioning Addendum

The public surface should read like a small technical harness, not a resume artifact.

Acceptance criteria:

- Avoid role-fit and self-marketing framing in the repo.
- Prefer concrete nouns: SQLite state, JSONL traces, local tools, eval gates.
- Keep claims bounded to checkpointed stop/resume, not crash recovery.
- Keep site copy short and descriptive rather than promotional.

## README Graphic Addendum

Objective: add one restrained technical graphic near the top of `README.md`.

Files:

- `README.md`
- `docs/assets/agent-systems-proof-graphic.png`

Acceptance criteria:

- The image is stored in the repo instead of hotlinking a local generated-image path.
- The README references the asset with a relative path so GitHub renders it.
- The graphic appears after the short project description and before the detailed explanation.

## README Usage Addendum

Objective: explain how the harness would be used and when it is helpful.

Files:

- `README.md`

Acceptance criteria:

- The section describes adaptation steps, not a product pitch.
- Scenarios are concrete: regulated workflows, long-running agents, eval development, debugging, and teaching.
- The section states the production boundary plainly: this is a reference harness, not full orchestration infrastructure.
