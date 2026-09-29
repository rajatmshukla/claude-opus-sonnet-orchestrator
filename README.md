# Claude Opus Orchestrator + Sonnet Subagents

A Claude Code setup where **Opus** plans, integrates, and reviews, and
**Sonnet** subagents do the bounded execution work.

Ported from [donvito/codex-astra-luna-orchestrator](https://github.com/donvito/codex-astra-luna-orchestrator)
(Apache 2.0) to Claude Code's native subagents, skills, and `CLAUDE.md`.

## Topology

```text
                 Claude Opus
             root / orchestrator
                      |
      +---------------+---------------+
      |               |               |
   explorer         worker        researcher
    Sonnet          Sonnet          Sonnet
      |               |
      +-------+-------+
              |
           tester
           Sonnet
              |
          reviewer
            Opus
              |
              v
          root agent
      integrate + verify
```

| Role | Model | Tools |
|---|---|---|
| root | Opus (`.claude/settings.json`) | all |
| explorer | Sonnet | Read, Grep, Glob (read-only) |
| researcher | Sonnet | Read, Grep, Glob, WebFetch, WebSearch (read-only) |
| worker | Sonnet | all |
| tester | Sonnet | Read, Grep, Glob, Bash, Edit, Write |
| reviewer | Opus | Read, Grep, Glob, Bash (read-only by instruction) |

## Setup

```sh
git clone <this-repo> claude-opus-sonnet-orchestrator
cd claude-opus-sonnet-orchestrator
./setup.sh ../my-project
```

This installs into the target:

```text
my-project/
├── .claude/
│   ├── settings.json          # "model": "opus" (kept if it already exists)
│   ├── agents/
│   │   ├── explorer.md
│   │   ├── researcher.md
│   │   ├── reviewer.md
│   │   ├── tester.md
│   │   └── worker.md
│   └── skills/
│       └── opus-orchestrator/
│           └── SKILL.md
└── CLAUDE.md                  # policy appended if the file already exists
```

Existing agent/skill files prompt before overwrite. For a personal/global
setup, copy `template/.claude/agents` and `template/.claude/skills` into
`~/.claude/` and set `"model": "opus"` in `~/.claude/settings.json`.

## Usage

```sh
cd ../my-project
claude
```

Claude may pick the skill automatically for complex work, or invoke it:

```text
/opus-orchestrator Implement the invoice export endpoint. Use the explorer to
map the path, a worker to implement it, and the tester and reviewer to verify it.
```

To change a role's model, edit `model:` (`opus`, `sonnet`, `haiku`, or
`inherit`) in its `.claude/agents/<role>.md` frontmatter.

## Test

```sh
./test_setup.sh
```

## License

[Apache License 2.0](LICENSE).
