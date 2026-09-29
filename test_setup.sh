#!/bin/sh
# Smoke test: fresh install, then re-install preserves existing settings and CLAUDE.md.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT

"$here/setup.sh" "$t" >/dev/null
for f in explorer researcher reviewer tester worker; do
    grep -q "^name: $f$" "$t/.claude/agents/$f.md"
done
test -f "$t/.claude/skills/opus-orchestrator/SKILL.md"
grep -q '"model": "opus"' "$t/.claude/settings.json"

echo '{"x":1}' > "$t/.claude/settings.json"
echo '# mine' > "$t/CLAUDE.md"
yes | "$here/setup.sh" "$t" >/dev/null 2>&1
grep -q '"x":1' "$t/.claude/settings.json"
head -1 "$t/CLAUDE.md" | grep -q '# mine'
test "$(grep -c 'opus-orchestrator' "$t/CLAUDE.md")" -eq 1
yes | "$here/setup.sh" "$t" >/dev/null 2>&1
test "$(grep -c 'opus-orchestrator' "$t/CLAUDE.md")" -eq 1

echo PASS
