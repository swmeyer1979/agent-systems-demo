# Cost, Latency, and Observability

- Cost is a product constraint. Each run needs a budget, and the harness should know when to use cheaper or stronger models.
- Prompt caching helps when system prompts, tool definitions, and project rules repeat across calls.
- Latency improves when independent source reads, searches, or sub-agent tasks run in parallel.
- Multi-agent fan-out can multiply token spend, so it should be justified by task value and decomposition quality.
- Trace sampling should capture model calls, tool calls, token counts, status, latency, and error details.
- Re-baseline evals after model upgrades because harness assumptions go stale as model behavior changes.
- Alert on tool failure rate, cost per request, eval regression, p95 latency, and judge-score drift.

