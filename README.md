# Agent Systems Proof

Offline proof repo for durable agent loops, tool traces, eval gates, and checkpointed stop/resume behavior.

Public repo: https://github.com/swmeyer1979/agent-systems-proof

This is intentionally small. The point is not to call an LLM API and hope the demo looks clever. The point is to expose the harness mechanics that make agent systems production-ready.

## What This Proves

- **Tool use:** the agent searches local source files, reads selected documents, and writes a report through an explicit tool registry.
- **Durability:** every step is checkpointed in SQLite. A stopped run resumes from the next incomplete step.
- **Traceability:** every step and tool call emits JSONL trace records with status and latency.
- **Evals:** `make eval` runs single-turn, trajectory, judge-style, and end-state gates.
- **Guardrails:** write access is narrow, source reads are local, and report generation fails if the rubric does not pass.
- **Cost discipline:** the default demo has zero model spend and a clear adapter boundary for a real model.

## What This Does Not Prove

- It does not prove foundation-model research ability.
- It does not claim hosted LangSmith or Braintrust integration.
- It does not benchmark against GAIA, SWE-bench, or tau-bench.
- It does not pretend a deterministic offline planner is a frontier model.

That restraint is deliberate. Fake trophies are cheap. Inspectable state is better.

## Quickstart

Requires Python 3.11+.

```bash
make clean
make demo
make resume-proof
make eval
make test
```

Inspect the evidence:

```bash
make inspect-db
ls traces workspace/reports eval_results
sed -n '1,12p' traces/demo.jsonl
sed -n '1,80p' workspace/reports/demo.md
```

## Commands

`make demo`

Runs the agent end to end for the default question:

```text
What makes agent systems production-ready?
```

Outputs:

- `workspace/reports/demo.md`
- `traces/demo.jsonl`
- `.runs/agent.db`

`make resume-proof`

Runs the same agent with `--stop-after-step 3`, performs a checkpointed simulated stop, then resumes the same `run_id`.

This proves the resume path:

1. create run
2. finish plan/search/read checkpoints
3. simulate a checkpointed process stop
4. reload from SQLite
5. continue draft/self-check/write

`make eval`

Runs four gates:

- **single-turn:** required concepts appear in the final report.
- **trajectory:** expected steps and tools were used.
- **judge-style:** rubric scores citation quality, coverage, specificity, actionability, and source discipline.
- **end-state:** the report exists, the run is complete, and citations are present.

Outputs:

- `eval_results/summary.json`
- `traces/eval-*.jsonl`
- `workspace/reports/eval-*.md`

## Architecture

```text
agent_systems_proof/
  cli.py          command entry points
  agent.py        step loop, resume logic, self-check, report generation
  storage.py      SQLite run, step, and tool-call state
  tools.py        local source search/read/write tools
  tracing.py      JSONL trace emitter
  evaluator.py    eval gates
  judge.py        offline rubric-style judge
```

Run shape:

```text
plan -> search -> read_sources -> draft_report -> self_check -> write_report
```

State shape:

```text
runs(run_id, question, status, current_step, total_steps, output_path)
steps(run_id, step_index, name, status, input_json, output_json, error)
tool_calls(run_id, step_index, tool_name, args_json, output_json, status, latency_ms)
```

Trace shape:

```json
{"event":"step.start","run_id":"demo","step_index":1,"step_name":"search"}
{"event":"tool.call","run_id":"demo","tool_name":"search_sources","status":"ok","latency_ms":1.2}
{"event":"step.finish","run_id":"demo","step_index":1,"step_name":"search","status":"ok"}
```

## Why Offline

A public proof repo should run for a reviewer without secrets, credits, cloud setup, or vendor ceremony.

The model boundary is intentionally boring. Swap `ResearchAgent._plan`, `_draft_report`, or the judge with a real Anthropic/OpenAI/LangGraph adapter when the task calls for it. The durable loop, state, trace, and eval gates stay the same.

## Extension Points

- Replace the deterministic planner with an LLM adapter.
- Add parallel source reads with bounded fan-out.
- Export traces to OpenTelemetry, LangSmith, Phoenix, or Braintrust.
- Replace the heuristic judge with a calibrated model judge.
- Add a sandboxed code-execution tool.
- Add credential brokering for SaaS tools without putting secrets in model context.

## Acceptance Bar

This repo is useful only if these pass:

```bash
make clean
make demo
make resume-proof
make eval
make test
```
