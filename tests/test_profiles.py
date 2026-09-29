import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROLES = ("explorer", "researcher", "reviewer", "tester", "worker")
SONNET_ROLES = ("explorer", "researcher", "tester", "worker")
READ_ONLY = ("explorer", "researcher", "reviewer")
# profile: (root model, root effort, sonnet effort, reviewer model, reviewer effort, concurrency)
PROFILES = {
    "pro": ("opus", "medium", "max", "opus", "low", 4),
    "plus": ("sonnet", "max", "medium", "opus", "low", 4),
    "pro-max-2-subagents": ("opus", "medium", "max", "opus", "low", 2),
    "plus-max-2-subagents": ("sonnet", "max", "medium", "opus", "low", 2),
    "Claude-FableMax-SonnetMax": ("fable", "max", "max", "fable", "max", 4),
    "Claude-FableMedium-SonnetMax": ("fable", "medium", "max", "fable", "medium", 4),
}


def frontmatter(path: Path) -> dict:
    text = path.read_text()
    assert text.startswith("---\n"), path
    head, body = text[4:].split("\n---\n", 1)
    fields = dict(line.split(": ", 1) for line in head.splitlines())
    fields["body"] = body
    return fields


def root_effort(settings: dict) -> str:
    return settings["env"].get("CLAUDE_CODE_EFFORT_LEVEL") or settings["effortLevel"]


class ProfileTests(unittest.TestCase):
    def test_profile_models_and_roles(self):
        bodies = {}
        for profile, (root, effort, sonnet_effort, rev_model, rev_effort, limit) in PROFILES.items():
            with self.subTest(profile=profile):
                directory = ROOT / "profiles" / profile / "claude"
                settings = json.loads((directory / "settings.json").read_text())
                self.assertEqual(settings["model"], root)
                # max cannot be persisted in settings; xhigh is the closest saved level.
                expected = effort
                if effort == "max" and "CLAUDE_CODE_EFFORT_LEVEL" not in settings["env"]:
                    expected = "xhigh"
                self.assertEqual(root_effort(settings), expected)
                self.assertEqual(settings["permissions"]["defaultMode"], "default")
                self.assertTrue(settings["sandbox"]["enabled"])
                self.assertEqual(settings["env"]["CLAUDE_CODE_SUBAGENT_MODEL"], "sonnet")
                self.assertEqual(settings["env"]["CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS"], str(limit))
                if "CLAUDE_CODE_EFFORT_LEVEL" in settings["env"]:
                    # The env var overrides subagent effort, so only allow it when every role matches.
                    efforts = {frontmatter(directory / "agents" / f"{r}.md")["effort"] for r in ROLES}
                    self.assertEqual(efforts, {settings["env"]["CLAUDE_CODE_EFFORT_LEVEL"]})

                for role in ROLES:
                    agent = frontmatter(directory / "agents" / f"{role}.md")
                    self.assertEqual(agent["name"], role)
                    if role in SONNET_ROLES:
                        self.assertEqual((agent["model"], agent["effort"]), ("sonnet", sonnet_effort))
                    else:
                        self.assertEqual((agent["model"], agent["effort"]), (rev_model, rev_effort))
                    if role in READ_ONLY:
                        self.assertEqual(agent["permissionMode"], "plan")
                        self.assertEqual(agent["disallowedTools"], "Edit, Write, NotebookEdit")
                    else:
                        self.assertNotIn("permissionMode", agent)
                        self.assertNotIn("disallowedTools", agent)
                    # Role instructions are identical across profiles.
                    self.assertEqual(bodies.setdefault(role, agent["body"]), agent["body"])

                skill = (directory / "skills" / "opus-orchestrator" / "SKILL.md").read_text()
                self.assertIn("name: opus-orchestrator", skill)
                self.assertIn(f"`sonnet` at `{sonnet_effort}` reasoning", skill)
                for stale in ("Codex", "codex", "gpt-", "GPT-", "Astra", "Luna", "spawn_agent"):
                    self.assertNotIn(stale, skill)

    def test_installers_select_profiles(self):
        installers = [("shell", ["sh", str(ROOT / "setup.sh")])]
        if shutil.which("pwsh"):
            installers.append(("powershell", ["pwsh", "-NoProfile", "-File", str(ROOT / "setup.ps1")]))
        choices = [(str(i), p) for i, p in enumerate(PROFILES, start=1)] + [
            ("", "pro"),
            ("Claude-FableMax-SonnetMax", "Claude-FableMax-SonnetMax"),
            ("claude-FableMedium-SonnetMax", "Claude-FableMedium-SonnetMax"),
        ]
        for installer, command in installers:
            for choice, profile in choices:
                with self.subTest(installer=installer, choice=choice), tempfile.TemporaryDirectory() as target:
                    result = subprocess.run(
                        command, input=f"{target}\n{choice}\n\n\n", text=True, capture_output=True
                    )
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("Select Profile [1-6] (default 1):", result.stdout)
                    self.assertIn(f"profile: {profile}", result.stdout)
                    self.assertIn("2 component(s) installed", result.stdout)
                    source = ROOT / "profiles" / profile / "claude"
                    for component in (
                        "settings.json",
                        "agents/reviewer.md",
                        "agents/worker.md",
                        "skills/opus-orchestrator/SKILL.md",
                    ):
                        self.assertEqual(
                            (Path(target) / ".claude" / component).read_text(),
                            (source / component).read_text(),
                        )
                    self.assertEqual(
                        (Path(target) / "CLAUDE.md").read_text(), (ROOT / "CLAUDE.md").read_text()
                    )

    def test_installers_preserve_existing_files(self):
        installers = [("shell", ["sh", str(ROOT / "setup.sh")])]
        if shutil.which("pwsh"):
            installers.append(("powershell", ["pwsh", "-NoProfile", "-File", str(ROOT / "setup.ps1")]))
        for installer, command in installers:
            with self.subTest(installer=installer), tempfile.TemporaryDirectory() as target:
                target_path = Path(target)
                (target_path / ".claude").mkdir()
                (target_path / ".claude" / "settings.json").write_text('{"mine": true}\n')
                (target_path / "CLAUDE.md").write_text("# Existing\n")
                # Decline the .claude update; CLAUDE.md is appended without a prompt.
                for _ in range(2):
                    result = subprocess.run(
                        command, input=f"{target}\n1\n\nn\n\n", text=True, capture_output=True
                    )
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual((target_path / ".claude" / "settings.json").read_text(), '{"mine": true}\n')
                claude_md = (target_path / "CLAUDE.md").read_text()
                self.assertTrue(claude_md.startswith("# Existing\n"))
                self.assertEqual(claude_md.count("opus-orchestrator"), 1)


if __name__ == "__main__":
    unittest.main()
