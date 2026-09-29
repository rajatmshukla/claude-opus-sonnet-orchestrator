# Orchestration policy

For complex coding tasks, use the `opus-orchestrator` skill when its trigger conditions match.

The root agent (Opus) owns architecture, decomposition, integration, and final verification.
Prefer the Sonnet subagents (`explorer`, `worker`, `tester`, `researcher`) for bounded execution and the Opus `reviewer` for independent review.

Do not delegate trivial work merely for parallelism.
Do not let multiple implementation agents edit the same files without explicit ownership boundaries.
User instructions always take precedence over this orchestration policy.
