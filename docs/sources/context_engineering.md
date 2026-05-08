# Context Engineering

- Context engineering decides which tokens are available at each step of the loop.
- Write means storing durable scratchpads, notes, and state outside the live context window.
- Select means retrieving only the relevant context at the point of use.
- Compress means summarizing or compacting older context before it crowds out the current task.
- Isolate means giving sub-agents or subtasks their own context window and returning only compressed results to the parent.
- Filesystem memory is a good default until a measured recall problem justifies a vector store.
- Context offload is especially important for large tool outputs. The parent should receive a path and a preview, not a wall of raw tokens.

