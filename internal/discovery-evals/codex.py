"""Run one frozen discovery case with native Codex project-local skills."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from focused import FOCUSED, prepare

HERE = Path(__file__).resolve().parent
MODELS = ("gpt-6-luna", "gpt-6.2-sol")
SYSTEM = {"imagegen", "openai-docs", "skill-creator", "skill-installer"}


def strings(data):
    if isinstance(data, str):
        yield data
    elif isinstance(data, (list, dict)):
        for value in data.values() if isinstance(data, dict) else data:
            yield from strings(value)


def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def command(project, model, marketplace):
    executable = Path(shutil.which("codex") or "codex").resolve(strict=True)
    # Grant shell reads for the fixture and CLI helpers. No unrestricted home or network.
    readable = [project, executable.parent]
    if tool := shutil.which("rg"):
        readable.append(Path(tool).resolve())
    fs = {":minimal": "read", "/tmp": "deny", "/private/tmp": "deny", **{str(p): "read" for p in readable}}
    table = "{" + ",".join(f"{json.dumps(k)}={json.dumps(v)}" for k, v in fs.items()) + "}"
    flags = [str(executable), "--no-daemon", "-a", "never", "-m", model,
             "-c", 'model_reasoning_effort="low"', "-c", "project_doc_max_bytes=0",
             "-c", 'default_permissions="fixture"', "-c", "permissions.fixture.filesystem=" + table,
             "-c", 'web_search="disabled"', "-c", 'model_provider="openai"',
             "-c", 'shell_environment_policy.inherit="none"',
             "-c", 'shell_environment_policy.set.PATH=' + json.dumps(
                 os.pathsep.join(dict.fromkeys(["/usr/bin", "/bin", str(executable.parent),
                                                str(Path(shutil.which("rg") or "/usr/bin/rg").parent)]))),
             "-c", f'projects.{json.dumps(str(project))}.trust_level="trusted"']
    for feature in ("plugins", "hooks", "apps", "remote_plugin", "multi_agent", "multi_agent_v2",
                    "skill_mcp_dependency_install", "computer_use", "browser_use", "recommended_plugins"):
        flags.extend(["--enable" if feature == "plugins" and marketplace else "--disable", feature])
    home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    for filename in ("AGENTS.md", "AGENTS.override.md"):
        if (home / filename).is_file() and (home / filename).stat().st_size:
            raise RuntimeError("Use a clean authenticated Codex profile without global instructions")
    paths = set()
    for directory in (home / "skills", Path.home() / ".agents/skills"):
        for skill in directory.glob("*/SKILL.md"):
            paths.update((skill, skill.resolve()))
    entries = ",".join("{path=" + json.dumps(str(p)) + ",enabled=false}" for p in sorted(paths))
    return flags + ["-c", "skills.config=[" + entries + "]"]


def inventory(flags, env, project, expected, prefix=""):
    result = subprocess.run([*flags, "debug", "prompt-input", "sample"], cwd=project, env=env,
                            text=True, capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError("Offline catalog renderer failed: " + result.stderr[-600:])
    rows = [line for item in strings(json.loads(result.stdout)) for line in item.splitlines()
            if line.startswith("- ") and "(file:" in line]
    names = [line[2:].split(": ", 1)[0].removeprefix(prefix) for line in rows]
    count = Counter(names)
    if expected - count.keys() or count.keys() - expected - SYSTEM or max(count.values(), default=0) != 1:
        raise RuntimeError(f"Unexpected inventory: missing={sorted(expected-count.keys())}, "
                           f"extra={sorted(count.keys()-expected-SYSTEM)}, duplicates={sum(count.values())-len(count)}")
    package = [row for name, row in zip(names, rows) if name in expected]
    return {"scandit": sorted(expected), "other": sorted(count.keys() - expected),
            "scandit_characters": len("\n".join(package)),
            "entries": [row.replace(str(project), "<project>") for row in package]}


def run(args):
    dest = args.out.resolve()
    dest.mkdir(parents=True, exist_ok=False)
    env = {k: v for k, v in os.environ.items() if k in
           ("HOME", "CODEX_HOME", "USER", "LOGNAME", "PATH", "LANG", "LC_ALL", "TERM", "TMPDIR", "SSL_CERT_FILE")}
    with tempfile.TemporaryDirectory(prefix="discovery-") as scratch:
        project = (Path(scratch) / "project").resolve()
        if args.case in FOCUSED:
            prompt = prepare(args.case, project)
        else:
            prompt = (HERE / "prompts" / (args.case + ".txt")).read_text()
            shutil.copytree(HERE / "cases" / args.case, project)
        (project / ".git").mkdir(exist_ok=True)
        package = args.package.resolve()
        expected = {p.parent.name for p in (package / "skills").glob("*/SKILL.md")}
        if not expected:
            raise RuntimeError("Package contains no skills")
        flags = command(project, args.model, args.marketplace)
        version = subprocess.check_output([flags[0], "--version"], text=True, stderr=subprocess.DEVNULL).strip()
        install = "isolated local marketplace" if args.marketplace else "project-local .agents/skills"
        save(dest / "settings.json", {"version": version, "requested_model": args.model, "effort": "low",
             "case": args.case, "install": install, "mcp": "disabled",
             "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()})
        prefix = ""
        if args.marketplace:
            profile = Path(scratch) / "profile"
            profile.mkdir()
            env["CODEX_HOME"] = str(profile)
            plugin = "scandit-sdk@scandit-plugins"
            flags += ["-c", f'plugins."{plugin}".mcp_servers.scandit.enabled=false',
                      "-c", 'mcp_servers.scandit={enabled=false,url="https://ssl.scandit.com/mcp"}']
            for steps in (["marketplace", "add", str(package)], ["add", plugin]):
                subprocess.run([*flags, "plugin", *steps, "--json"], cwd=project, env=env, capture_output=True,
                               check=True, text=True, timeout=60)
            prefix = "scandit-sdk:"
        else:
            shutil.copytree(package / "skills", project / ".agents" / "skills")
        # The renderer lacks exec's --ignore-user-config flag. Give it a clean
        # profile with the same cached model metadata used for catalog limits.
        render_env = env.copy()
        if not args.marketplace:
            profile = Path(scratch) / "renderer"
            profile.mkdir()
            cache = Path(env.get("CODEX_HOME", Path.home() / ".codex")) / "models_cache.json"
            if cache.is_file():
                shutil.copyfile(cache, profile / cache.name)
            render_env["CODEX_HOME"] = str(profile)
        save(dest / "inventory.json", inventory(flags, render_env, project, expected, prefix))
        if args.measure:
            result = subprocess.run([*flags, "exec", "--ignore-user-config", "--ignore-rules", "--ephemeral",
                                     "--skip-git-repo-check", "--json", "-"], cwd=project, env=env, input=prompt,
                                    text=True, capture_output=True, timeout=600)
            def normalize(text):
                return text.replace(str(project), "<project>").replace(str(Path.home()), "<home>")
            (dest / "events.jsonl").write_text(normalize(result.stdout))
            (dest / "stderr.log").write_text(normalize(result.stderr))
            events = [json.loads(line) for line in result.stdout.splitlines()]
            if result.returncode or not events or events[-1]["type"] != "turn.completed":
                raise RuntimeError(f"Run incomplete. See {dest}/events.jsonl and stderr.log")
            save(dest / "usage.json", events[-1]["usage"])


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--package", type=Path, required=True)
    cli.add_argument("--case", choices=sorted({p.stem for p in (HERE / "prompts").glob("*.txt")} | FOCUSED.keys()),
                     required=True)
    cli.add_argument("--model", choices=MODELS, required=True)
    cli.add_argument("--out", type=Path, required=True, help="New directory for this single observation")
    action = cli.add_mutually_exclusive_group()
    action.add_argument("--measure", action="store_true", help="Run the official model after the inventory check")
    action.add_argument("--marketplace", action="store_true", help="Check offline installation in a fresh marketplace profile")
    run(cli.parse_args())
