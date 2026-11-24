#!/usr/bin/env python3
"""Release-check: platform release notes vs skill dirs, and new releases between two docs commits.

``--dry-run`` prints the platform/skill inventory as JSON and, with ``--from``, the releases new
since that docs commit with their items and sizing. Without it, ``--from`` and ``--max-calls`` make
one ``claude -p`` call per planned batch and add each item's outcome and findings to the same JSON.
"""
import argparse
from collections import Counter
import functools
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TypeGuard

from common import AUDITOR_ROOT, REPO_ROOT, list_skill_dirs


BYTES_PER_TOKEN = 4
OUTCOMES = ("finding", "no-impact", "no-skill", "not-checked")


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


def notes_at(docs_dir: Path, sha: str, rel: str) -> str | None:
    """Notes text at ``sha``; None when the tree has no such path. A git read failure is a UsageError."""
    git = ["git", "-C", str(docs_dir)]
    try:
        proc = subprocess.run([*git, "ls-tree", "--name-only", sha, "--", rel], capture_output=True)
        if proc.returncode == 0 and not proc.stdout.strip():
            return None
        if proc.returncode == 0:
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


def visible(path: Path, root: Path) -> bool:
    """Inside ``root`` with no hidden component below it."""
    return path.is_relative_to(root) and not any(p.startswith(".") for p in path.relative_to(root).parts)


@functools.cache
def _one_skill_files(root: Path) -> tuple[tuple[Path, int], ...]:
    def fail(exc: OSError):
        raise exc

    try:
        real = root.resolve()
        if not real.is_relative_to(root.parent.resolve()):
            raise UsageError(f"skill directory {root} resolves outside {root.parent}")
        files = []
        for d, dirs, names in os.walk(root, onerror=fail):
            dirs[:] = [x for x in dirs if not x.startswith(".")]
            files += [f for n in names if visible((f := Path(d, n)).resolve(), real) and visible(f, root)]
        return tuple((f, f.stat().st_size) for f in sorted(files))
    except OSError as exc:
        raise UsageError(f"cannot read skill files under {root}: {exc}")


def skill_files(skills_dir: Path, skills: list[str]) -> list[tuple[Path, int]]:
    return [f for skill in sorted(skills) for f in _one_skill_files(skills_dir / skill)]


def plan_group(items_bytes: int, files: list[tuple[Path, int]], max_batch_bytes: int) -> list[list[tuple[Path, int]]]:
    """Batches of one group: every batch carries all items plus a run of files."""
    if not files:
        return []
    batches: list[list[tuple[Path, int]]] = [[]]
    used = 0
    for file in files:
        if batches[-1] and items_bytes + used + file[1] > max_batch_bytes:
            batches.append([])
            used = 0
        batches[-1].append(file)
        used += file[1]
    return batches


def group_entries(entries: list[dict]) -> list[list[dict]]:
    groups: dict[str | None, list[dict]] = {}
    for entry in entries:
        if entry["skills"]:
            groups.setdefault(entry["product"], []).append(entry)
    return list(groups.values())


def items_bytes_of(group: list[dict]) -> int:
    return sum(len(e["text"].encode()) for e in group)


def group_batches(group: list[dict], skills_dir: Path, max_batch_bytes: int) -> list[list[tuple[Path, int]]]:
    return plan_group(items_bytes_of(group), skill_files(skills_dir, group[0]["skills"]), max_batch_bytes)


def platform_row(version: str, key: str, entries: list[dict], skills_dir: Path, max_batch_bytes: int) -> dict:
    calls = input_bytes = prompt_tokens = 0
    for group in group_entries(entries):
        batches = group_batches(group, skills_dir, max_batch_bytes)
        calls += len(batches)
        input_bytes += sum(items_bytes_of(group) + sum(size for _, size in batch) for batch in batches)
        prompt_tokens += sum(prompt_tokens_of(build_prompt(version, key, group[0]["product"], group, batch,
                                                           skills_dir)[0]) for batch in batches)
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
        "prompt_tokens": prompt_tokens,
        "entries": entries,
    }


def new_releases(registry: dict, skills_dir: Path, docs_dir: Path, only: str | None,
                 from_sha: str, to_sha: str, max_batch_bytes: int) -> tuple[list[dict], list[str]]:
    """(releases, platforms whose notes file is absent at ``to_sha``)."""
    platforms = registry["platforms"]
    by_version: dict[str, list[dict]] = {}
    missing = []
    for key, entry in ({only: platforms[only]} if only else platforms).items():
        new_text = notes_at(docs_dir, to_sha, entry["notes"])
        if new_text is None:
            missing.append(key)
            continue
        old = parse_releases(notes_at(docs_dir, from_sha, entry["notes"]) or "", registry["sections"])
        new = parse_releases(new_text, registry["sections"])
        for version in new.keys() - old.keys():
            entries = [{
                "id": f"{key}/{version}/{n}",
                "section": item["section"],
                "product": item["product"],
                "text": item["text"],
                "skills": map_skills(item["product"], entry["skills"], registry["products"]),
            } for n, item in enumerate(new[version], 1)]
            by_version.setdefault(version, []).append(platform_row(version, key, entries, skills_dir,
                                                                       max_batch_bytes))
    releases = []
    for version in sorted(by_version, key=lambda v: tuple(map(int, v.split("."))), reverse=True):
        rows = by_version[version]
        totals = {name: sum(r[name] for r in rows)
                  for name in ("items", "mapped", "no_skill", "planned_calls", "input_bytes", "prompt_tokens")}
        totals["estimated_tokens"] = totals["input_bytes"] // BYTES_PER_TOKEN
        releases.append({"version": version, "platforms": rows, "totals": totals})
    return releases, missing


SYSTEM_PROMPT = """\
You check whether agent skills are still accurate for a new SDK release.
You get the release items of one platform and product, and the skill files that cover them, each
line numbered "<n>: <text>". For every item, report zero or more findings of two kinds:
- "outdated": the skill contradicts the release. Give the file path exactly as in its "=== path ===" header,
  the line number, and "quote": the exact text copied from that one line.
- "not-covered": a new thing this skill should mention. Give the skill directory name and why.
Every finding has a "confidence": "high", "medium" or "low". Report only what the items support.
Reply with JSON only, no prose, listing every item id exactly once:
{"items": [{"id": "<item id>", "findings": [
  {"kind": "outdated", "path": "<path>", "line": <n>, "quote": "<text>", "why": "<reason>", "confidence": "high"},
  {"kind": "not-covered", "skill": "<skill>", "why": "<reason>", "confidence": "medium"}]}]}
"""


@functools.cache
def read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(errors="replace").splitlines()
    except OSError as exc:
        raise UsageError(f"cannot read skill file {path}: {exc}")


def prompt_tokens_of(user: str) -> int:
    """The estimate the --max-input-tokens check uses for one call."""
    return len((SYSTEM_PROMPT + user).encode()) // BYTES_PER_TOKEN


def build_prompt(version: str, platform: str, product: str | None, group: list[dict],
                 batch: list[tuple[Path, int]], skills_dir: Path) -> tuple[str, dict[str, list[str]]]:
    files = {path.relative_to(skills_dir).as_posix(): read_lines(path) for path, _ in batch}
    parts = [f"Release {version}, platform {platform}, product {product}\n\n## Release items\n"]
    parts += [f"### {e['id']} [{e['section']}]\n{e['text']}\n" for e in group]
    parts.append("\n## Skill files\n")
    for rel, lines in files.items():
        parts.append(f"=== {rel} ===\n" + "\n".join(f"{n}: {text}" for n, text in enumerate(lines, 1)) + "\n")
    return "\n".join(parts), files


class BatchFailure(Exception):
    """A call or reply that cannot be used; ``cost`` is what the call reported spending, None if unknown."""

    def __init__(self, message: str, cost: float | None = 0.0):
        super().__init__(message)
        self.cost = cost


def number(value) -> TypeGuard[int | float]:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


CONFIDENCES = ("high", "medium", "low")
FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.S)


def claude_bin() -> str:
    return os.environ.get("CLAUDE", "claude")


def call_claude(user: str, system_file: Path, model: str, timeout: int) -> tuple[str, int | None, float | None]:
    """(reply text, reported input tokens or None, reported cost or None); raises BatchFailure."""
    cmd = [claude_bin(), "-p", "--output-format", "json", "--model", model,
           "--system-prompt-file", str(system_file), "--tools", "", "--setting-sources", "",
           "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"]
    try:
        proc = subprocess.run(cmd, input=user, capture_output=True, text=True, timeout=timeout)
    except OSError as exc:
        raise BatchFailure(f"call failed: {exc!r}"[:300])
    except subprocess.TimeoutExpired:
        raise BatchFailure(f"call failed: timed out after {timeout}s", None)
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        data = None
    if proc.returncode or not isinstance(data, dict) or data.get("is_error") \
            or not isinstance(data.get("result"), str):
        spent = data.get("total_cost_usd") if isinstance(data, dict) else None
        raise BatchFailure(f"call failed: exit {proc.returncode} {(proc.stderr or proc.stdout)[-200:]}",
                           float(spent) if number(spent) else None)
    cost = data.get("total_cost_usd")
    if cost is not None and not number(cost):
        raise BatchFailure(f"invalid reply: total_cost_usd {cost!r}"[:300], None)
    usage = data.get("usage")
    tokens = None
    if isinstance(usage, dict) and "input_tokens" in usage:
        counts = [usage.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")]
        if not all(number(c) and isinstance(c, int) for c in counts):
            raise BatchFailure(f"invalid reply: usage {usage!r}"[:300], None if cost is None else float(cost))
        tokens = sum(counts)
    return data["result"], tokens, None if cost is None else float(cost)


def files_skills(files: dict[str, list[str]]) -> set[str]:
    return {rel.split("/")[0] for rel in files}


def check_finding(finding, files: dict[str, list[str]], complete: set[str]) -> dict | None:
    """The validated finding; None for a not-covered claim on a skill only partly in this batch."""
    if not isinstance(finding, dict) or not isinstance(finding.get("why"), str) \
            or finding.get("confidence") not in CONFIDENCES:
        raise BatchFailure(f"invalid reply: bad finding {finding!r}"[:300])
    kind = finding.get("kind")
    base = {"kind": kind, "why": finding["why"], "confidence": finding["confidence"]}
    if kind == "not-covered":
        skill = finding.get("skill")
        if not isinstance(skill, str) or skill not in files_skills(files):
            raise BatchFailure(f"invalid reply: skill {skill!r} is not in this batch")
        return {**base, "skill": skill} if skill in complete else None
    if kind != "outdated":
        raise BatchFailure(f"invalid reply: unknown finding kind {kind!r}")
    path, line, quote = finding.get("path"), finding.get("line"), finding.get("quote")
    lines = files.get(path) if isinstance(path, str) else None
    if lines is None:
        raise BatchFailure(f"invalid reply: path {path!r} is not a file of this batch")
    if not isinstance(line, int) or isinstance(line, bool) or not 1 <= line <= len(lines) \
            or not isinstance(quote, str) or not quote or quote not in lines[line - 1]:
        raise BatchFailure(f"invalid reply: quote {quote!r} not found at {path}:{line}")
    return {**base, "path": path, "line": line, "quote": quote}


def parse_reply(text: str, ids: list[str], files: dict[str, list[str]],
                complete: set[str]) -> dict[str, list[dict]]:
    """Item id -> findings for one batch; raises BatchFailure on anything off-schema."""
    fence = FENCE.fullmatch(text.strip())
    try:
        data = json.loads(fence.group(1) if fence else text)
    except ValueError:
        raise BatchFailure("invalid reply: not JSON")
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise BatchFailure("invalid reply: no 'items' list")
    found: dict[str, list[dict]] = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) \
                or not isinstance(item.get("findings"), list):
            raise BatchFailure(f"invalid reply: bad item {item!r}"[:300])
        if item["id"] not in ids:
            raise BatchFailure(f"invalid reply: unknown item id {item['id']!r}")
        if item["id"] in found:
            raise BatchFailure(f"invalid reply: duplicate item id {item['id']!r}")
        checked = [check_finding(f, files, complete) for f in item["findings"]]
        found[item["id"]] = [f for f in checked if f]
    missing = [i for i in ids if i not in found]
    if missing:
        raise BatchFailure(f"invalid reply: missing item ids {', '.join(missing)}")
    return found


class Budget:
    def __init__(self, max_calls: int, max_tokens: int | None, max_cost: float | None):
        self.max_calls, self.max_tokens, self.max_cost = max_calls, max_tokens, max_cost
        self.calls = self.tokens = self.unknown_cost_calls = 0
        self.cost = 0.0

    def limit(self, estimated_tokens: int) -> str | None:
        """The limit that forbids one more call of ``estimated_tokens``, if any."""
        if self.calls + 1 > self.max_calls:
            return "max-calls"
        if self.max_tokens is not None and self.tokens + estimated_tokens > self.max_tokens:
            return "max-input-tokens"
        if self.max_cost is not None and self.unknown_cost_calls:
            return "max-cost-usd (a call's spend is unknown)"
        if self.max_cost is not None and self.cost >= self.max_cost:
            return "max-cost-usd"
        return None


def whole_skills(batch: list[tuple[Path, int]], skills: list[str], skills_dir: Path) -> set[str]:
    present = Counter(path.relative_to(skills_dir).parts[0] for path, _ in batch)
    return {s for s in skills if present[s] and present[s] == len(_one_skill_files(skills_dir / s))}


def check_batch(user: str, ids: list[str], files: dict[str, list[str]], complete: set[str],
                system_file: Path, args, budget: Budget) -> tuple[dict[str, list[dict]] | None, str | None, bool]:
    """(findings by item id, None, False), or (None, why the batch is not-checked, whether a limit stops the run);
    one retry, budget checked each call."""
    estimate = prompt_tokens_of(user)
    reason = ""
    for _ in range(2):
        limit = budget.limit(estimate)
        if limit:
            return None, f"limit: {limit}", True
        budget.calls += 1
        try:
            text, tokens, cost = call_claude(user, system_file, args.model, args.timeout)
            if cost is None:
                budget.unknown_cost_calls += 1
        except BatchFailure as exc:
            budget.tokens += estimate
            if exc.cost is None:
                budget.unknown_cost_calls += 1
            else:
                budget.cost += exc.cost
            reason = str(exc)
            continue
        budget.tokens += estimate if tokens is None else tokens
        budget.cost += cost or 0.0
        try:
            return parse_reply(text, ids, files, complete), None, False
        except BatchFailure as exc:
            reason = str(exc)
    return None, reason, False


def settle(entries: list[dict], failed: dict[str, str], partial: dict[str, str]) -> dict[str, int]:
    for entry in entries:
        if not entry["skills"]:
            entry["outcome"] = "no-skill"
        elif entry["id"] in failed and not entry["findings"]:
            entry.update(outcome="not-checked", reason=failed[entry["id"]])
        else:
            entry["outcome"] = "finding" if entry["findings"] else "no-impact"
            incomplete = failed.get(entry["id"]) or partial.get(entry["id"])
            if incomplete:
                entry["incomplete"] = incomplete
    return {o: sum(e["outcome"] == o for e in entries) for o in OUTCOMES}


def run_batches(releases: list[dict], skills_dir: Path, args) -> dict:
    claude = claude_bin()
    if shutil.which(claude) is None:
        raise UsageError(f"claude binary not found: {claude} (set CLAUDE)")
    budget = Budget(args.max_calls, args.max_input_tokens, args.max_cost_usd)
    stopped = None
    with tempfile.TemporaryDirectory() as tmp:
        system_file = Path(tmp, "system.md")
        system_file.write_text(SYSTEM_PROMPT)
        for release in releases:
            for row in release["platforms"]:
                for group in group_entries(row["entries"]):
                    for path, _ in skill_files(skills_dir, group[0]["skills"]):
                        read_lines(path)
        for release in releases:
            for row in release["platforms"]:
                failed: dict[str, str] = {}
                partial: dict[str, str] = {}
                for entry in row["entries"]:
                    entry["findings"] = []
                for group in group_entries(row["entries"]):
                    ids = [e["id"] for e in group]
                    by_id = {e["id"]: e for e in group}
                    split: set[str] = set()
                    for batch in group_batches(group, skills_dir, args.max_batch_bytes):
                        if stopped:
                            failed.update({i: stopped for i in ids})
                            continue
                        user, files = build_prompt(release["version"], row["key"], group[0]["product"],
                                                   group, batch, skills_dir)
                        complete = whole_skills(batch, group[0]["skills"], skills_dir)
                        split |= files_skills(files) - complete
                        findings, reason, stops = check_batch(user, ids, files, complete, system_file, args,
                                                              budget)
                        for item_id, found in (findings or {}).items():
                            by_id[item_id]["findings"] += found
                        if reason:
                            failed.update({i: reason for i in ids})
                            stopped = reason if stops else None
                    if split:
                        note = f"not-covered unchecked, skill split across batches: {', '.join(sorted(split))}"
                        partial.update({i: note for i in ids})
                    empty = sorted(s for s in group[0]["skills"] if not _one_skill_files(skills_dir / s))
                    if empty:
                        note = f"no skill files: {', '.join(empty)}"
                        (failed if len(empty) == len(group[0]["skills"]) else partial).update({i: note for i in ids})
                row["outcomes"] = settle(row["entries"], failed, partial)
    return {"calls": budget.calls, "input_tokens": budget.tokens, "cost_usd": budget.cost,
            "unknown_cost_calls": budget.unknown_cost_calls}


INPUT_USD_PER_MTOK = {"haiku": 1, "sonnet": 3, "opus": 5}


def usage_block(result: dict, usage: dict | None, model: str) -> dict:
    """Usage for the report: a real run's spend is labelled actual only on an API key, a dry run's is an estimate."""
    if usage is None:
        rows = [r for release in result["releases"] for r in release["platforms"]]
        tokens = sum(r["prompt_tokens"] for r in rows)
        price = next((p for name, p in INPUT_USD_PER_MTOK.items() if name in model), None)
        return {"calls": sum(r["planned_calls"] for r in rows), "input_tokens": tokens,
                "cost_usd": None if price is None else tokens * price / 1_000_000,
                "cost_label": "unavailable" if price is None else "estimated", "unknown_cost_calls": 0}
    known = bool(os.environ.get("ANTHROPIC_API_KEY")) and not usage["unknown_cost_calls"]
    return {**usage, "cost_usd": usage["cost_usd"] if known else None,
            "cost_label": "actual" if known else "unavailable"}


def platform_report(row: dict) -> dict:
    buckets: dict[str, list] = {outcome: [] for outcome in OUTCOMES}
    partial = []
    for entry in row["entries"]:
        outcome = entry.get("outcome") or ("not-checked" if entry["skills"] else "no-skill")
        item = {k: entry[k] for k in ("id", "section", "product", "text")}
        if outcome == "finding":
            item["findings"] = entry["findings"]
        elif outcome == "not-checked":
            item["reason"] = entry.get("reason", "dry run")
        buckets[outcome].append(item)
        if entry.get("incomplete"):
            partial.append({"id": entry["id"], "reason": entry["incomplete"]})
    checked = len(buckets["finding"]) + len(buckets["no-impact"])
    kept = len(row["entries"])
    complete = checked == kept - len(buckets["no-skill"]) and not partial
    return {
        "key": row["key"],
        "coverage": {"kept": kept, "checked": checked, "complete": complete},
        "outcomes": {outcome: len(items) for outcome, items in buckets.items()},
        "findings": buckets["finding"],
        "no_impact": [item["id"] for item in buckets["no-impact"]],
        "no_skill": buckets["no-skill"],
        "not_checked": buckets["not-checked"],
        "partial": partial,
    }


def build_report(result: dict, usage: dict) -> dict:
    return {
        "from": result["from"], "to": result["to"],
        "releases": [{"version": r["version"], "platforms": [platform_report(p) for p in r["platforms"]]}
                     for r in result["releases"]],
        "missing_notes": result["missing_notes"],
        "usage": usage,
    }


def one_line(text: str) -> str:
    return " ".join(text.replace("`", "").split())


def finding_line(finding: dict, item_id: str) -> str:
    why = one_line(finding["why"])
    if finding["kind"] == "outdated":
        where = f"`{one_line(finding['path'])}:{finding['line']}`"
        return f"{where} ({finding['confidence']}) “{one_line(finding['quote'])}” — {why} [{item_id}]"
    return f"{finding['skill']} ({finding['confidence']}) — {why} [{item_id}]"


def render_digest(report: dict) -> str:
    blocks = []
    for release in report["releases"]:
        platforms = release["platforms"]
        lines = [f"*Release {release['version']}*"]
        for platform in platforms:
            if platform["findings"]:
                lines.append(f"*{platform['key']}*")
                lines += [f"• {finding_line(f, item['id'])}"
                          for item in platform["findings"] for f in item["findings"]]
        counts = (f"No skill: {sum(len(p['no_skill']) for p in platforms)}"
                  f" · Not checked: {sum(len(p['not_checked']) for p in platforms)}")
        for platform in platforms:
            cov = platform["coverage"]
            if not cov["complete"]:
                counts += f" · {platform['key']} checked {cov['checked']} of {cov['kept']}"
                if platform["partial"]:
                    counts += f", partly checked {len(platform['partial'])}"
        blocks.append("\n".join([*lines, counts]))
    if report["missing_notes"]:
        blocks.append(f"Release notes missing for: {', '.join(report['missing_notes'])}")
    text = "\n\n".join(blocks) + "\n"
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_markdown(report: dict) -> str:
    usage = report["usage"]
    cost = "n/a" if usage["cost_usd"] is None else f"${usage['cost_usd']:.4f}"
    lines = ["# Skill accuracy review", "", f"From `{report['from']}` to `{report['to']}`", "",
             f"Usage: {usage['calls']} calls, {usage['input_tokens']} input tokens, "
             f"cost {cost} ({usage['cost_label']}), "
             f"{usage['unknown_cost_calls']} calls with unknown cost"]
    if report["missing_notes"]:
        lines += ["", f"Release notes missing for: {', '.join(report['missing_notes'])}"]
    if not report["releases"]:
        lines += ["", "No new releases."]
    for release in report["releases"]:
        lines += ["", f"## Release {release['version']}"]
        for platform in release["platforms"]:
            cov, counts = platform["coverage"], platform["outcomes"]
            state = "complete" if cov["complete"] else "INCOMPLETE"
            lines += ["", f"### {platform['key']}", "",
                      f"Checked {cov['checked']} of {cov['kept']} items ({state}). Findings: {counts['finding']},"
                      f" no impact: {counts['no-impact']}, no skill: {counts['no-skill']},"
                      f" not checked: {counts['not-checked']}."]
            for item in platform["findings"]:
                lines += ["", f"- `{item['id']}` ({item['section']}, {item['product']}): {one_line(item['text'])}"]
                lines += [f"  - {finding_line(f, item['id'])}" for f in item["findings"]]
            if platform["no_skill"]:
                lines += ["", "No skill:"] + [f"- `{i['id']}`: {one_line(i['text'])}" for i in platform["no_skill"]]
            if platform["not_checked"]:
                lines += ["", "Not checked:"] + [f"- `{i['id']}`: {i['reason']}" for i in platform["not_checked"]]
            if platform["partial"]:
                lines += ["", "Partly checked:"] + [f"- `{i['id']}`: {i['reason']}" for i in platform["partial"]]
            if platform["no_impact"]:
                lines += ["", "No impact: " + ", ".join(f"`{i}`" for i in platform["no_impact"])]
    return "\n".join(lines) + "\n"


def make_out_dir(out_dir: Path) -> None:
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise UsageError(f"cannot create --out {out_dir}: {exc}")


def write_reports(out_dir: Path, report: dict) -> None:
    files = {"report.json": json.dumps(report, indent=2) + "\n", "report.md": render_markdown(report)}
    if report["releases"]:
        files["digest.md"] = render_digest(report)
    try:
        for name, text in files.items():
            (out_dir / f"{name}.tmp").write_text(text, encoding="utf-8")
        for name in files:
            (out_dir / f"{name}.tmp").replace(out_dir / name)
        if "digest.md" not in files:
            (out_dir / "digest.md").unlink(missing_ok=True)
    except OSError as exc:
        raise UsageError(f"cannot write reports to {out_dir}: {exc}")


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
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--max-calls", type=int, help="required for a real run")
    ap.add_argument("--max-input-tokens", type=int,
                    help="checked before each call against a bytes/4 estimate; the last call may overshoot")
    ap.add_argument("--max-cost-usd", type=float,
                    help="checked before each call; the last call may overshoot; a timed-out call stops the run")
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "eval-runs" / "accuracy-review",
                    help="directory for report.json, report.md and digest.md; written whenever --from is given")
    ap.add_argument("--timeout", type=int, default=600, help="seconds per call")
    args = ap.parse_args()
    try:
        if not args.dry_run:
            if args.max_calls is None or args.max_calls < 1:
                raise UsageError("a real run needs --max-calls (a positive number)")
            if any(v is not None and not (math.isfinite(v) and v > 0) for v in (args.max_input_tokens, args.max_cost_usd)):
                raise UsageError("--max-input-tokens and --max-cost-usd must be finite and positive")
            if not args.from_ref:
                raise UsageError("a real run needs --from")
        if args.to_ref and not args.from_ref:
            raise UsageError("--to needs --from")
        if args.max_batch_bytes <= 0:
            raise UsageError("--max-batch-bytes must be positive")
        registry = load_registry(args.registry)
        result = inventory(registry, args.skills, args.docs, args.platform)
        if args.from_ref:
            result["from"] = resolve_ref(args.docs, args.from_ref)
            result["to"] = resolve_ref(args.docs, args.to_ref or "HEAD")
            make_out_dir(args.out)
            result["releases"], result["missing_notes"] = new_releases(registry, args.skills, args.docs, args.platform,
                                              result["from"], result["to"], args.max_batch_bytes)
            if not args.dry_run:
                result["usage"] = run_batches(result["releases"], args.skills, args)
    except UsageError as exc:
        print(f"accuracy_review: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    if args.from_ref:
        try:
            write_reports(args.out, build_report(result, usage_block(result, result.get("usage"), args.model)))
        except UsageError as exc:
            print(f"accuracy_review: {exc}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
