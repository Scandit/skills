#!/usr/bin/env python3
"""Release-check inventory: which platform release notes cover which skill dirs.

Only ``--dry-run`` is implemented: it prints the platform/skill inventory as JSON.
"""
import argparse
import json
import sys
from pathlib import Path

from common import AUDITOR_ROOT, REPO_ROOT, list_skill_dirs


class UsageError(Exception):
    pass


def load_registry(path: Path) -> dict:
    try:
        registry = json.loads(path.read_text())
        platforms, not_assessed = registry["platforms"], registry["not_assessed"]
        for key, entry in platforms.items():
            skills = entry["skills"]
            if not isinstance(entry["notes"], str) or not isinstance(skills, list) \
                    or not all(isinstance(s, str) for s in skills):
                raise ValueError(f"platform {key!r} needs a string 'notes' and a list of names 'skills'")
        if not isinstance(not_assessed, dict) or not all(isinstance(v, str) for v in not_assessed.values()):
            raise ValueError("'not_assessed' must map skill names to reasons")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise UsageError(f"invalid registry {path}: {exc!r}")
    overlap = sorted(set(not_assessed) & {s for e in platforms.values() for s in e["skills"]})
    if overlap:
        raise UsageError(f"registry skills both mapped and not-assessed: {', '.join(overlap)}")
    return registry


def inventory(registry: dict, skills_dir: Path, docs_dir: Path, only: str | None) -> dict:
    platforms = registry["platforms"]
    not_assessed = registry["not_assessed"]
    if only is not None and only not in platforms:
        raise UsageError(f"unknown platform {only!r}; known: {', '.join(platforms)}")
    if not skills_dir.is_dir():
        raise UsageError(f"--skills is not a directory: {skills_dir}")
    dirs = [d.name for d in list_skill_dirs(skills_dir)]

    registered = {s for entry in platforms.values() for s in entry["skills"]} | set(not_assessed)
    missing = sorted(registered - set(dirs))
    if missing:
        raise UsageError(f"registry skills not a directory under {skills_dir}: {', '.join(missing)}")

    selected = {only: platforms[only]} if only else platforms
    out_platforms = []
    for key, entry in selected.items():
        notes_path = docs_dir / entry["notes"]
        if not notes_path.is_file():
            raise UsageError(f"notes file for {key} missing: {notes_path}")
        out_platforms.append({
            "key": key,
            "notes": entry["notes"],
            "skills": entry["skills"],
            "status": "ok" if entry["skills"] else "gap",
        })

    out_skills = []
    for name in dirs:
        owners = [k for k, e in platforms.items() if name in e["skills"]]
        row = {"dir": name, "platforms": owners}
        if name in not_assessed:
            row.update(status="not-assessed", reason=not_assessed[name])
        else:
            row["status"] = "mapped" if owners else "gap"
        out_skills.append(row)
    return {"platforms": out_platforms, "skills": out_skills}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--docs", type=Path, required=True, help="local clone of the documentation repo")
    ap.add_argument("--skills", type=Path, default=REPO_ROOT / "skills")
    ap.add_argument("--registry", type=Path, default=AUDITOR_ROOT / "accuracy" / "registry.json")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--platform")
    args = ap.parse_args()
    try:
        if not args.dry_run:
            raise UsageError("only --dry-run is implemented")
        registry = load_registry(args.registry)
        result = inventory(registry, args.skills, args.docs, args.platform)
    except UsageError as exc:
        print(f"accuracy_review: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
