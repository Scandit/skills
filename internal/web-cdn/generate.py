#!/usr/bin/env python3
"""Render the plain-HTML CDN set-up of the web skills from cdn.json and fragments/.

Usage:
    internal/web-cdn/generate.py          # rewrite every generated block and SDK pin
    internal/web-cdn/generate.py --check  # exit 1 if any block or pin differs

A web skill file opts in with a marker pair; the generator owns everything between them:

    <!-- BEGIN GENERATED web-cdn packages=core,barcode engine=barcode -->
    <!-- END GENERATED web-cdn -->

`packages` are keys of cdn.json `packages` and must include `core`; `engine` is
the listed package whose `sdc-lib/` `libraryLocation` points at; `multithreading`
is `yes` (default) or `no`, which leaves out the check and its dialog. The block
is the fragments in FRAGMENTS order, with `{{name}}` placeholders filled in.
The BEGIN marker's indentation is applied to every generated line.

Outside the blocks, every `@scandit/web-datacapture-*@x.y.z` URL and every
backticked `@x.y.z` example in the .md files under skills/*-web is rewritten to
`sdk_version`, and --check verifies the same. Floating-major examples such as
`@8`, caret ranges and non-Markdown files are not covered.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONFIG = HERE / "cdn.json"
FRAGMENTS = HERE / "fragments"
FRAGMENT_ORDER = ("cdn-warning", "import-map", "headers", "serving", "multithreading", "umd")
OPTIONS = ("packages", "engine", "multithreading")
SKILL_GLOB = "skills/*-web/**/*.md"
JSDELIVR = "https://cdn.jsdelivr.net/npm"

BEGIN = re.compile(r"^(?P<indent>[ \t]*)<!-- BEGIN GENERATED web-cdn (?P<args>[^>]*?) -->$", re.M)
END = re.compile(r"^[ \t]*<!-- END GENERATED web-cdn -->$", re.M)
PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")
SCANDIT_PIN = re.compile(r"(@scandit/web-datacapture-[a-z]+@)\d+\.\d+\.\d+")
EXAMPLE_PIN = re.compile(r"`@\d+\.\d+\.\d+`")


def skill_files(root: Path) -> list[Path]:
    return sorted(root.glob(SKILL_GLOB))


def fill(template: str, values: dict[str, str]) -> str:
    def value(match: re.Match) -> str:
        if match[1] not in values:
            raise ValueError(f"unknown placeholder {match[0]}")
        line_start = template.rfind("\n", 0, match.start()) + 1
        indent = re.match(r"[ \t]*", template[line_start:])[0]
        return values[match[1]].replace("\n", "\n" + indent)

    return PLACEHOLDER.sub(value, template)


def options(args: str) -> dict[str, str]:
    pairs = [token.partition("=") for token in args.split()]
    malformed = [key for key, sep, value in pairs if not sep or not value]
    if malformed:
        raise ValueError(f"malformed marker option {malformed}")
    return {key: value for key, _, value in pairs}


def placeholders(listed: list[dict], engine: dict, config: dict) -> dict[str, str]:
    version = config["sdk_version"]
    base = {pkg["npm"]: f"{JSDELIVR}/{pkg['npm']}@{version}" for pkg in listed}
    entries = []
    for npm, url in base.items():
        entries += [f'"{npm}": "{url}/build/js/index.js"', f'"{npm}/": "{url}/"']
    return {
        "sdk_version": version,
        "sdk_major": version.split(".")[0],
        "serve_version": config["serve_version"],
        "es_module_shims_version": config["es_module_shims_version"],
        **{f"{name}_link": url for name, url in config["links"].items()},
        "import_map_entries": ",\n".join(entries),
        "library_location": f"{base[engine['npm']]}/sdc-lib/",
        "engine_npm": engine["npm"],
        "engine_loader": engine["loader"],
        "umd_scripts": "\n".join(f'<script src="{url}/build/js/umd/index.js"></script>' for url in base.values()),
        "umd_all_globals": ", ".join(f"`{pkg['global']}`" for pkg in config["packages"].values()),
        "umd_parser_npm": config["packages"]["parser"]["npm"],
        "umd_parser_global": config["packages"]["parser"]["global"],
        "umd_globals": "\n".join(
            f"- `{pkg['npm']}/build/js/umd/index.js` exposes exactly one global, `{pkg['global']}`." for pkg in listed
        ),
    }


def block(args: dict[str, str], config: dict) -> list[str]:
    packages = config["packages"]
    names = args.get("packages", "").split(",")
    engine = args.get("engine")
    multithreading = args.get("multithreading", "yes")
    unknown = sorted(set(args) - set(OPTIONS))
    if unknown:
        raise ValueError(f"unknown option {unknown}")
    if "core" not in names or not set(names) <= set(packages):
        raise ValueError(f"packages={args.get('packages')!r} must include core and only {sorted(packages)}")
    if engine not in names or "loader" not in packages[engine]:
        raise ValueError(f"engine={engine!r} must be a listed package that ships sdc-lib/")
    if multithreading not in ("yes", "no"):
        raise ValueError(f"multithreading={multithreading!r} must be yes or no")

    listed = [pkg for name, pkg in packages.items() if name in names]
    values = placeholders(listed, packages[engine], config)
    fragments = [f for f in FRAGMENT_ORDER if multithreading == "yes" or f != "multithreading"]
    text = "\n\n".join(fill((FRAGMENTS / f"{f}.md").read_text().strip("\n"), values) for f in fragments)
    return text.split("\n")


def rewrite_pins(text: str, version: str) -> str:
    text = SCANDIT_PIN.sub(rf"\g<1>{version}", text)
    return EXAMPLE_PIN.sub(f"`@{version}`", text)


def render(text: str, config: dict) -> str:
    out, pos, blocks = [], 0, 0
    for begin in BEGIN.finditer(text):
        if begin.start() < pos:
            continue
        end = END.search(text, begin.end())
        if end is None:
            raise ValueError(f"BEGIN marker at offset {begin.start()} has no END marker")
        indent = begin["indent"]
        body = "\n".join((indent + line).rstrip() for line in block(options(begin["args"]), config))
        out += [text[pos:begin.end()], "\n", body, "\n"]
        pos = end.start()
        blocks += 1
    if text.count("GENERATED web-cdn") != 2 * blocks:
        raise ValueError("malformed or unpaired web-cdn marker")
    out.append(text[pos:])
    return rewrite_pins("".join(out), config["sdk_version"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the web skills' CDN set-up from cdn.json.")
    parser.add_argument("--check", action="store_true", help="exit 1 if a generated block or SDK pin is out of date")
    parser.add_argument("--root", type=Path, default=ROOT, help="repo root holding skills/ (default: this repo)")
    parser.add_argument("--config", type=Path, default=CONFIG, help="source file (default: cdn.json next to this script)")
    opts = parser.parse_args()

    config = json.loads(opts.config.read_text())
    stale = []
    for path in skill_files(opts.root):
        text = path.read_text()
        try:
            new = render(text, config)
        except (ValueError, KeyError) as error:
            sys.exit(f"{path.relative_to(opts.root)}: {error}")
        if new == text:
            continue
        stale.append(path.relative_to(opts.root))
        if not opts.check:
            path.write_text(new)

    if opts.check and stale:
        print("web-cdn blocks or SDK pins out of date (run internal/web-cdn/generate.py):")
        for path in stale:
            print(f"  {path}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
