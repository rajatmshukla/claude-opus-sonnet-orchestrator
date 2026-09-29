# Complex Repository Work

Choose this preset for architecture changes, difficult debugging, and work
where higher-confidence reasoning matters more than latency.

This is an optional root override for the [Pro profile](full-orchestration.md),
whose default is Opus `medium`. It leaves the installed Sonnet `max` roles
and Opus `low` reviewer in place. If you adopt this override, update the
installed skill's root-effort wording to match.

Add or merge this into:

`~/.claude/settings.json`

```json
{
  "model": "opus",
  "effortLevel": "high",
  "fastMode": false
}
```

If your Claude Code version does not support `fastMode`, remove that line and
keep the model and effort settings.
