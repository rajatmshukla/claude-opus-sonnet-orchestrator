#!/usr/bin/env python3
"""Aggregate Claude Code token usage for an orchestrated session.

Claude Code writes the main transcript to
~/.claude/projects/<project>/<sessionId>.jsonl and each subagent's transcript
to ~/.claude/projects/<project>/<sessionId>/subagents/agent-<agentId>.jsonl.
Grouping those files by session gives the full cost of one orchestrated task,
split by thread, role, and model.

Usage:
  scripts/token_usage.py --list [--date YYYY-MM-DD]
  scripts/token_usage.py --root <session-id-or-prefix> [--format md|json]
  scripts/token_usage.py --latest

Standard library only. Read-only: it never modifies the transcript files.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date as Date, datetime, timezone
from pathlib import Path

USAGE_KEYS = (
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "output_tokens",
)
SPAWN_TOOLS = {"Agent", "Task"}
AGENT_ID_TEXT = re.compile(r"agentId:\s*([\w-]+)")


def empty_usage() -> dict[str, int]:
    return {k: 0 for k in (*USAGE_KEYS, "total_tokens")}


def add_usage(target: dict[str, int], usage: dict) -> None:
    for k in USAGE_KEYS:
        target[k] += int(usage.get(k) or 0)
    target["total_tokens"] += sum(int(usage.get(k) or 0) for k in USAGE_KEYS)


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def iter_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    yield obj
    except OSError:
        return


def session_files(root_file: Path) -> list[Path]:
    """The main transcript plus any subagent transcripts for the session."""
    sub_dir = root_file.with_suffix("") / "subagents"
    return [root_file, *sorted(sub_dir.glob("agent-*.jsonl"))]


def first_timestamp(path: Path) -> datetime | None:
    for obj in iter_json(path):
        ts = parse_ts(obj.get("timestamp"))
        if ts:
            return ts
    return None


def collect_sessions(projects_dir: Path, day: str | None) -> dict[str, Path]:
    """Map session id -> main transcript path."""
    since = None
    if day:
        since = datetime.combine(Date.fromisoformat(day), datetime.min.time()).timestamp()
    sessions = {}
    for path in projects_dir.glob("*/*.jsonl"):
        if since is not None:
            try:
                if path.stat().st_mtime < since:
                    continue
            except OSError:
                continue
            started = first_timestamp(path)
            if not started or started.astimezone().date().isoformat() != day:
                continue
        sessions[path.stem] = path
    return sessions


def spawn_roles(entries: list[dict], meta_roles: dict[str, str]) -> dict[str, str]:
    """Map agentId -> subagent_type using the parent's Agent tool calls."""
    by_tool_use: dict[str, str] = {}
    roles = dict(meta_roles)
    for obj in entries:
        content = (obj.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("name") in SPAWN_TOOLS:
                by_tool_use[block.get("id")] = (block.get("input") or {}).get("subagent_type") or "subagent"
            elif block.get("type") == "tool_result" and block.get("tool_use_id") in by_tool_use:
                role = by_tool_use[block["tool_use_id"]]
                result = obj.get("toolUseResult")
                agent_id = result.get("agentId") if isinstance(result, dict) else None
                if not agent_id:
                    text = json.dumps(block.get("content"))
                    match = AGENT_ID_TEXT.search(text)
                    agent_id = match.group(1) if match else None
                if agent_id:
                    roles.setdefault(agent_id, role)
    return roles


def analyze_session(root_file: Path) -> list[dict]:
    files = session_files(root_file)
    threads: dict[str, dict] = {}
    entries: list[dict] = []
    meta_roles: dict[str, str] = {}

    for path in files:
        if path != root_file:
            meta = path.with_suffix(".meta.json")
            try:
                agent_type = json.loads(meta.read_text(encoding="utf-8")).get("agentType")
            except (OSError, ValueError, AttributeError):
                agent_type = None
            if agent_type:
                meta_roles[path.stem.removeprefix("agent-")] = agent_type
        for obj in iter_json(path):
            entries.append(obj)
            if obj.get("isSidechain") and obj.get("agentId"):
                key = obj["agentId"]
            elif path == root_file:
                key = "root"
            else:
                key = path.stem.removeprefix("agent-")
            t = threads.setdefault(key, {"id": key, "messages": {}, "started": None, "ended": None,
                                         "cwd": None, "version": None})
            ts = parse_ts(obj.get("timestamp"))
            if ts:
                t["started"] = min(t["started"] or ts, ts)
                t["ended"] = max(t["ended"] or ts, ts)
            t["cwd"] = t["cwd"] or obj.get("cwd")
            t["version"] = t["version"] or obj.get("version")
            if obj.get("type") != "assistant":
                continue
            msg = obj.get("message") or {}
            model = msg.get("model")
            if not msg.get("usage") or not model or model == "<synthetic>":
                continue
            # Claude Code writes one line per content block, each repeating the
            # response's usage; keep one record per message id.
            t["messages"][msg.get("id") or obj.get("uuid")] = (model, msg["usage"])

    roles = spawn_roles(entries, meta_roles)
    out = []
    for key, t in threads.items():
        per_model: dict[str, dict[str, int]] = defaultdict(empty_usage)
        responses: dict[str, int] = defaultdict(int)
        for model, usage in t["messages"].values():
            add_usage(per_model[model], usage)
            responses[model] += 1
        out.append({
            "id": key if key != "root" else root_file.stem,
            "role": "root" if key == "root" else roles.get(key, "subagent"),
            "models": sorted(per_model),
            "cwd": t["cwd"],
            "version": t["version"],
            "started": t["started"],
            "ended": t["ended"],
            "per_model": dict(per_model),
            "responses": dict(responses),
        })
    far = datetime.max.replace(tzinfo=timezone.utc)
    out.sort(key=lambda t: (t["role"] != "root", t["started"] or far))
    return out


def fmt_int(n: int) -> str:
    return f"{n:,}"


def fmt_duration(start: datetime | None, end: datetime | None) -> str:
    if not start or not end:
        return "-"
    seconds = int((end - start).total_seconds())
    return f"{seconds // 60}m{seconds % 60:02d}s"


def render_markdown(session_id: str, threads: list[dict]) -> str:
    root = next((t for t in threads if t["role"] == "root"), None)
    starts = [t["started"] for t in threads if t["started"]]
    ends = [t["ended"] for t in threads if t["ended"]]
    wall = fmt_duration(min(starts), max(ends)) if starts and ends else "-"

    lines: list[str] = [f"### Session `{session_id[:8]}`", ""]
    if root:
        lines.append(f"- cwd: `{root['cwd']}`")
        lines.append(f"- claude code: `{root['version']}`")
    lines.append(f"- threads: {len(threads)} ({len(threads) - 1 if root else len(threads)} subagents)")
    lines.append(f"- wall time: {wall}")
    lines.append("")

    lines.append("| Thread | Role | Model | Responses | Uncached in | Cache write | Cache read | Output | Total | Duration |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|")
    grand = empty_usage()
    by_model: dict[str, dict[str, int]] = defaultdict(empty_usage)
    by_model_responses: dict[str, int] = defaultdict(int)
    by_model_threads: dict[str, int] = defaultdict(int)
    for t in threads:
        for model, usage in sorted(t["per_model"].items()):
            lines.append(
                f"| `{t['id'][:8]}` | {t['role']} | {model} | {t['responses'].get(model, 0)} | "
                f"{fmt_int(usage['input_tokens'])} | {fmt_int(usage['cache_creation_input_tokens'])} | "
                f"{fmt_int(usage['cache_read_input_tokens'])} | {fmt_int(usage['output_tokens'])} | "
                f"{fmt_int(usage['total_tokens'])} | {fmt_duration(t['started'], t['ended'])} |"
            )
            for k in grand:
                grand[k] += usage[k]
                by_model[model][k] += usage[k]
            by_model_responses[model] += t["responses"].get(model, 0)
            by_model_threads[model] += 1
    lines.append("")

    lines.append("| Model | Threads | Responses | Uncached in | Cache write | Cache read | Output | Total |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for model, usage in sorted(by_model.items()):
        lines.append(
            f"| {model} | {by_model_threads[model]} | {by_model_responses[model]} | "
            f"{fmt_int(usage['input_tokens'])} | {fmt_int(usage['cache_creation_input_tokens'])} | "
            f"{fmt_int(usage['cache_read_input_tokens'])} | {fmt_int(usage['output_tokens'])} | "
            f"{fmt_int(usage['total_tokens'])} |"
        )
    lines.append(
        f"| **all** | {len(threads)} | {sum(by_model_responses.values())} | "
        f"{fmt_int(grand['input_tokens'])} | {fmt_int(grand['cache_creation_input_tokens'])} | "
        f"{fmt_int(grand['cache_read_input_tokens'])} | {fmt_int(grand['output_tokens'])} | "
        f"{fmt_int(grand['total_tokens'])} |"
    )
    total_in = grand["input_tokens"] + grand["cache_creation_input_tokens"] + grand["cache_read_input_tokens"]
    if total_in:
        lines.append("")
        lines.append(f"Cache hit rate on input: {100.0 * grand['cache_read_input_tokens'] / total_in:.1f}%")
    return "\n".join(lines)


def to_json(session_id: str, threads: list[dict]) -> str:
    def clean(t: dict) -> dict:
        out = dict(t)
        out["started"] = t["started"].isoformat() if t["started"] else None
        out["ended"] = t["ended"].isoformat() if t["ended"] else None
        return out

    return json.dumps({"root": session_id, "threads": [clean(t) for t in threads]}, indent=2)


def summarize(root_file: Path) -> tuple[datetime, int, str | None]:
    started = first_timestamp(root_file) or datetime.min.replace(tzinfo=timezone.utc)
    n_sub = len(session_files(root_file)) - 1
    if n_sub == 0:
        # Older layouts kept subagent entries in the main transcript.
        n_sub = len({o["agentId"] for o in iter_json(root_file) if o.get("isSidechain") and o.get("agentId")})
    cwd = next((o["cwd"] for o in iter_json(root_file) if o.get("cwd")), None)
    return started, n_sub, cwd


def list_sessions(sessions: dict[str, Path], limit: int) -> None:
    rows = [(*summarize(path), sid) for sid, path in sessions.items()]
    rows.sort(key=lambda r: r[0], reverse=True)
    print("started (UTC)       session   subagents  cwd")
    for started, n_sub, cwd, sid in rows[:limit]:
        print(f"{started.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M'):<19} {sid[:8]}  {n_sub:>9}  {cwd}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--projects-dir", default=os.path.expanduser("~/.claude/projects"))
    parser.add_argument("--date", help="Only scan sessions started on this local day (YYYY-MM-DD). Much faster.")
    parser.add_argument("--list", action="store_true", help="List sessions and their subagent counts.")
    parser.add_argument("--limit", type=int, default=20, help="Rows to show with --list.")
    parser.add_argument("--root", help="Session id (or unique prefix) to report on.")
    parser.add_argument("--latest", action="store_true", help="Report on the most recent session that spawned subagents.")
    parser.add_argument("--format", choices=("md", "json"), default="md")
    args = parser.parse_args(argv)

    projects_dir = Path(args.projects_dir)
    if not projects_dir.is_dir():
        print(f"projects dir not found: {projects_dir}", file=sys.stderr)
        return 2

    sessions = collect_sessions(projects_dir, args.date)
    if not sessions:
        print("no transcripts found", file=sys.stderr)
        return 1

    if args.list:
        list_sessions(sessions, args.limit)
        return 0

    if args.root:
        matches = [s for s in sessions if s.startswith(args.root)]
        if len(matches) != 1:
            print(f"--root matched {len(matches)} sessions; give a longer prefix", file=sys.stderr)
            return 2
        session_id = matches[0]
    elif args.latest:
        candidates = [(started, sid) for sid, path in sessions.items()
                      for started, n_sub, _ in [summarize(path)] if n_sub]
        if not candidates:
            print("no session with subagents found", file=sys.stderr)
            return 1
        session_id = max(candidates)[1]
    else:
        parser.print_help()
        return 2

    threads = analyze_session(sessions[session_id])
    if args.format == "json":
        print(to_json(session_id, threads))
    else:
        print(render_markdown(session_id, threads))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
