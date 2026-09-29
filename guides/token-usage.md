# Token Usage

There is no single token number for this setup. Usage depends on repository
size, task shape, how many subagents the root actually spawns, and how much
of each subagent's context is served from cache. What this guide gives you
instead is a repeatable way to measure your own runs and the caveats needed
to read the numbers correctly.

## What Claude Code records

Claude Code writes one transcript per session and one per subagent:

- `~/.claude/projects/<project>/<sessionId>.jsonl`: the root thread.
- `~/.claude/projects/<project>/<sessionId>/subagents/agent-<agentId>.jsonl`:
  each subagent, with `isSidechain: true` and its `agentId` on every entry.

The relevant fields are:

- `assistant` entries: `message.model`, `message.id`, and `message.usage`
  with `input_tokens` (uncached), `cache_creation_input_tokens`,
  `cache_read_input_tokens`, and `output_tokens`. Claude Code writes one line
  per content block, each repeating the response's usage, so count one record
  per `message.id`.
- The root's `Agent` tool calls: `input.subagent_type` names the role, and the
  matching tool result carries the spawned `agentId`.
- `cwd`, `version`, and `timestamp` on every entry.

Extended-thinking tokens are billed as output and are not reported
separately. Effort level and plan rate-limit usage are not recorded in
transcripts; use `/usage` in Claude Code for plan limits.

Grouping a session's files therefore gives the full cost of one orchestrated
task, split by thread, role, and model, with no instrumentation. Claude Code
deletes transcripts after `cleanupPeriodDays` (30 by default), so measure
soon after a run.

## Measuring a run

`scripts/token_usage.py` does the grouping. It is standard-library Python and
read-only.

```bash
# Which sessions spawned subagents today?
scripts/token_usage.py --list --date 2026-09-07

# Report on one session (any unique id prefix works)
scripts/token_usage.py --root 01a079f2 --date 2026-09-07

# Report on the most recent session that used subagents
scripts/token_usage.py --latest --date 2026-09-07

# Machine-readable output
scripts/token_usage.py --root 01a079f2 --format json
```

Omitting `--date` scans every project, which is slower.

If you have a plain root-only session to compare against, run the same
command with its id. The script works for sessions with zero subagents.

## Benchmark protocol

If you want numbers that are comparable across configurations:

1. Pick three or four representative tasks in one repository: a single-file
   fix, a multi-file feature, a cross-component bug, and a research-heavy
   change. Write the prompts down and reuse them verbatim.
2. Run each task in at least two configurations:
   - Baseline: Opus root only, no `.claude/agents/`, no skill.
   - Orchestrated: the selected Pro or Plus profile as installed.
   - Optional floor: Sonnet root only, to see the cheapest possible run.
3. Record for every run: per-model uncached input, cache writes, cache reads,
   and output tokens; number of subagents spawned; wall time; and the change
   in plan usage shown by `/usage`.
4. Repeat each cell two or three times. Variance between runs of the same
   prompt is large enough that a single sample misleads.
5. Record the profile and any overrides: Pro uses Opus `medium` with Sonnet
   `max`; Plus uses Sonnet `max` (or `xhigh` without `--effort max`) with
   Sonnet `medium`. Both use an Opus `low` reviewer. Note the Claude Code
   version. Caching behaviour and subagent context handling change between
   releases.

Suggested results table:

| Task | Config | Opus uncached / cache write / cache read / out | Sonnet uncached / cache write / cache read / out | Subagents | Wall | Usage delta |
|---|---|---|---|---:|---:|---:|

## Reading the numbers

Cached input dominates. A raw total therefore overstates cost by more than an
order of magnitude. Always look at uncached input, cache writes, and output
separately: cache reads are billed at a fraction of the input price, cache
writes at a premium.

Plan usage is what Pro and Max subscribers actually pay with. The mapping
from tokens to plan usage is not published and differs by model, so the
`/usage` delta is the most honest single number for "how much of my plan did
this task cost". The window is account-wide, so other sessions running at the
same time inflate the delta.

The root thread is usually the largest line item even at `low` effort. It
stays alive for the whole task, waits on subagents, and re-reads its context
on every response. Parallelism trades tokens for latency: every spawned
subagent re-reads its own context on every response.

## Sample run

None yet for Claude Code. The upstream Codex repository's sample does not
transfer: different models, caching, and billing. See Contributing results.

## Reducing usage

In rough order of impact:

- On a tighter plan, move the root to Sonnet. The root is the largest line
  item in every orchestrated session, so this saves more than any subagent
  change. The installer does this when you select the Plus plan; for manual
  setups see `plus-plan.md`:

  ```json
  { "model": "sonnet", "effortLevel": "xhigh" }
  ```

- Do not orchestrate small tasks. The skill's delegation gate already says
  this; enforce it by not invoking `/opus-orchestrator` for one-file edits.
- Keep `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` low. Each extra concurrent
  subagent is a second full context being re-read on every response.
- Ask subagents for short reports. The skill's "cost and context discipline"
  section exists because raw logs pasted into the root are re-read by the
  root on every subsequent response.
- Skip the reviewer for low-risk changes. It is Opus, and it re-reads the
  diff and surrounding context.
- Lower Sonnet to `low` effort for explorer and tester roles; this mainly
  shortens wall time.

## Contributing results

If you run the protocol on your own projects, open a pull request adding a
sample run above with the task description, repository size, Claude Code
version, plan type, and the script output. Please redact repository paths
you do not want published.
