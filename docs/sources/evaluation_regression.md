# Evals and Regression Gates

- Evals convert agent quality from taste into a repeatable engineering check.
- Single-turn evals check whether one answer is correct for one input.
- Trajectory evals check whether the agent called the right tools in the right order with the right arguments.
- Judge-style evals are useful for open-ended outputs when the rubric is explicit and periodically calibrated.
- End-state evals verify the final environment state: file written, database updated, task closed, or policy obeyed.
- CI gates matter because dashboards without blocking power become wallpaper.
- Golden datasets should grow from real failures, not only synthetic examples.

