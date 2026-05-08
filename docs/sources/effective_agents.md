# Effective Agent Loops

- An agent is useful when control flow cannot be fixed up front and the system must choose tools based on intermediate results.
- A workflow is better when the path is known: prompt chain, route, parallelize, orchestrate workers, or run evaluator-optimizer loops.
- The model call is only one part of the system. The harness owns the loop, tool dispatch, context assembly, error handling, and stopping rule.
- Tool descriptions and parameter schemas are part of the interface. Bad tools make the model look worse than it is.
- Parallel tool calls are valuable when subtasks are independent; serial reasoning is expensive when the work decomposes cleanly.
- A production agent should expose the trajectory, not just the final answer.

