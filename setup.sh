#!/bin/sh
# Install the Opus/Sonnet orchestrator into a target repository.
# Usage: ./setup.sh [target-repo]
set -eu

src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)/template

target=${1:-}
if [ -z "$target" ]; then
    printf 'Target repository path: '
    IFS= read -r target
fi
[ -d "$target" ] || { echo "Error: not a directory: ${target:-<empty>}" >&2; exit 1; }
target=$(CDPATH= cd -- "$target" && pwd -P)
[ "$target" != "$(dirname "$src")" ] || { echo "Error: target must differ from this repo." >&2; exit 1; }

# Agents and skill: -i asks before overwriting any existing file.
mkdir -p "$target/.claude"
cp -Ri "$src/.claude/agents" "$src/.claude/skills" "$target/.claude/"

# settings.json: never clobber existing settings.
if [ -e "$target/.claude/settings.json" ]; then
    echo 'Kept existing .claude/settings.json; add "model": "opus" to it to make Opus the root.'
else
    cp "$src/.claude/settings.json" "$target/.claude/settings.json"
fi

# CLAUDE.md: append policy once, preserving existing content.
if [ ! -e "$target/CLAUDE.md" ]; then
    cp "$src/CLAUDE.md" "$target/CLAUDE.md"
elif ! grep -q 'opus-orchestrator' "$target/CLAUDE.md"; then
    printf '\n\n' >> "$target/CLAUDE.md"
    cat "$src/CLAUDE.md" >> "$target/CLAUDE.md"
fi

echo "Installed into $target"
