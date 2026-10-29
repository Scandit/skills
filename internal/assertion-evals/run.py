#!/usr/bin/env python3
"""Runs the assertion evals (evals/<skill>/*evals.json) through `claude -p` and scores them.

Usage: run.py --skill barcode-capture-android [--skill 'id-capture-*'] [--files integration-evals]
              [--ids 1,3] [--smoke] [--reps N] [--ref main] [--jobs 4] [--out DIR]
              [--model sonnet] [--effort medium] [--judge-model opus]
"""
import argparse
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score import JUDGE_SYSTEM, deterministic_check, judge_prompt, parse_verdicts, scoped_output  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
TASK = (
    "Apply the skill. Output the complete final file content (or files) the user should "
    "end up with, plus any setup checklist required. Use code fences for files."
)


def claude(prompt, system_file, model, effort, timeout, work):
    cmd = [
        os.environ.get("CLAUDE", "claude"), "-p", prompt, "--output-format", "json",
        "--model", model, "--system-prompt-file", str(system_file),
        "--tools", "", "--setting-sources", "", "--strict-mcp-config",
        "--disable-slash-commands", "--no-session-persistence",
    ]
    if effort:
        cmd += ["--effort", effort]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=work)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise RuntimeError((proc.stderr or proc.stdout)[-300:]) from None
    if proc.returncode or data.get("is_error"):
        raise RuntimeError(str(data.get("result") or proc.stderr)[-300:])
    return data["result"], data.get("total_cost_usd") or 0.0, set(data.get("modelUsage") or ())


def skills_root(ref, work):
    if not ref:
        return REPO / "skills"
    data = subprocess.run(["git", "-C", str(REPO), "archive", ref, "skills"], capture_output=True, check=True).stdout
    tarfile.open(fileobj=io.BytesIO(data)).extractall(work / "ref", filter="data")
    return work / "ref" / "skills"


def system_file(skill_dir, work):
    parts = [f"# Skill\n{(skill_dir / 'SKILL.md').read_text()}"]
    parts += [f"---\n# references/{r.name}\n{r.read_text()}" for r in sorted((skill_dir / "references").glob("*.md"))]
    path = work / f"{skill_dir.name}.system.md"
    path.write_text("\n\n".join(parts))
    return path


def collect(args, root):
    skills = sorted({d.name for pattern in args.skill for d in (REPO / "evals").glob(pattern) if d.is_dir()})
    if not skills:
        sys.exit(f"no evals/ dir matches {args.skill}")
    jobs = []
    for skill in skills:
        if not (root / skill / "SKILL.md").is_file():
            print(f"skip {skill}: no skills/{skill}/SKILL.md{' at ' + args.ref if args.ref else ''}", file=sys.stderr)
            continue
        found = []
        for f in sorted((REPO / "evals" / skill).glob("*evals.json")):
            if args.files and f.stem not in args.files:
                continue
            for ev in json.loads(f.read_text())["evals"]:
                if not args.ids or ev["id"] in args.ids:
                    found.append((skill, f.stem, ev))
        jobs += found[:1] if args.smoke else found
    return jobs * args.reps


def run_eval(args, skill, suite, ev, system, work):
    row = {"skill": skill, "file": suite, "id": ev["id"], "cost_usd": 0.0, "models": set()}
    try:
        fixtures = "".join(
            f"\n\n=== File: {f} ===\n```\n{(REPO / 'evals' / skill / f).read_text()}\n```" for f in ev.get("files", [])
        )
        output, cost, models = claude(f"{ev['prompt']}\n\nHere are the relevant files:{fixtures}\n\n{TASK}",
                                      system, args.model, args.effort, args.timeout, work)
        row["cost_usd"] += cost
        row["models"] |= models
        texts = [a["text"] if isinstance(a, dict) else a for a in ev["assertions"]]
        scoped = [scoped_output(output, t, "migration" in suite) for t in texts]
        results = [deterministic_check(s, t) for s, t in zip(scoped, texts)]
        pending = [i for i, r in enumerate(results) if r is None]
        if pending:
            # One judge call sees one output, so migration absence checks needing code-only scope are judged apart.
            groups = {}
            for i in pending:
                groups.setdefault(scoped[i], []).append(i)
            for scope, idx in groups.items():
                verdict, cost, models = claude(judge_prompt(scope, [texts[i] for i in idx]), work / "judge.system.md",
                                               args.judge_model, None, args.timeout, work)
                row["cost_usd"] += cost
                row["models"] |= models
                for i, v in zip(idx, parse_verdicts(verdict, len(idx))):
                    results[i] = v
    except Exception as e:  # noqa: BLE001
        return {**row, "error": str(e)[:300], "assertions": []}
    return {**row, "output": output, "assertions": [
        {"text": t, "pass": p, "reason": r} for t, (p, r) in zip(texts, results)
    ]}


def git(*a):
    return subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True).stdout.strip()


def summarize(rows, meta):
    lines = [f"model {meta['model']} (effort {meta['effort'] or 'default'}), judge {meta['judge_model']}, "
             f"resolved {', '.join(meta['models_used'])}, skills {meta['skills_ref']}{' (dirty)' if meta['dirty'] else ''}"]
    by_skill = {}
    for r in rows:
        by_skill.setdefault(r["skill"], []).append(r)
    for skill, rs in by_skill.items():
        p = sum(a["pass"] for r in rs for a in r["assertions"])
        t = sum(len(r["assertions"]) for r in rs)
        lines.append(f"\n{skill}: {p}/{t} across {len(rs)} evals, ${sum(r['cost_usd'] for r in rs):.2f}")
        for r in rs:
            if "error" in r:
                lines.append(f"  {r['file']}#{r['id']}: ERROR {r['error'][:120]}")
            for a in r["assertions"]:
                if not a["pass"]:
                    lines.append(f"  {r['file']}#{r['id']} x {a['text'][:90]}\n      {a['reason'][:140]}")
    p = sum(a["pass"] for r in rows for a in r["assertions"])
    t = sum(len(r["assertions"]) for r in rows)
    lines.append(f"\nOVERALL: {p}/{t} ({100 * p / max(t, 1):.0f}%), {sum('error' in r for r in rows)} errors, "
                 f"${meta['cost_usd']:.2f}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skill", action="append", required=True, help="evals/ dir name or glob; repeatable")
    ap.add_argument("--files", type=lambda s: s.split(","), help="eval file stems, e.g. integration-evals")
    ap.add_argument("--ids", type=lambda s: {int(i) for i in s.split(",")})
    ap.add_argument("--smoke", action="store_true", help="first eval of each skill only")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--ref", help="git ref to take skills/ from (evals stay at the working tree)")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--model", default="sonnet", help="model or alias; aliases follow the latest release")
    ap.add_argument("--effort", default="medium", help="generator effort; '' for the model default")
    ap.add_argument("--judge-model", default="opus")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = args.out or REPO / "eval-runs" / "assertion" / stamp
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="assertion-evals-") as tmp:
        work = Path(tmp)
        (work / "judge.system.md").write_text(JUDGE_SYSTEM)
        root = skills_root(args.ref, work)
        jobs = collect(args, root)
        systems = {s: system_file(root / s, work) for s in {j[0] for j in jobs}}
        print(f"{len(jobs)} evals, {args.model}, jobs={args.jobs}", flush=True)
        rows = []
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            futures = [pool.submit(run_eval, args, s, f, ev, systems[s], work) for s, f, ev in jobs]
            for fut in as_completed(futures):
                r = fut.result()
                r["models"] = sorted(r["models"])
                rows.append(r)
                ok = sum(a["pass"] for a in r["assertions"])
                print(f"  {r['skill']} {r['file']}#{r['id']}: {ok}/{len(r['assertions'])} "
                      f"${r['cost_usd']:.2f} {r.get('error', '')}", flush=True)
    rows.sort(key=lambda r: (r["skill"], r["file"], r["id"]))
    meta = {
        "generated_at": stamp, "model": args.model, "effort": args.effort, "judge_model": args.judge_model,
        "models_used": sorted({m for r in rows for m in r["models"]}),
        "skills_ref": args.ref or git("rev-parse", "--short", "HEAD"),
        "dirty": not args.ref and bool(git("status", "--porcelain", "skills", "evals")),
        "cost_usd": round(sum(r["cost_usd"] for r in rows), 4),
    }
    (out / "results.json").write_text(json.dumps({**meta, "rows": rows}, indent=1))
    summary = summarize(rows, meta)
    (out / "summary.txt").write_text(summary + "\n")
    print(f"\n{summary}\nResults: {out}")


if __name__ == "__main__":
    main()
