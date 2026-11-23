#!/usr/bin/env python3
"""Release-check: platform release notes vs skill dirs, and new releases between two docs commits.

Only ``--dry-run`` is implemented: it prints the platform/skill inventory as JSON and,
with ``--from``, the releases new since that docs commit with their items and sizing.
"""
import argparse
import functools
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from common import AUDITOR_ROOT, REPO_ROOT, list_skill_dirs


BYTES_PER_TOKEN = 4


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
        products, sections = registry["products"], registry["sections"]
        if not isinstance(products, dict) or not products or not all(
                v == "all" or (isinstance(v, list) and v and all(isinstance(p, str) and p for p in v))
                for v in products.values()):
            raise ValueError("'products' must map product names to \"all\" or a list of dir prefixes")
        if not isinstance(sections, list) or not sections \
                or not all(isinstance(s, str) and s for s in sections):
            raise ValueError("'sections' must be a non-empty list of section headings")
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
    try:
        if not skills_dir.is_dir():
            raise UsageError(f"--skills is not a directory: {skills_dir}")
        dirs = [d.name for d in list_skill_dirs(skills_dir)]
    except OSError as exc:
        raise UsageError(f"cannot list --skills {skills_dir}: {exc}")

    registered = {s for entry in platforms.values() for s in entry["skills"]} | set(not_assessed)
    missing = sorted(registered - set(dirs))
    if missing:
        raise UsageError(f"registry skills not a directory under {skills_dir}: {', '.join(missing)}")

    selected = {only: platforms[only]} if only else platforms
    out_platforms = []
    for key, entry in selected.items():
        try:
            notes_path = (docs_dir / entry["notes"]).resolve()
            if not notes_path.is_relative_to(docs_dir.resolve()):
                raise UsageError(f"notes file for {key} is outside --docs: {entry['notes']}")
            if not notes_path.is_file():
                raise UsageError(f"notes file for {key} missing: {notes_path}")
        except OSError as exc:
            raise UsageError(f"cannot check notes file for {key} under --docs {docs_dir}: {exc}")
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


RELEASE_HEADING = re.compile(r"^## (\d+\.\d+\.\d+)\s*$")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")


def resolve_ref(docs_dir: Path, ref: str) -> str:
    git = ["git", "-C", str(docs_dir), "rev-parse"]
    try:
        top = subprocess.run([*git, "--show-toplevel"], capture_output=True, text=True)
        proc = subprocess.run([*git, "--verify", "--quiet", f"{ref}^{{commit}}"], capture_output=True, text=True)
    except OSError as exc:
        raise UsageError(f"cannot run git: {exc}")
    if top.returncode != 0 or Path(top.stdout.strip()).resolve() != docs_dir.resolve():
        raise UsageError(f"--docs {docs_dir} is not the root of a git worktree")
    if proc.returncode != 0:
        raise UsageError(f"unknown commit {ref!r} in --docs {docs_dir}")
    return proc.stdout.strip()


def notes_at(docs_dir: Path, sha: str, rel: str) -> str:
    git = ["git", "-C", str(docs_dir)]
    try:
        if subprocess.run([*git, "rev-parse", "--verify", "--quiet", f"{sha}:{rel}"], capture_output=True).returncode != 0:
            return ""
        proc = subprocess.run([*git, "show", f"{sha}:{rel}"], capture_output=True)
    except OSError as exc:
        raise UsageError(f"cannot run git: {exc}")
    if proc.returncode != 0:
        raise UsageError(f"cannot read {rel} at {sha}: {proc.stderr.decode(errors='replace').strip()}")
    return proc.stdout.decode("utf-8", "replace")


def parse_releases(text: str, sections: list[str]) -> dict[str, list[dict]]:
    """Version -> kept items (section in ``sections``) of one notes file, in file order."""
    releases: dict[str, list[dict]] = {}
    version = section = product = item = None
    gap = False
    for line in text.splitlines():
        match = RELEASE_HEADING.match(line)
        if match:
            version, section, product, item = match.group(1), None, None, None
            releases.setdefault(version, [])
            continue
        heading = HEADING.match(line)
        if heading:
            item = None
            level, title = len(heading.group(1)), heading.group(2)
            if level <= 2:
                version = None
            elif level == 3:
                section, product = title, None
            elif level == 4:
                product = title
        elif version is None:
            continue
        elif line.startswith("* "):
            item = None
            if section in sections:
                item, gap = {"section": section, "product": product, "text": line[2:].rstrip()}, False
                releases[version].append(item)
        elif item is not None and not line.strip():
            gap = True
        elif item is not None and line[:1] in (" ", "\t"):
            item["text"] += ("\n\n" if gap else "\n") + line.strip()
            gap = False
        else:
            item = None
    return releases


def map_skills(product: str | None, platform_skills: list[str], products: dict) -> list[str]:
    rule = products.get(product) if product else None
    if rule == "all":
        return list(platform_skills)
    if isinstance(rule, list):
        return [s for s in platform_skills if s.startswith(tuple(rule))]
    return []


@functools.cache
def _one_skill_sizes(root: Path) -> tuple[int, ...]:
    def fail(exc: OSError):
        raise exc

    try:
        files = sorted(Path(d, f) for d, _, names in os.walk(root, onerror=fail) for f in names)
        return tuple(f.stat().st_size for f in files)
    except OSError as exc:
        raise UsageError(f"cannot read skill files under {root}: {exc}")


def skill_file_sizes(skills_dir: Path, skills: list[str]) -> list[int]:
    return [size for skill in sorted(skills) for size in _one_skill_sizes(skills_dir / skill)]


def plan_group(items_bytes: int, file_sizes: list[int], max_batch_bytes: int) -> tuple[int, int]:
    """(planned_calls, input_bytes) for one group: every batch carries all items plus a run of files."""
    batches = [0]
    for size in file_sizes:
        if batches[-1] and items_bytes + batches[-1] + size > max_batch_bytes:
            batches.append(0)
        batches[-1] += size
    return len(batches), sum(items_bytes + b for b in batches)


def platform_row(key: str, entries: list[dict], skills_dir: Path, max_batch_bytes: int) -> dict:
    groups: dict[str | None, list[dict]] = {}
    for entry in entries:
        if entry["skills"]:
            groups.setdefault(entry["product"], []).append(entry)
    calls = input_bytes = 0
    for group in groups.values():
        items_bytes = sum(len(e["text"].encode()) for e in group)
        group_calls, group_bytes = plan_group(
            items_bytes, skill_file_sizes(skills_dir, group[0]["skills"]), max_batch_bytes)
        calls += group_calls
        input_bytes += group_bytes
    mapped = sum(1 for e in entries if e["skills"])
    return {
        "key": key,
        "items": len(entries),
        "mapped": mapped,
        "no_skill": len(entries) - mapped,
        "skills": sorted({s for e in entries for s in e["skills"]}),
        "planned_calls": calls,
        "input_bytes": input_bytes,
        "estimated_tokens": input_bytes // BYTES_PER_TOKEN,
        "entries": entries,
    }


def new_releases(registry: dict, skills_dir: Path, docs_dir: Path, only: str | None,
                 from_sha: str, to_sha: str, max_batch_bytes: int) -> list[dict]:
    platforms = registry["platforms"]
    by_version: dict[str, list[dict]] = {}
    for key, entry in ({only: platforms[only]} if only else platforms).items():
        old = parse_releases(notes_at(docs_dir, from_sha, entry["notes"]), registry["sections"])
        new = parse_releases(notes_at(docs_dir, to_sha, entry["notes"]), registry["sections"])
        for version in new.keys() - old.keys():
            entries = [{
                "id": f"{key}/{version}/{n}",
                "section": item["section"],
                "product": item["product"],
                "text": item["text"],
                "skills": map_skills(item["product"], entry["skills"], registry["products"]),
            } for n, item in enumerate(new[version], 1)]
            by_version.setdefault(version, []).append(platform_row(key, entries, skills_dir, max_batch_bytes))
    releases = []
    for version in sorted(by_version, key=lambda v: tuple(map(int, v.split("."))), reverse=True):
        rows = by_version[version]
        totals = {name: sum(r[name] for r in rows)
                  for name in ("items", "mapped", "no_skill", "planned_calls", "input_bytes")}
        totals["estimated_tokens"] = totals["input_bytes"] // BYTES_PER_TOKEN
        releases.append({"version": version, "platforms": rows, "totals": totals})
    return releases


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--docs", type=Path, required=True, help="local clone of the documentation repo")
    ap.add_argument("--skills", type=Path, default=REPO_ROOT / "skills")
    ap.add_argument("--registry", type=Path, default=AUDITOR_ROOT / "accuracy" / "registry.json")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--platform")
    ap.add_argument("--from", dest="from_ref", help="older docs commit; lists the releases new since it")
    ap.add_argument("--to", dest="to_ref", help="newer docs commit (default HEAD); needs --from")
    ap.add_argument("--max-batch-bytes", type=int, default=400000)
    args = ap.parse_args()
    try:
        if not args.dry_run:
            raise UsageError("only --dry-run is implemented")
        if args.to_ref and not args.from_ref:
            raise UsageError("--to needs --from")
        if args.max_batch_bytes <= 0:
            raise UsageError("--max-batch-bytes must be positive")
        registry = load_registry(args.registry)
        result = inventory(registry, args.skills, args.docs, args.platform)
        if args.from_ref:
            result["from"] = resolve_ref(args.docs, args.from_ref)
            result["to"] = resolve_ref(args.docs, args.to_ref or "HEAD")
            result["releases"] = new_releases(registry, args.skills, args.docs, args.platform,
                                              result["from"], result["to"], args.max_batch_bytes)
    except UsageError as exc:
        print(f"accuracy_review: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
