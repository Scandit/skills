"""Shared helpers for the skill-auditor scripts."""
import json
import re
from pathlib import Path
from typing import Any

AUDITOR_ROOT = Path(__file__).resolve().parents[1]  # internal/skill-auditor
REPO_ROOT = AUDITOR_ROOT.parents[1]


def load_manifest() -> dict:
    """Product/repo knowledge shared by all auditor scripts (kept as data, not code)."""
    return json.loads((AUDITOR_ROOT / "manifest.json").read_text())


def list_skill_dirs(skills_root: Path, prefix: str | None = None,
                    exclude: "frozenset[str] | set[str]" = frozenset()) -> list[Path]:
    return sorted(
        d for d in skills_root.iterdir()
        if d.is_dir() and d.name not in exclude
        and (not prefix or d.name.startswith(prefix))
    )


def _fold_block(block: list[str], literal: bool) -> str:
    """Fold the continuation lines of a YAML block scalar into a single string.

    `literal` (``|``) joins lines with newlines; folded (``>``) collapses single
    line breaks between non-empty lines into spaces and blank lines into newlines.
    """
    non_empty = [b for b in block if b.strip()]
    common = min((len(b) - len(b.lstrip()) for b in non_empty), default=0)
    content = [b[common:] if b.strip() else "" for b in block]
    if literal:
        return "\n".join(content).strip()
    out: list[str] = []
    for ln in content:
        if ln == "":
            out.append("\n")
        elif out and out[-1] != "\n":
            out.append(" " + ln)
        else:
            out.append(ln)
    return "".join(out).strip()


def frontmatter(path: Path) -> dict:
    """Parse SKILL.md YAML frontmatter into a flat dict (metadata children flattened).

    Handles block scalars (``key: >`` / ``key: |`` with an optional ``-``/``+``
    chomping indicator): their indented continuation lines are folded into the
    value, so length/name checks see the real text rather than the ``>-`` indicator.
    """
    m = re.match(r"^---\n(.*?)\n---", path.read_text(), re.S)
    fm: dict = {}
    if not m:
        return fm
    lines = m.group(1).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if ":" not in line:
            continue
        indent = len(line) - len(line.lstrip())
        k, _, v = line.strip().partition(":")
        v = v.strip()
        if v[:1] in ("|", ">"):
            literal = v[0] == "|"
            block: list[str] = []
            while i < len(lines):
                nxt = lines[i]
                if nxt.strip() and (len(nxt) - len(nxt.lstrip())) <= indent:
                    break
                block.append(nxt)
                i += 1
            v = _fold_block(block, literal)
        fm[k.strip()] = v.strip('"')
    return fm


def load_taxonomy(path: Path) -> dict:
    """Load a taxonomy YAML. Uses PyYAML when available; otherwise falls back to a
    minimal parser for the constrained flat schema documented in references/."""
    try:
        import yaml  # type: ignore
        return yaml.safe_load(path.read_text())
    except ImportError:
        pass
    tax: dict[str, Any] = {"features": []}
    feat = None
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" ") and not line.startswith("-"):
            key, _, val = line.partition(":")
            if key.strip() != "features":
                tax[key.strip()] = val.strip()
        elif line.strip().startswith("- id:"):
            feat = {"id": line.split("id:", 1)[1].strip(), "match": [], "required": False}
            tax["features"].append(feat)
        elif feat is not None:
            stripped = line.strip()
            if stripped.startswith("required:"):
                feat["required"] = "true" in stripped
            elif stripped.startswith("match:"):
                items = re.findall(r'"((?:[^"\\]|\\.)*)"', stripped)
                feat["match"] = [i.replace("\\\\", "\\") for i in items]
            elif stripped.startswith("excluded_platforms:"):
                feat["excluded_platforms"] = re.findall(r"[\w-]+", stripped.split(":", 1)[1])
    return tax
