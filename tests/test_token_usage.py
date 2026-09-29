import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "token_usage.py"
SESSION = "11111111-2222-3333-4444-555555555555"


def assistant(msg_id, model, ts, content=None, usage=None, **extra):
    return {
        "type": "assistant",
        "sessionId": SESSION,
        "timestamp": ts,
        "cwd": "/example",
        "version": "2.1.300",
        "message": {
            "id": msg_id,
            "model": model,
            "content": content or [{"type": "text", "text": "ok"}],
            "usage": usage or {"input_tokens": 10, "cache_creation_input_tokens": 20,
                               "cache_read_input_tokens": 60, "output_tokens": 10},
        },
        **extra,
    }


def spawn_result(tool_use_id, agent_id, ts):
    return {
        "type": "user",
        "sessionId": SESSION,
        "timestamp": ts,
        "message": {"content": [{"type": "tool_result", "tool_use_id": tool_use_id,
                                 "content": [{"type": "text", "text": f"done\nagentId: {agent_id}"}]}]},
    }


def write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")


class TokenUsageCliTests(unittest.TestCase):
    def run_cli(self, *args):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "-example"
            spawns = [
                {"type": "tool_use", "id": "tu1", "name": "Agent", "input": {"subagent_type": "explorer"}},
                {"type": "tool_use", "id": "tu2", "name": "Agent", "input": {"subagent_type": "reviewer"}},
            ]
            write_jsonl(project / f"{SESSION}.jsonl", [
                {"type": "user", "sessionId": SESSION, "timestamp": "2026-09-09T12:00:00Z", "cwd": "/example"},
                # One response split across two lines (text + tool use) must count once.
                assistant("m1", "claude-opus-5-5", "2026-09-09T12:00:01Z"),
                assistant("m1", "claude-opus-5-5", "2026-09-09T12:00:01Z", content=spawns),
                spawn_result("tu1", "aexp1", "2026-09-09T12:01:00Z"),
                spawn_result("tu2", "arev1", "2026-09-09T12:02:00Z"),
                assistant("m2", "claude-opus-5-5", "2026-09-09T12:03:00Z"),
            ])
            sub = project / SESSION / "subagents"
            write_jsonl(sub / "agent-aexp1.jsonl", [
                assistant("s1", "claude-sonnet-5-5", "2026-09-09T12:00:05Z", isSidechain=True, agentId="aexp1"),
                assistant("s2", "claude-sonnet-5-5", "2026-09-09T12:00:30Z", isSidechain=True, agentId="aexp1"),
            ])
            write_jsonl(sub / "agent-arev1.jsonl", [
                assistant("r1", "claude-opus-5-5", "2026-09-09T12:01:05Z", isSidechain=True, agentId="arev1"),
            ])
            # A synthetic (non-API) message must be ignored.
            write_jsonl(sub / "agent-aoth1.jsonl", [
                assistant("x1", "<synthetic>", "2026-09-09T12:01:10Z", isSidechain=True, agentId="aoth1"),
            ])
            (sub / "agent-aoth1.meta.json").write_text(json.dumps({"agentType": "worker"}))
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--projects-dir", directory, *args],
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_list_counts_subagents(self):
        self.assertRegex(self.run_cli("--list"), r"11111111\s+3\s+/example")

    def test_latest_renders_roles_and_dedupes(self):
        output = self.run_cli("--latest")
        self.assertIn("threads: 4 (3 subagents)", output)
        self.assertIn("| `11111111` | root | claude-opus-5-5 | 2 |", output)
        self.assertIn("| `aexp1` | explorer | claude-sonnet-5-5 | 2 |", output)
        self.assertIn("| `arev1` | reviewer | claude-opus-5-5 | 1 |", output)
        self.assertIn("| **all** | 4 | 5 | 50 | 100 | 300 | 50 | 500 |", output)
        self.assertIn("Cache hit rate on input: 66.7%", output)

    def test_root_json_preserves_roles_and_usage(self):
        report = json.loads(self.run_cli("--root", "1111", "--format", "json"))
        roles = {t["id"]: t["role"] for t in report["threads"]}
        self.assertEqual(roles, {SESSION: "root", "aexp1": "explorer", "arev1": "reviewer", "aoth1": "worker"})
        total = sum(u["total_tokens"] for t in report["threads"] for u in t["per_model"].values())
        self.assertEqual(total, 500)

    def test_date_filter(self):
        self.assertIn("11111111", self.run_cli("--list", "--date", "2026-09-09"))


if __name__ == "__main__":
    unittest.main()
