# Durability, Sandboxing, and Guardrails

- Long-running agents need durable state. If a process stop loses the task, the harness is not production-ready.
- A practical checkpoint boundary is after each node or tool step, not after every token.
- Resume should be boring: load the run id, rehydrate completed outputs, continue from the next incomplete step.
- Code execution belongs in a sandbox. The model should not execute arbitrary code in the main process.
- Credentials should be brokered outside the model context. A model can ask for an action without seeing the secret that authorizes it.
- Human approval is required for irreversible or high-blast-radius actions.
- Pre-tool hooks can block destructive commands, validate write paths, and reject secret-looking payloads.

