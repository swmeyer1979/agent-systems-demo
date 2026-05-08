# Harness Postmortem

Date: 2026-05-08

## Design Decision

This repo implements the smallest useful harness proof: deterministic planner, explicit tools, SQLite durability, JSONL traces, and eval gates.

I did not start with LangGraph, Claude Agent SDK, or a hosted observability product. That would make the first proof depend on somebody else's scaffolding. The goal here is to show the primitive mechanics plainly.

## What The Harness Gets Right

- The run loop is explicit. Each step has a name, input, output, status, and trace event.
- The tool registry is explicit. Search, read, and write are narrow tools, not hidden Python helpers.
- Durable checkpointed resume is real. The process can stop after completed steps and continue from SQLite.
- The trajectory is inspectable. Reviewers can inspect `steps`, `tool_calls`, and `traces/*.jsonl`.
- Evals are blocking. The eval command exits non-zero if required concepts, trajectory, judge score, or end state fail.
- The offline default is honest. No API key is required to verify the harness.

## What It Cuts

- No real LLM adapter by default.
- No hosted trace URL.
- No vector database.
- No parallel sub-agent fan-out.
- No sandboxed code execution.
- No credential broker.
- No benchmark-grade external eval suite.

These omissions are not philosophical. They are sequencing. The durable loop comes before the shiny integrations.

## Comparison To Claude Agent SDK

Claude Agent SDK gives you a mature harness: tool use, skills, hooks, sub-agents, permissions, session behavior, and a battle-tested developer workflow.

This repo is not trying to beat that. It isolates the ideas a reviewer should care about:

- what a step is
- where state is persisted
- what the tool boundary looks like
- how a trace records behavior
- how eval gates fail a bad change

Claude Agent SDK is the product-grade harness. This repo is the x-ray.

## Comparison To Deep Agents / LangGraph

LangGraph gives you a real state graph, checkpointers, middleware, interrupts, and production ecosystem support.

This repo uses a linear graph because the proof target is narrower: show durable agent execution with inspectable state. The next serious upgrade would be to move the step list into a LangGraph state graph and use PostgresSaver for persistence.

The useful invariant should survive that migration:

```text
checkpoint after every node, trace every tool call, gate every behavioral promise
```

## Failure Modes Found

- A report can be fluent and still ungrounded. The judge gate forces citations and source discipline.
- A demo can pass while the trajectory is wrong. The trajectory eval checks step names and tools directly.
- A resume story can be fake. `make resume-proof` intentionally stops and resumes the same run id.
- A local proof can overclaim production readiness. The README separates what is proven from what is not.

## Next Upgrade

The highest-value next slice is a real model adapter behind the existing planner and judge boundary:

1. Add an Anthropic or OpenAI adapter with structured outputs.
2. Keep the same SQLite checkpoints.
3. Keep the same JSONL trace contract.
4. Add tool-schema trajectory tests for bad tool choice.
5. Export traces to OpenTelemetry or LangSmith.

No rewrite should be required. If a real model adapter forces a rewrite of the state and eval layers, the harness abstraction was wrong.
