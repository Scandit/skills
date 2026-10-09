#!/usr/bin/env python3
"""Render the third-party format -> Scandit symbology tables from mapping.json.

Usage:
    internal/symbology-map/generate.py          # rewrite every generated block
    internal/symbology-map/generate.py --check  # exit 1 if any block differs

A guide opts in with a marker pair; the generator owns everything between them:

    <!-- BEGIN GENERATED symbology-table sources=zxing,mlkit style=kotlin -->
    <!-- END GENERATED symbology-table -->

`sources` are keys of mapping.json `sources`, one table column each, in order;
a source with `rows_from` reuses another source's rows under its own label.
A format `note` is a string, or a {style: text} dict for style-specific notes.
`style` is kotlin, swift, dart, js or csharp. `namespace` (default `Symbology`)
prefixes the Scandit name, e.g. `namespace=Scandit.Symbology` for Cordova.
The BEGIN marker's indentation is applied to every generated line.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAPPING = Path(__file__).resolve().parent / "mapping.json"
GUIDE_GLOB = "skills/*/references/third-party-migration.md"
STYLES = ("kotlin", "swift", "dart", "js", "csharp")

BEGIN = re.compile(r"^(?P<indent>[ \t]*)<!-- BEGIN GENERATED symbology-table (?P<args>[^>]*?) -->$", re.M)
END = re.compile(r"^[ \t]*<!-- END GENERATED symbology-table -->$", re.M)


def guides(root: Path) -> list[Path]:
    return sorted(root.glob(GUIDE_GLOB))


def scandit_name(symbology: str, style: str, namespace: str, mapping: dict) -> str:
    member = mapping["symbologies"][symbology][style]
    return f"`.{member}`" if style == "swift" else f"`{namespace}.{member}`"


def source_cell(row) -> str:
    if row is None:
        return "—"
    if isinstance(row, list):
        row = {"names": row}
    cell = " / ".join(f"`{name}`" for name in row["names"])
    note = row.get("note")
    if note:
        cell = f"{cell} ({note})" if cell else f"({note})"
    return cell


def rows(source: str, mapping: dict) -> dict:
    entry = mapping["sources"][source]
    return mapping["sources"][entry["rows_from"]]["rows"] if "rows_from" in entry else entry["rows"]


def scandit_cell(fmt: dict, style: str, namespace: str, mapping: dict) -> str:
    note = fmt.get("note")
    if fmt["symbology"] is None:
        return fmt["note"]
    if isinstance(note, dict):
        note = note.get(style)
    name = scandit_name(fmt["symbology"], style, namespace, mapping)
    return f"{name} ({note})" if note else name


def table(args: dict, mapping: dict) -> list[str]:
    sources = args["sources"].split(",")
    style = args["style"]
    namespace = args.get("namespace", "Symbology")
    unknown = [s for s in sources if s not in mapping["sources"]]
    if unknown or style not in STYLES:
        raise ValueError(f"unknown source {unknown} or style {style!r}")
    columns = [rows(s, mapping) for s in sources]

    header = [mapping["sources"][s]["label"] for s in sources]
    header.append("Scandit `Symbology`" if style == "swift" else f"Scandit `{namespace}`")
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for key, fmt in mapping["formats"].items():
        if not any(key in c for c in columns):
            continue
        cells = [source_cell(c.get(key)) for c in columns]
        cells.append(scandit_cell(fmt, style, namespace, mapping))
        lines.append("| " + " | ".join(cells) + " |")

    defaults = ", ".join(scandit_name(s, style, namespace, mapping) for s in mapping["default_set"])
    lines += ["", f"**Recommended default set** when the source scanned every format and nothing in the app narrows it: {defaults}."]
    return lines


def render(text: str, mapping: dict) -> str:
    out, pos, blocks = [], 0, 0
    for begin in BEGIN.finditer(text):
        if begin.start() < pos:
            continue
        end = END.search(text, begin.end())
        if end is None:
            raise ValueError(f"BEGIN marker at offset {begin.start()} has no END marker")
        args = dict(token.split("=", 1) for token in begin["args"].split())
        indent = begin["indent"]
        body = "\n".join((indent + line).rstrip() for line in table(args, mapping))
        out += [text[pos:begin.end()], "\n", body, "\n"]
        pos = end.start()
        blocks += 1
    if text.count("GENERATED symbology-table") != 2 * blocks:
        raise ValueError("malformed or unpaired symbology-table marker")
    out.append(text[pos:])
    return "".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the symbology tables from mapping.json.")
    parser.add_argument("--check", action="store_true", help="exit 1 if a generated block is out of date")
    parser.add_argument("--root", type=Path, default=ROOT, help="repo root holding skills/ (default: this repo)")
    opts = parser.parse_args()

    mapping = json.loads(MAPPING.read_text())
    stale = []
    for guide in guides(opts.root):
        text = guide.read_text()
        try:
            new = render(text, mapping)
        except (ValueError, KeyError) as error:
            sys.exit(f"{guide.relative_to(opts.root)}: {error}")
        if new == text:
            continue
        stale.append(guide.relative_to(opts.root))
        if not opts.check:
            guide.write_text(new)

    if opts.check and stale:
        print("symbology tables out of date (run internal/symbology-map/generate.py):")
        for path in stale:
            print(f"  {path}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
