#!/usr/bin/env python3
"""Runs claude over each third-party migration eval, then scores and reports.

Usage: run.py --skill barcode-capture-flutter [--ids 1,3] [--out DIR] [--jobs 4]
              [--model M] [--timeout 1200] [--score-only DIR]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report import write_report  # noqa: E402
from score import REPO, SUITES, eval_dir, fixture_paths, score_eval  # noqa: E402


def load_evals(skill, ids):
    evals_dir = eval_dir(skill)
    data = json.loads((evals_dir / "third-party-migration-evals.json").read_text())
    return evals_dir, [e for e in data["evals"] if not ids or e["id"] in ids]


def prepare_workdir(evals_dir, entry, work):
    fixtures = evals_dir / "fixtures"
    shutil.copy(fixtures / "pubspec.yaml", work / "pubspec.yaml")
    (work / "lib").mkdir()
    shutil.copy(evals_dir / entry["files"][0], work / "lib")
    shutil.copytree(fixtures / "stubs", work / "lib" / "stubs")


def claude_command(prompt, suite, model):
    cmd = [
        os.environ.get("CLAUDE", "claude"), "-p", prompt,
        "--plugin-dir", str(REPO), "--setting-sources", "project",
        "--output-format", "json", "--permission-mode", "acceptEdits",
        "--allowedTools", suite.allowed_tools,
    ]
    return cmd + (["--model", model] if model else [])


def as_text(value):
    return value.decode() if isinstance(value, bytes) else (value or "")


def save_outputs(entry, work, out):
    lib = work / "lib"
    for name in fixture_paths(entry):
        if (lib / name).is_file():
            (out / "lib" / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(lib / name, out / "lib" / name)


def run_claude(suite, evals_dir, entry, out, model, timeout):
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    info = {"exit_code": None, "timed_out": False, "model": model}
    with tempfile.TemporaryDirectory(prefix="migration-eval-") as tmp:
        work = Path(tmp)
        prepare_workdir(evals_dir, entry, work)
        prompt = entry["prompt"] + suite.prompt_suffix.format(main=fixture_paths(entry)[0])
        try:
            proc = subprocess.run(
                claude_command(prompt, suite, model), cwd=work, capture_output=True, text=True, timeout=timeout
            )
            info["exit_code"] = proc.returncode
            stdout, stderr = proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as exc:
            info["timed_out"] = True
            stdout, stderr = as_text(exc.stdout), as_text(exc.stderr)
        (out / "claude.json").write_text(stdout)
        (out / "claude.stderr").write_text(stderr)
        save_outputs(entry, work, out)
    (out / "run.json").write_text(json.dumps(info) + "\n")


def read_claude_info(out):
    info = {}
    try:
        info.update(json.loads((out / "run.json").read_text()))
    except (OSError, ValueError, TypeError):
        pass
    try:
        result = json.loads((out / "claude.json").read_text())
        info["num_turns"] = result.get("num_turns")
        info["cost_usd"] = result.get("total_cost_usd")
    except (OSError, ValueError, AttributeError):
        pass
    return info


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", required=True, choices=sorted(SUITES))
    ap.add_argument("--ids", default="")
    ap.add_argument("--out")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--model")
    ap.add_argument("--timeout", type=int, default=1200)
    ap.add_argument("--score-only", metavar="DIR")
    args = ap.parse_args(argv)

    try:
        ids = {int(i) for i in args.ids.split(",") if i}
    except ValueError:
        ap.error(f"--ids must be comma-separated integers, got {args.ids!r}")
    evals_dir, entries = load_evals(args.skill, ids)
    if not entries:
        ap.error(f"no evals match --ids {args.ids}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = Path(args.score_only or args.out or REPO / "eval-runs" / "migration" / stamp)
    skill_out = out_root / args.skill
    suite = SUITES[args.skill]
    if args.score_only and not ids:
        # Rescore only the fixtures the saved run has, so a partial run keeps its totals.
        entries = [e for e in entries if (skill_out / str(e["id"])).is_dir()]

    if not args.score_only:
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            futures = [
                pool.submit(run_claude, suite, evals_dir, e, skill_out / str(e["id"]), args.model, args.timeout)
                for e in entries
            ]
            for future in futures:
                future.result()

    rows = []
    for entry in entries:
        out = skill_out / str(entry["id"])
        row = score_eval(suite, entry, out, evals_dir)
        row["claude"] = read_claude_info(out)
        rows.append(row)
    model = args.model or next((r["claude"].get("model") for r in rows if r["claude"].get("model")), None)
    write_report({args.skill: rows}, out_root, model=model)
    print((out_root / "report.md").read_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
