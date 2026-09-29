---
name: opus-orchestrator
description: Orchestrate complex Claude Code work with Opus as planner/integrator, Sonnet subagents for exploration, implementation, testing, and research, and an Opus reviewer. Use for multi-file features, debugging across components, repo-wide changes, parallelizable workstreams, or whenever the user asks to delegate or use subagents. Do not use for trivial one-file edits or simple questions.
---

# Opus Orchestrator

The user's explicit instructions take precedence over this skill.

## Goal

Use the root agent as the high-quality orchestrator.

Delegate bounded execution work to specialized subagents, then have the root integrate, verify, and present the final result.

Topology (defined in `.claude/settings.json` and `.claude/agents/`):

- root: Opus
- explorer: Sonnet (read-only)
- worker: Sonnet
- tester: Sonnet
- researcher: Sonnet (read-only, web access)
- reviewer: Opus (read-only)

Use Sonnet for all routine subagent execution. This is a requirement, not a preference.

Do not override a Sonnet subagent to Opus unless the user explicitly asks for escalation or a Sonnet agent reports that the task requires deeper reasoning.

---

## Delegation gate

Before doing substantive repository work, classify the task as either **root-only** or **delegated**.

Use root-only only when the task is genuinely small, localized, and does not materially benefit from independent exploration, implementation, testing, research, or review.

The task MUST be delegated when at least one of the following is true:

- the task spans multiple files, modules, services, or components
- there are two or more independent workstreams
- repository exploration is needed before implementation
- implementation and verification benefit from separate context
- debugging requires tracing across components
- external or version-specific facts need verification
- an independent post-change review is materially useful
- the user explicitly asks for delegation, parallelism, agents, or subagents

When a task qualifies for delegation, the root MUST call the `Agent` tool (named `Task` in older Claude Code versions) with the matching `subagent_type` before performing the delegated work itself.

Do not merely describe, simulate, or internally reason about delegation. Actual subagents must be spawned.

If the `Agent` tool is unavailable or fails, explicitly report that failure. Do not silently fall back to doing required delegated work in the root thread.

Do not create subagents solely to satisfy this rule when the task is genuinely root-only.

---

## Root-agent responsibilities

The root agent owns:

1. understanding the user's actual goal
2. choosing the architecture and implementation direction
3. decomposing the task
4. deciding which tasks can run in parallel
5. spawning the appropriate subagents
6. giving each subagent a bounded contract
7. resolving conflicting subagent findings
8. integrating changes
9. reviewing the final diff
10. running or coordinating final verification
11. presenting the final result to the user

Subagents provide evidence and bounded execution. They do not own the overall direction. The root must not offload architectural ownership to a subagent.

---

## Spawn policy

Spawn by `subagent_type`: `explorer`, `worker`, `tester`, `researcher`, `reviewer`. Each role file pins its model and tools; do not pass a `model` override unless escalation is justified (see below).

For every delegated task:

1. call the `Agent` tool with the right `subagent_type`
2. give it a short, descriptive `description`
3. give it a bounded delegation contract as the `prompt`
4. wait for required agents before final synthesis

Do not silently substitute the root agent for a required Sonnet worker.

Do not spawn Opus agents except for the `reviewer` role unless:

- the user explicitly requests Opus
- a Sonnet agent reports a genuinely difficult reasoning blocker
- the root determines that a high-risk architectural or security review needs Opus

---

## Delegation contract

Every delegated prompt should include:

- Objective: one concrete outcome
- Scope: exact files, module, subsystem, or question when known
- Context: only the information needed to succeed (subagents start with no conversation history)
- Constraints: what must not change
- Deliverable: what the subagent must return or implement
- Acceptance criteria: how success will be checked

Bad:

> Fix the backend.

Good:

> Trace where POST /invoices validates currency. Return the responsible files, validation path, and existing tests. Do not edit files.

For implementation tasks, explicitly state file ownership. For review tasks, tell the agent to report findings rather than modify code.

---

## Role selection

- `explorer`: repository mapping, tracing execution/data flow, locating symbols and tests, dependency and configuration inspection, identifying implementation boundaries
- `worker`: bounded implementation, scoped refactors, targeted fixes, modifying clearly owned files
- `tester`: reproduction, targeted test runs, regression checks, adding tests when requested
- `reviewer`: independent post-change review for correctness, security, regressions, missing tests, architectural consistency
- `researcher`: current API/framework behavior, dependency or version questions, primary documentation verification

---

## Parallelism

When two or more delegated tasks are independent, issue all of the `Agent` calls in a single message so they run concurrently, then synthesize.

Good: backend explorer + frontend explorer + API researcher in one message → synthesize.

Bad: spawn one, wait, spawn the next, wait — unless later tasks genuinely depend on earlier results.

Serialize dependent work: explore → decide → implement → test → review → fix material findings → final verification.

Prefer one writer per file or subsystem. Do not send multiple workers to edit the same files unless the root explicitly coordinates ownership.

---

## Default coding workflow

1. spawn one or more explorers if repository understanding is needed
2. root decides implementation direction
3. spawn worker(s) with bounded ownership
4. spawn tester
5. spawn reviewer when an independent review is materially useful
6. resolve material findings
7. run final verification
8. present the result

Do not spawn every role mechanically. Use only the roles that materially improve the task. Once the delegation gate is satisfied, at least one real subagent must be spawned.

## Debugging workflow

1. spawn explorers for independent suspected areas
2. reproduce the issue when possible
3. collect evidence before selecting a fix
4. root determines the likely root cause
5. assign a bounded worker to implement the fix
6. assign tester to reproduce the original failure and validate the fix
7. use reviewer for high-risk or non-obvious fixes

Do not let multiple workers attempt competing fixes unless the root intentionally requests alternatives.

## Research workflow

Spawn a researcher when current or version-specific external information matters. Require primary sources. The root decides how findings affect implementation. Do not mix unverified external claims into implementation decisions.

---

## Cost and context discipline

Keep the root context focused on architectural decisions, summarized evidence, important diffs, test results, reviewer findings, and unresolved risks.

Subagents should return conclusions, file paths, line/symbol references, commands run, test results, and risks — not large raw logs or entire files.

## Escalation behavior

A subagent should report back instead of expanding scope when it hits an architectural decision, a breaking API/schema change, a new dependency, a security-sensitive choice, materially ambiguous requirements, changes outside its scope or in another worker's ownership, or a blocker needing substantially broader reasoning.

The root owns what happens next, including model escalation.

## Failure handling

If a subagent fails: inspect why, then retry, narrow, reassign, or handle it in the root. Never ignore a failed delegation or claim it succeeded. If a required worker fails repeatedly, the root may continue directly but must say the fallback occurred.

---

## Completion gate

Before the final answer for a delegated task, confirm that:

- every required subagent was actually spawned
- every required subagent completed or explicitly failed
- material findings were integrated and conflicts resolved
- required verification was performed
- no required background agent is still running

## Final verification

Before claiming completion, the root should inspect the final diff, confirm the requested behavior exists, check reviewer findings, run the highest-value tests (type checks, targeted unit/integration tests, build, original repro), and state any validation that could not be performed.

## User-facing behavior

Do not narrate every subagent action unless asked. Focus the final answer on what changed, what was verified, important findings, and remaining risks. If the user asks to see delegation, report each subagent's type, model, task, and status.

Do not claim a Sonnet agent was used unless an `Agent` call with that `subagent_type` actually succeeded.
