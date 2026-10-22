#!/usr/bin/env python3
"""Fresh-agent licence smoke test: does each skill get a key from the MCP server into the code?

Usage: smoke.py [--skills barcode-capture-android,id-bolt] [--no-mcp-skill S] [--jobs 4]
              [--model M] [--timeout 900] [--out DIR] [--grade-only DIR]

One `claude -p` per skill in an empty temp project, with this checkout loaded via
`--plugin-dir` (its `.mcp.json` brings the Scandit MCP server), plus one run with
`--strict-mcp-config` and no server. Each run is graded from its stream-json tool
calls and assistant text, never from the agent's own summary.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "internal" / "skill-auditor" / "scripts"))
from lint_structure import CREDENTIAL_READ  # noqa: E402

# The lint's credential pattern, so the runtime check and the static one agree.
ENV_READ = re.compile(CREDENTIAL_READ)
SHELL_ENV = re.compile(r"\bprintenv\b|(?:^|[\s;&|(])env(?:\s|$)|\$\{?SCANDIT|os\.environ")
DEFAULT_SKILLS = [f"barcode-capture-{p}" for p in (
    "android", "ios", "web", "cordova", "capacitor", "flutter", "rn", "kmp",
    "net-android", "net-ios", "net-maui")] + ["id-bolt"]
# One identifier per platform set, so repeated runs reuse one trial key.
APP_ID = "com.scandit.licencesmoke"
WEB_ID = "licencesmoke.example.com"
ALLOWED_TOOLS = "Skill Read Write Edit Glob Grep mcp__plugin_scandit-sdk_scandit"


def prompt_for(skill):
    web = skill.endswith("-web") or skill == "id-bolt"
    what = "ID scanning" if skill == "id-bolt" else "barcode scanning"
    return (f"Use the scandit-sdk:{skill} skill to add {what} to a new app in this "
            f"empty directory. Its {'production domain' if web else 'application id'} is "
            f"{WEB_ID if web else APP_ID}. Write only the minimal source files, including the "
            "licence key setup; do not install dependencies or build.")


def claude_command(skill, mcp, model):
    cmd = [os.environ.get("CLAUDE", "claude"), "-p", prompt_for(skill),
           "--plugin-dir", str(REPO), "--setting-sources", "project",
           "--output-format", "stream-json", "--verbose", "--no-session-persistence",
           "--permission-mode", "acceptEdits", "--allowedTools", ALLOWED_TOOLS]
    if not mcp:
        cmd.append("--strict-mcp-config")
    return cmd + (["--model", model] if model else [])


def parse(lines):
    """Tool calls, tool results by id, assistant text and MCP status from stream-json lines."""
    calls, results, text, mcp = [], {}, [], {}
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            mcp = {s["name"]: s.get("status") for s in event.get("mcp_servers", [])}
        message = event.get("message")
        for item in (message.get("content") or [] if isinstance(message, dict) else []):
            if not isinstance(item, dict):
                continue
            if item.get("type") == "tool_use":
                calls.append(item)
            elif item.get("type") == "tool_result":
                content = item.get("content")
                results[item.get("tool_use_id")] = (content if isinstance(content, str)
                                                    else json.dumps(content))
            elif item.get("type") == "text" and event.get("type") == "assistant":
                text.append(item["text"])
    return calls, results, "\n".join(text), mcp


def tool(call):
    return call["name"].rsplit("__", 1)[-1]


def grade(lines, mcp):
    """Failure reasons for one run; an empty list is a pass."""
    calls, results, text, servers = parse(lines)
    failures = []
    names = [tool(c) for c in calls]
    for c in calls:
        if c["name"].startswith("mcp__"):
            continue  # the server's own `env_var` / `env_file` arguments read nothing
        payload = json.dumps(c.get("input", {}))
        if ENV_READ.search(payload) or (c["name"] == "Bash" and SHELL_ENV.search(payload)):
            failures.append(f"{c['name']} touches `.env` or the environment: {payload[:120]}")
    if "get_license_env_command" in names:
        failures.append("called get_license_env_command")
    if not mcp:
        if any(c["name"].startswith("mcp__") for c in calls):
            failures.append("called an MCP tool with no server configured")
        if not re.search(r"licen[cs]e key", text, re.I):
            failures.append("did not ask the user for the licence key")
        return failures
    if not any(s == "connected" for n, s in servers.items() if "scandit" in n):
        return [f"precondition: Scandit MCP server not connected ({servers}) — run /mcp once"]
    for required in ("ensure_scanner_setup", "get_license_key"):
        if required not in names:
            failures.append(f"never called {required}")
    keys = {k for c in calls if tool(c) == "get_license_key"
            for k in re.findall(r"[A-Za-z0-9+/=_-]{60,}", results.get(c["id"], ""))}
    written = " ".join(json.dumps(c.get("input", {})) for c in calls
                       if c["name"] in ("Write", "Edit", "MultiEdit"))
    if "get_license_key" in names and not keys:
        failures.append("get_license_key returned no key")
    elif keys and not any(k in written for k in keys):
        failures.append("the key from get_license_key was not written into the code")
    if any(k in text for k in keys):
        failures.append("printed the full key in assistant text")
    return failures


def run_one(skill, mcp, model, timeout, out):
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as work:
        try:
            proc = subprocess.run(claude_command(skill, mcp, model), cwd=work,
                                  capture_output=True, text=True, timeout=timeout)
            stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired as exc:
            stdout, stderr, code = exc.stdout or "", exc.stderr or "", "timeout"
    stdout = stdout.decode() if isinstance(stdout, bytes) else stdout
    (out / "stream.jsonl").write_text(stdout)
    (out / "claude.stderr").write_text(stderr if isinstance(stderr, str) else stderr.decode())
    (out / "run.json").write_text(json.dumps({"skill": skill, "mcp": mcp, "exit": code}))
    return grade_dir(out)


def grade_dir(out):
    meta = json.loads((out / "run.json").read_text())
    failures = grade((out / "stream.jsonl").read_text().splitlines(), meta["mcp"])
    if meta["exit"] == "timeout":
        failures.insert(0, "timed out; graded on a partial stream")
    return {**meta, "pass": not failures, "failures": failures}


def main():
    ap = argparse.ArgumentParser(description="Fresh-agent licence smoke test")
    ap.add_argument("--skills", default=",".join(DEFAULT_SKILLS))
    ap.add_argument("--no-mcp-skill", default="barcode-capture-android")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--model")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--grade-only", type=Path)
    args = ap.parse_args()
    if args.grade_only:
        rows = [grade_dir(d) for d in sorted(args.grade_only.iterdir()) if (d / "run.json").is_file()]
        out = args.grade_only
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = args.out or REPO / "eval-runs" / "licence-smoke" / stamp
        runs = [(s, True, out / s) for s in args.skills.split(",")]
        runs.append((args.no_mcp_skill, False, out / f"no-mcp-{args.no_mcp_skill}"))
        with ThreadPoolExecutor(args.jobs) as pool:
            rows = list(pool.map(lambda r: run_one(r[0], r[1], args.model, args.timeout, r[2]), runs))
    (out / "report.json").write_text(json.dumps(rows, indent=2))
    for r in rows:
        print(f"{'PASS' if r['pass'] else 'FAIL'}  {r['skill']}{'' if r['mcp'] else ' (no MCP)'}"
              + "".join(f"\n      {f}" for f in r["failures"]))
    print(f"report: {out / 'report.json'}")
    sys.exit(0 if all(r["pass"] for r in rows) else 1)


if __name__ == "__main__":
    main()
