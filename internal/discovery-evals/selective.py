"""Reproduce the public project-local single-skill installation in empty profiles."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def codex_inventory(project):
    from codex import inventory

    # Keep discovery outside this source checkout and its plugin manifest.
    with tempfile.TemporaryDirectory(prefix="selected-skill-") as tmp:
        root = Path(tmp).resolve()
        work = root / "project"
        shutil.copytree(project, work)
        subprocess.run(["git", "init", "--quiet", str(work)], check=True)
        profile = root / "home" / ".codex"
        profile.mkdir(parents=True)
        env = {"PATH": os.environ["PATH"], "HOME": str(profile.parent), "CODEX_HOME": str(profile)}
        flags = ["codex", "--no-daemon", "-c", f'projects.{json.dumps(str(work))}.trust_level="trusted"']
        return inventory(flags, env, work, {"barcode-capture-rn"})


def install(out, agent):
    project = out / agent / "project"
    profile = out / agent / "profile"
    project.mkdir(parents=True)
    profile.mkdir()
    env = {"PATH": os.environ["PATH"], "HOME": str(profile), "CI": "1",
           "DISABLE_TELEMETRY": "1", "GIT_TERMINAL_PROMPT": "0"}
    cli = ["npx", "--yes", "skills@1.7.0"]
    add = ["add", "scandit/skills", "--skill", "barcode-capture-rn",
           "--agent", agent, "--copy", "-y"]
    subprocess.run(cli + add, env=env, cwd=project, check=True)
    listing = subprocess.check_output(cli + ["list", "--agent", agent],
                                      env=env, cwd=project, text=True)
    print(listing)
    files = sorted(path.relative_to(project).as_posix()
                   for path in project.rglob("SKILL.md"))
    if not files or {Path(p).parent.name for p in files} != {"barcode-capture-rn"}:
        raise ValueError(f"Unexpected skill inventory: {files}")
    if "barcode-capture-rn" not in listing:
        raise ValueError("Selected skill missing from installer inventory")
    evidence = {"agent": agent, "command": cli + add, "files": files,
                "lock": json.loads((project / "skills-lock.json").read_text())}
    if agent == "codex":
        evidence["effective"] = codex_inventory(project)
    else:
        from claude import project_inventory
        evidence["effective"] = project_inventory(project)
    (out / agent / "inventory.json").write_text(json.dumps(evidence, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--agent", required=True, choices=["codex", "claude-code"])
    args = parser.parse_args()
    install(args.out.resolve(), args.agent)
