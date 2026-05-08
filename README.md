# Agent Systems Proof

Small offline harness for checkpointed agent runs, local tools, JSONL traces, and eval gates.

This is not a framework and not a chatbot. It keeps the moving parts visible: a step loop, a local source corpus, explicit tool calls, SQLite state, trace records, and deterministic gates.

## What It Contains

- **Tool registry:** source search, source read, and report write tools with narrow path rules.
- **Checkpointing:** every step is recorded in SQLite before the next step starts.
- **Resume:** a stopped run can continue from the next incomplete step.
- **Trace records:** every step and tool call emits JSONL with status, latency, and estimated cost.
- **Eval gates:** `make eval` runs concept, trajectory, report-quality, and end-state checks.
- **Offline defaults:** no API key, cloud account, or hosted tracing service required.

## Non-goals

- No foundation-model research.
- No benchmark claim against GAIA, SWE-bench, or tau-bench.
- No hosted observability dependency.
- No claim that the deterministic planner is a frontier model.

## Quickstart

Requires Python 3.11+.

```bash
make clean
make demo
make resume-proof
make eval
make test
```

Inspect the outputs:

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

Resume path:

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

The default path should run without secrets, credits, cloud setup, or vendor ceremony.

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
