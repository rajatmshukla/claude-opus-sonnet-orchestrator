# Plus Plan

Choose this profile for a Sonnet root at `max` effort and Sonnet execution
subagents at `medium` effort, with an Opus reviewer at `low`.

The installers (`setup.sh`, `setup.ps1`) ask which profile to install and use this
configuration when you select `Plus`. Setup copies `profiles/plus/claude/` to
`.claude/` without rewriting configuration. For manual installation, copy that
folder and the repository's `CLAUDE.md` to the target.

For a global setup, merge `profiles/plus/claude/settings.json` into:

`~/.claude/settings.json`

```json
{
  "model": "sonnet",
  "effortLevel": "xhigh",
  "env": {
    "CLAUDE_CODE_SUBAGENT_MODEL": "sonnet",
    "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "4"
  }
}
```

Claude Code does not accept `max` in settings files, so the profile saves
`xhigh`, the highest level that persists. For a literal `max` root, launch
with:

```sh
claude --effort max
```

`--effort` sets the session level, so the subagents keep their own `medium`
and `low`. Avoid `CLAUDE_CODE_EFFORT_LEVEL=max` here: the environment variable
overrides subagent `effort` too and would run every role at `max`.

Subagents keep their pinned models from `.claude/agents/*.md`. Explorer,
worker, tester, and researcher explicitly set `model: sonnet` and
`effort: medium`. The reviewer stays on Claude Opus on the Plus plan too: it
is a single, read-only, `low`-effort thread, and it gives you an independent
review by a different model than the one that planned and wrote the change.
If you want the whole session on Sonnet, change `model` in
`.claude/agents/reviewer.md` as well.

See `token-usage.md` for how to measure the difference on your own tasks.

For global installation, also copy `profiles/plus/claude/agents/` to
`~/.claude/agents/` and `profiles/plus/claude/skills/opus-orchestrator/` to
`~/.claude/skills/opus-orchestrator/`. Use the skill from the same profile
as the configuration so its model and effort instructions match.
