"""Writes report.json and report.md for a migration eval run."""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from score import REPO


def skills_revision():
    def git(*args):
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()
    return git("rev-parse", "HEAD"), bool(git("status", "--porcelain"))


def totals(rows):
    return {
        "fixtures": len(rows),
        "compiles": sum(1 for r in rows if r["compiles"]),
        "errors_left": sum(r["errors_left"] for r in rows),
        "symbologies_kept": sum(1 for r in rows if r["kept"]),
    }


def compiles_cell(row):
    if row["compiles"] is None:
        return "n/a"
    return "yes" if row["compiles"] else f"no ({row['status']})"


def kept_cell(row):
    total = len(row["expected"])
    cell = f"{total - len(row['missing'])}/{total}"
    return cell + (f" (missing: {', '.join(row['missing'])})" if row["missing"] else "")


def claude_cell(row):
    claude = row.get("claude")
    if not claude:
        return ""
    parts = [f"exit {claude['exit_code']}"] if claude.get("exit_code") is not None else []
    if claude.get("timed_out"):
        parts.append("timeout")
    if claude.get("num_turns") is not None:
        parts.append(f"{claude['num_turns']} turns")
    if claude.get("cost_usd") is not None:
        parts.append(f"${claude['cost_usd']:.2f}")
    return ", ".join(parts)


def render_markdown(report):
    dirty = " (dirty)" if report["dirty"] else ""
    lines = [
        "# Migration evals",
        "",
        f"Skills revision: `{report['skills_sha']}`{dirty}  ",
        f"Generated: {report['generated_at']}  ",
        f"Model: {report['model'] or 'default'}",
    ]
    for skill, data in report["skills"].items():
        t = data["totals"]
        lines += [
            "", f"## {skill}", "",
            "| id | fixture | compiles | errors left | symbologies kept | claude |",
            "|---|---|---|---|---|---|",
        ]
        for r in data["rows"]:
            lines.append(
                f"| {r['id']} | {r['fixture']} | {compiles_cell(r)} | {r['errors_left']} "
                f"| {kept_cell(r)} | {claude_cell(r)} |"
            )
        lines.append(
            f"| **total** | {t['fixtures']} | {t['compiles']}/{t['fixtures']} "
            f"| {t['errors_left']} | {t['symbologies_kept']}/{t['fixtures']} | |"
        )
    return "\n".join(lines) + "\n"


def write_report(rows_by_skill, out_dir, skills_sha=None, dirty=False, model=None):
    if skills_sha is None:
        skills_sha, dirty = skills_revision()
    report = {
        "skills_sha": skills_sha,
        "dirty": dirty,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": model,
        "skills": {s: {"rows": rows, "totals": totals(rows)} for s, rows in rows_by_skill.items()},
    }
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (out_dir / "report.md").write_text(render_markdown(report))
    return report
