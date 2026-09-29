# Claude Opus/Fable Orchestrator + Sonnet Subagents

Install a Claude Code profile with Claude Opus, Fable, or Sonnet as the
orchestrator, Claude Sonnet execution subagents, and an independent reviewer.

A full port of
[donvito/codex-astra-luna-orchestrator](https://github.com/donvito/codex-astra-luna-orchestrator)
(Apache 2.0) to Claude Code's native subagents, skills, settings, and
`CLAUDE.md`. Model mapping: Astra → Opus, Luna → Sonnet, Sol → Fable. Role
instructions, skills, profiles, and effort levels are carried over unchanged.

## Orchestration topology

The diagram shows the Opus (Pro) and Fable orchestrators. Plus uses a Sonnet
root, as shown in the profile table below. Execution roles use Claude Sonnet;
the reviewer uses Opus for Pro/Plus and Fable for Fable profiles.

```text
             Claude Opus / Fable
             root / orchestrator
                      |
      +---------------+---------------+
      |               |               |
   explorer         worker        researcher
 Claude Sonnet   Claude Sonnet   Claude Sonnet
      |               |
      +-------+-------+
              |
           tester
        Claude Sonnet
              |
          reviewer
     Claude Opus / Fable
              |
              v
          root agent
      integrate + verify
```

## Setup

1. Clone this repository and enter it:

   ```sh
   git clone https://github.com/rajatmshukla/claude-opus-sonnet-orchestrator.git
   cd claude-opus-sonnet-orchestrator
   ```

2. Run the installer for your platform:

   macOS/Linux:

   ```sh
   ./setup.sh
   ```

   Windows PowerShell:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\setup.ps1
   ```

   PowerShell 7:

   ```powershell
   pwsh -File .\setup.ps1
   ```

3. When prompted, enter an **existing target repository other than this one**,
   choose a profile by number or name (Enter selects Pro), and confirm which
   components to install. For example:

   ```text
   Target repository path: ../my-project
   Select Profile [1-6] (default 1): 5
   ```

The installer copies the selected configuration, agents, and skill to
`.claude/`, and project instructions to `CLAUDE.md`. Existing component files
are updated only after confirmation; existing `CLAUDE.md` content is preserved.

### Installed target project

If you install both components into `../my-project`, the installer adds
these paths alongside the project's existing files:

```text
my-project/
├── .claude/
│   ├── settings.json
│   ├── agents/
│   │   ├── explorer.md
│   │   ├── researcher.md
│   │   ├── reviewer.md
│   │   ├── tester.md
│   │   └── worker.md
│   └── skills/
│       └── opus-orchestrator/
│           └── SKILL.md
└── CLAUDE.md
```

`profiles/<profile>/claude/` becomes `.claude/`. The root `CLAUDE.md` is
copied to the target, or its instructions are appended if that file exists.

## How to use the skill

From the target repository, launch Claude Code. For the example above:

```sh
cd ../my-project
claude
```

For complex work, Claude may select the skill automatically, or you can
invoke it explicitly:

```text
/opus-orchestrator
Implement the invoice export endpoint. Use the explorer to map the path,
a worker to implement it, and the tester and reviewer to verify it.
```

The skill keeps the `opus-orchestrator` name in every profile so the shared
`CLAUDE.md` works; the Fable and Plus profiles use their own root model
according to their configuration.

## Profiles

| Choice | Profile | Root | Execution roles | Reviewer | Concurrent subagents |
|---|---|---|---|---|---:|
| 1 (default) | `pro` | Opus medium | Sonnet max | Opus low | 4 |
| 2 | `plus` | Sonnet max* | Sonnet medium | Opus low | 4 |
| 3 | `pro-max-2-subagents` | Opus medium | Sonnet max | Opus low | 2 |
| 4 | `plus-max-2-subagents` | Sonnet max* | Sonnet medium | Opus low | 2 |
| 5 | `Claude-FableMax-SonnetMax` | Fable max | Sonnet max | Fable max | 4 |
| 6 | `Claude-FableMedium-SonnetMax` | Fable medium | Sonnet max | Fable medium | 4 |

\* Claude Code cannot save `max` effort in settings, so Plus profiles save
`xhigh`. Launch with `claude --effort max` for a literal `max` root; the
subagents keep their own effort. See [plus-plan.md](guides/plus-plan.md).

Execution roles are explorer, worker, tester, and researcher; named roles pin
their models and effort levels in frontmatter, independently of the session
defaults. Explorer, researcher, and reviewer are read-only (`permissionMode:
plan`, edit tools removed). Every profile starts the root in the default
permission mode (ask before edits and commands) with the Bash sandbox on.
Fable profiles require Fable access on your account. Each ready-to-copy
profile lives under `profiles/<profile>/`.

For manual project setup, copy the selected profile's `claude/` to the target
repository as `.claude/`, and add this repository's `CLAUDE.md`. For
personal/global setup, copy its `claude/agents/` into `~/.claude/agents/`,
its `claude/skills/opus-orchestrator/` into `~/.claude/skills/`, and
**merge**, rather than replace, its `claude/settings.json` into
`~/.claude/settings.json`. Do not overwrite other existing Claude Code
settings.

## Key directory structure

```text
.
├── profiles/
│   ├── pro/
│   ├── plus/
│   ├── pro-max-2-subagents/
│   ├── plus-max-2-subagents/
│   ├── Claude-FableMax-SonnetMax/
│   └── Claude-FableMedium-SonnetMax/
├── guides/
├── scripts/
│   └── token_usage.py
├── tests/
│   ├── test_profiles.py
│   └── test_token_usage.py
├── CLAUDE.md
├── setup.sh
├── setup.ps1
├── README.md
└── LICENSE
```

Each profile contains `claude/settings.json`, `claude/agents/*.md`, and
`claude/skills/opus-orchestrator/SKILL.md`.

## Guides

- [Pro orchestration and manual configuration](guides/full-orchestration.md) (includes the Codex → Claude Code settings map)
- [Plus profile and global setup](guides/plus-plan.md)
- [Fast iteration](guides/fast-iteration.md) and [routine coding](guides/routine-coding.md)
- [Complex repository work](guides/complex-repo-work.md)
- [Token usage and measurement](guides/token-usage.md)

## Tests

```sh
python3 -m unittest discover -s tests
```

The installer tests also run `setup.ps1` when `pwsh` is installed.

## License

Licensed under the [Apache License 2.0](LICENSE). Derived from
[donvito/codex-astra-luna-orchestrator](https://github.com/donvito/codex-astra-luna-orchestrator).
