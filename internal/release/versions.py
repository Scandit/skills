#!/usr/bin/env python3
"""Keep one release version across every plugin and marketplace manifest.

Usage:
    internal/release/versions.py check               # all versions equal
    internal/release/versions.py check --tag v1.2.0  # ...and equal the tag
    internal/release/versions.py set 1.2.0           # bump every manifest

A plugin entry inside a marketplace must not carry its own `version`: Claude
Code prefers plugin.json without warning, so a second copy only goes stale.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PLUGIN_MANIFESTS = (
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
    ".cursor-plugin/plugin.json",
    ".github/plugin/plugin.json",
)
MARKETPLACES = (
    ".claude-plugin/marketplace.json",
    ".cursor-plugin/marketplace.json",
    ".github/plugin/marketplace.json",
    ".agents/plugins/marketplace.json",
)
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
VERSION_LINE_RE = re.compile(r'("version"\s*:\s*")([^"]*)(")')


def collect(root: Path) -> tuple[dict[str, str], list[str]]:
    """Return {location: version} and the problems found while reading."""
    versions: dict[str, str] = {}
    problems: list[str] = []
    for rel in PLUGIN_MANIFESTS:
        data = json.loads((root / rel).read_text())
        if "version" not in data:
            problems.append(f"{rel}: no version")
        else:
            versions[rel] = data["version"]
    for rel in MARKETPLACES:
        data = json.loads((root / rel).read_text())
        if "version" in data.get("metadata", {}):
            versions[f"{rel} metadata"] = data["metadata"]["version"]
        for entry in data.get("plugins", []):
            if "version" in entry:
                problems.append(f"{rel}: plugin entry {entry.get('name')!r} sets version; keep it in plugin.json only")
    return versions, problems


def check(root: Path, tag: str | None) -> list[str]:
    versions, problems = collect(root)
    for where, value in versions.items():
        if not SEMVER_RE.match(str(value)):
            problems.append(f"{where}: {value!r} is not MAJOR.MINOR.PATCH")
    distinct = sorted(set(versions.values()))
    if len(distinct) > 1:
        listing = ", ".join(f"{w}={v}" for w, v in versions.items())
        problems.append(f"versions differ: {listing}")
    if tag is not None and distinct and f"v{distinct[0]}" != tag:
        problems.append(f"tag {tag} does not match manifest version {distinct[0]}")
    return problems


def set_version(root: Path, new: str) -> list[str]:
    if not SEMVER_RE.match(new):
        return [f"{new!r} is not MAJOR.MINOR.PATCH"]
    _, problems = collect(root)
    if problems:
        return problems
    for rel in PLUGIN_MANIFESTS + MARKETPLACES:
        path = root / rel
        text = path.read_text()
        path.write_text(VERSION_LINE_RE.sub(lambda m: m.group(1) + new + m.group(3), text))
    return check(root, None)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_check = sub.add_parser("check", help="fail unless every manifest carries the same version")
    p_check.add_argument("--tag", help="release tag the version must match, e.g. v1.2.0")
    p_set = sub.add_parser("set", help="write one version into every manifest")
    p_set.add_argument("version")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    problems = check(args.root, args.tag) if args.cmd == "check" else set_version(args.root, args.version)
    for problem in problems:
        print(f"error: {problem}", file=sys.stderr)
    if not problems:
        versions, _ = collect(args.root)
        print(f"plugin version {next(iter(versions.values()))} in {len(versions)} places")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
