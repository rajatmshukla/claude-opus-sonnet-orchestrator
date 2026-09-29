# Routine Coding

Choose this preset for predictable, routine coding tasks where lower cost and
faster orchestration are preferred.

This is an optional root override for the [Plus profile](plus-plan.md),
lowering its Sonnet root from `max` to `medium`. The installed Sonnet subagents
remain at `medium` and the Opus reviewer at `low`. If you adopt this override,
update the installed skill's root-effort wording to match.

Add or merge this into:

`~/.claude/settings.json`

```json
{
  "model": "sonnet",
  "effortLevel": "medium"
}
```

Fast mode is not part of this preset: it runs only on Opus, and turning it on
switches the session to Opus.
