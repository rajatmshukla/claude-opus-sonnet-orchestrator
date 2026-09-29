# Fast Iteration

Choose this preset when latency matters and you want Opus to orchestrate
quickly with Sonnet subagents.

Start with the [Pro profile](full-orchestration.md). This optional root
preset keeps Opus `medium`; the installed Sonnet roles remain at `max` and
the Opus reviewer at `low`. For a Sonnet root, use the [Plus profile](plus-plan.md).

Add or merge this into:

`~/.claude/settings.json`

```json
{
  "model": "opus",
  "effortLevel": "medium",
  "fastMode": true
}
```

Fast mode runs only on supported Opus models and costs more per token. If
your Claude Code version or plan does not offer it, remove `fastMode` and
keep the model and effort settings.
