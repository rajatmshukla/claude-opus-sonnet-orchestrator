# Pro Profile: Opus + Sonnet Orchestration

Choose this preset when you want Opus to plan, orchestrate, and review while
Sonnet handles the execution roles. Select Pro in `setup.sh` or `setup.ps1`.
Setup copies `profiles/pro/claude/` to `.claude/` in the target repository
without rewriting configuration. For manual installation, copy that folder
and the repository's `CLAUDE.md` to the target.

The topology is:

```text
Opus root (medium)
├── Sonnet explorer (max)
├── Sonnet worker (max)
├── Sonnet tester (max)
├── Sonnet researcher (max)
└── Opus reviewer (low)
```

Put the root settings in the project-scoped `.claude/settings.json`, or merge
them into `~/.claude/settings.json` for a personal/global setup:

```json
{
  "model": "opus",
  "effortLevel": "medium",
  "permissions": { "defaultMode": "default" },
  "sandbox": { "enabled": true },
  "env": {
    "CLAUDE_CODE_SUBAGENT_MODEL": "sonnet",
    "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "4"
  }
}
```

| Codex setting | Claude Code equivalent |
|---|---|
| `model`, `model_reasoning_effort` | `model`, `effortLevel` |
| `approval_policy = "on-request"` | `permissions.defaultMode = "default"` |
| `sandbox_mode = "workspace-write"` | `sandbox.enabled = true` (Bash writes limited to the project and temp dir) |
| `agents.max_concurrent_threads_per_session` | `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` |
| `agents.default_subagent_model` | `CLAUDE_CODE_SUBAGENT_MODEL` |
| `agents.default_subagent_reasoning_effort` | no equivalent; unnamed subagents inherit the session effort, so the named roles pin theirs |
| role `sandbox_mode = "read-only"` | `permissionMode: plan` + `disallowedTools: Edit, Write, NotebookEdit` |

In a project settings file, `effortLevel` applies to every model and is the
session level. Subagent `effort` frontmatter overrides it. Do **not** use the
`CLAUDE_CODE_EFFORT_LEVEL` environment variable for the root: it also
overrides every subagent's `effort`.

For the named roles, use these settings in the frontmatter of the
corresponding files under `.claude/agents/`:

```yaml
# explorer.md, worker.md, tester.md, researcher.md
model: sonnet
effort: max
```

```yaml
# reviewer.md
model: opus
effort: low
```

The role files override the inherited defaults. Keep those explicit
overrides when you want the topology above to remain stable. Remove them when
you want all named roles to follow the session defaults.

For the Sonnet-root configuration, use the [Plus profile](plus-plan.md).
