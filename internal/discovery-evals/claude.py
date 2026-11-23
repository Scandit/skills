"""Replay frozen cases using Claude Code and its existing first-party login.

The launcher needs --restricted support. Each session gets only local read-only
tools, a fresh fixture and the staged skills. The temporary plugin omits remote
MCP registration for both variants. No credential export or API key is needed.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from focused import FOCUSED, prepare

HERE = Path(__file__).resolve().parent
TOOLS = ("Read", "Glob", "Grep", "Skill")
BUILTINS = {"design", "doctor", "plugin-authoring"}
MODELS = ("claude-haiku-5-5", "claude-sonnet-5-5")
CASES = ("integration", "advisor", "migration", "unrelated", "react-native")


def project_inventory(project):
    """Observe project-local discovery without a model request or a plugin."""
    with tempfile.TemporaryDirectory(prefix="selected-skill-") as tmp:
        root = Path(tmp).resolve()
        work, home = root / "project", root / "home"
        shutil.copytree(project, work)
        subprocess.run(["git", "init", "--quiet", str(work)], check=True)
        home.mkdir()
        env = {"HOME": str(home), "PATH": os.environ["PATH"],
               "CLAUDE_CONFIG_DIR": str(home / ".claude"),
               "ANTHROPIC_BASE_URL": "http://127.0.0.1:1",
               "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"}
        settings = {"disableAllHooks": True, "disableClaudeAiConnectors": True,
                    "syncClaudeAiPlugins": False, "syncClaudeAiSkills": False,
                    "disableBundledSkills": True, "autoMemoryEnabled": False}
        args = ["claude", "-p", "--setting-sources", "project", "--no-session-persistence",
                "--output-format", "stream-json", "--verbose", "--no-chrome",
                "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
                "--settings", json.dumps(settings), "--tools", "Read,Skill",
                "--permission-mode", "dontAsk", "--", "/skills"]
        run = subprocess.run(args, env=env, cwd=work, capture_output=True, text=True,
                             stdin=subprocess.DEVNULL, timeout=30, check=True)
        events = [json.loads(line) for line in run.stdout.splitlines()]
        init = next(e for e in events if e.get("subtype") == "init")
        result = next(e for e in events if e.get("type") == "result")
        catalog = {s.parent.name for s in (HERE.parents[1] / "skills").glob("*/SKILL.md")}
        effective = sorted(set(init["skills"]) & catalog)
        if effective != ["barcode-capture-rn"] or result.get("modelUsage") or init["mcp_servers"]:
            raise ValueError("Offline Claude project skill inventory did not match the single-skill install")
        return {"cli_version": init["claude_code_version"], "scandit": effective,
                "other_skills": sorted(set(init["skills"]) - catalog),
                "mcp_servers": len(init["mcp_servers"]), "model_calls": 0}


def stage(source, destination):
    skills = source / "skills"
    if any(path.is_symlink() for path in skills.rglob("*")):
        raise ValueError("Staged skills must be ordinary files and directories")
    shutil.copytree(skills, destination / "skills")
    manifest_dir = destination / ".claude-plugin"
    manifest_dir.mkdir()
    manifest = json.loads((source / ".claude-plugin/plugin.json").read_text())
    manifest.pop("mcpServers", None)
    (manifest_dir / "plugin.json").write_text(json.dumps(manifest))
    return {f"{manifest['name']}:{s.parent.name}" for s in skills.glob("*/SKILL.md")}


def cli(package, model, prompt):
    personal = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")) / "skills"
    settings = {
        "autoMemoryEnabled": False, "disableClaudeAiConnectors": True,
        "disableAllHooks": True, "syncClaudeAiSkills": False,
        "syncClaudeAiPlugins": False, "disableBundledSkills": True,
        "claudeMdExcludes": ["**/CLAUDE.md", "**/CLAUDE.local.md"],
        "skillOverrides": {s.name: "off" for s in personal.glob("*") if s.is_dir()},
    }
    return [
        "claude", "-p", "--restricted", "--model", model, "--effort", "low",
        "--output-format", "stream-json", "--verbose", "--no-session-persistence",
        "--setting-sources", "", "--settings", json.dumps(settings), "--no-chrome",
        "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
        "--plugin-dir", str(package), "--add-dir", str(package),
        "--tools", ",".join(TOOLS), "--allowedTools", ",".join(TOOLS),
        "--permission-mode", "dontAsk", "--permission-prompts", "none", "--", prompt,
    ]


def summarize(events, expected, model, work, package, case):
    init = next((e for e in events if e.get("subtype") == "init"), {})
    result = next((e for e in reversed(events) if e.get("type") == "result"), {})
    skills = init.get("skills", [])
    plugins = init.get("plugins", [])
    unexpected_skills = set(skills) - expected - BUILTINS
    unexpected_plugins = [p for p in plugins if p.get("source") != "scandit-sdk@inline"
                          and not p.get("source", "").endswith("@builtin")]
    inventory_ok = (expected.issubset(skills) and not unexpected_skills
                    and not unexpected_plugins and set(init.get("tools", [])) == set(TOOLS)
                    and not init.get("mcp_servers"))
    assistants = [e["message"] for e in events if e.get("type") == "assistant"]
    models = sorted({m["model"] for m in assistants if m.get("model")})
    summary = {
        "cli_version": init.get("claude_code_version"), "requested_model": model,
        "models": models, "init_model": init.get("model"), "inventory_ok": inventory_ok,
        "skills": sorted(set(skills) & (expected | BUILTINS)),
        "unexpected_skill_count": len(unexpected_skills), "unexpected_plugin_count": len(unexpected_plugins),
        "tools": [t for t in init.get("tools", []) if t in TOOLS],
        "unexpected_tool_count": len(set(init.get("tools", [])) - set(TOOLS)),
        "mcp_server_count": len(init.get("mcp_servers", [])),
        "plugins": [p.get("source") for p in plugins if p not in unexpected_plugins],
        "subtype": result.get("subtype"), "is_error": result.get("is_error"),
    }
    if not inventory_ok:
        return summary

    def normalized(value):
        return (str(value).replace(str(work), "[fixture]").replace(str(package), "[package]")
                .replace(str(work.parent), "[session]"))

    outcomes, reference_reads, tool_results = {}, {}, {}
    for event in events:
        if event.get("type") == "user":
            for b in event.get("message", {}).get("content", []):
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    outcomes[b["tool_use_id"]] = not b.get("is_error", False)
                    if case in FOCUSED:
                        tool_results[b["tool_use_id"]] = b.get("content", "")
                    payload = event.get("tool_use_result")
                    if case in FOCUSED and isinstance(payload, dict) and isinstance(payload.get("file"), dict):
                        file = payload["file"]
                        path = Path(file.get("filePath", "")).resolve()
                        if (path.is_relative_to(package / "skills") and "references" in path.parts
                                and path.is_file() and isinstance(file.get("content"), str)):
                            reference_reads[b["tool_use_id"]] = {
                                key: file[key] for key in ("content", "startLine", "numLines", "totalLines")
                            }
    turns, calls = {}, {}
    for message in assistants:
        if message.get("usage"):
            turns[message["id"]] = message["usage"]
        for block in message.get("content", []):
            if block.get("type") != "tool_use":
                continue
            target = block.get("input", {})
            # Directory listings and searches are never proof of a file open.
            call = {"tool": block["name"], "successful": outcomes.get(block["id"])}
            for key in ("skill", "file_path", "path", "offset", "limit"):
                if key in target:
                    call[key] = normalized(target[key])
            if block["id"] in reference_reads and call["successful"]:
                call["reference_read"] = reference_reads[block["id"]]
            if case in FOCUSED and block["name"] == "Grep" and call["successful"]:
                searched = (work / target.get("path", ".")).resolve()
                if searched.is_relative_to(package) or searched.is_relative_to(work):
                    content = tool_results[block["id"]]
                    if isinstance(content, list):
                        content = "\n".join(s["text"] for s in content if s.get("type") == "text")
                    call["grep_result"] = {
                        "pattern": normalized(target.get("pattern", "")),
                        "output_mode": target.get("output_mode", "files_with_matches"),
                        "output": normalized(content),
                    }
            calls[block["id"]] = call
    summary.update(
        turns=list(turns.values()), usage=result.get("usage"), model_usage=result.get("modelUsage"),
        tools_complete=all(c["successful"] is not None for c in calls.values()),
        calls=list(calls.values()), answer=normalized(result.get("result", "")),
    )
    return summary


def run(args, variant, case, model):
    prefix = args.output / args.round / model / variant
    prefix.mkdir(parents=True, exist_ok=True)
    target = prefix / f"{case}.json"
    if target.exists():
        raise FileExistsError(f"Select a new --round to preserve existing {target}")
    with tempfile.TemporaryDirectory(prefix="discovery-eval-") as tmp:
        root = Path(tmp).resolve()
        work, package = root / "fixture", root / "package"
        expected = stage(args.stages / variant, package)
        if case in FOCUSED:
            prompt = prepare(case, work)
        else:
            shutil.copytree(HERE / "cases" / case, work)
            prompt = (HERE / "prompts" / f"{case}.txt").read_text()
        env = {**os.environ, "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"}
        try:
            process = subprocess.run(cli(package, model, prompt), cwd=work, env=env, text=True,
                                     stdin=subprocess.DEVNULL, capture_output=True, timeout=360)
        except subprocess.TimeoutExpired:
            summary = {"exit": 124, "error": "timeout"}
        else:
            events = []
            for line in process.stdout.splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if isinstance(event, dict):
                    events.append(event)
            summary = summarize(events, expected, model, work, package, case)
            summary["exit"] = process.returncode
            if process.returncode and not events:
                summary["error"] = "CLI returned no JSON events; check CLI login and option support"
    summary.update(variant=variant, case=case, round=args.round)
    with target.open("x") as output:
        json.dump(summary, output, indent=2)
        output.write("\n")
    valid = (summary["exit"] == 0 and summary.get("inventory_ok") and summary.get("models") == [model]
             and summary.get("subtype") == "success" and not summary.get("is_error")
             and summary.get("usage") and summary.get("tools_complete"))
    print(f"{variant} {case} {model}: {'complete' if valid else 'invalid'} ({target})", flush=True)
    return bool(valid)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stages", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--round", required=True)
    parser.add_argument("--model", nargs="+", choices=MODELS, default=MODELS)
    parser.add_argument("--variant", nargs="+", choices=("baseline", "candidate", "split"),
                        default=("baseline", "candidate"))
    parser.add_argument("--case", nargs="+", choices=(*CASES, *FOCUSED), default=CASES)
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    tasks = [(v, c, m) for c in args.case for m in args.model for v in args.variant]
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        valid = list(pool.map(lambda task: run(args, *task), tasks))
    return 0 if all(valid) else 1


if __name__ == "__main__":
    raise SystemExit(main())
