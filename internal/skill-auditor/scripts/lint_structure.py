#!/usr/bin/env python3
"""Deterministic structure linter for the Scandit skill repo.

Usage: python3 lint_structure.py [--prefix sparkscan-] [--repo-root PATH]

Checks (per skill, and across siblings sharing a product prefix):
  frontmatter   name matches directory, description present, license, author, version
  layout        every sibling has the same reference files and eval suite files
  routing       every skills/<dir> is referenced in the router skill's SKILL.md and vice versa

Product prefixes and parity exemptions live in ../manifest.json, not in code.
Exit code 1 on any finding, so it can run as a CI gate.
"""
import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import REPO_ROOT, frontmatter, list_skill_dirs, load_manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", help="only lint skills with this prefix")
    ap.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = ap.parse_args()

    manifest = load_manifest()
    prefixes: list[str] = manifest["product_prefixes"]
    parity_exempt: set[str] = set(manifest["parity_exempt"])
    router: str = manifest["router_skill"]

    def product_of(name: str) -> str | None:
        return next((p for p in prefixes if name.startswith(p)), None)

    skills_dir = args.repo_root / "skills"
    findings: list[str] = []
    skill_dirs = list_skill_dirs(skills_dir, args.prefix, exclude={router})

    # --- per-skill frontmatter checks
    for d in skill_dirs:
        sk = d / "SKILL.md"
        if not sk.exists():
            findings.append(f"{d.name}: SKILL.md missing")
            continue
        fm = frontmatter(sk)
        if fm.get("name") != d.name:
            findings.append(f"{d.name}: frontmatter name {fm.get('name')!r} != directory name")
        for field in ("description", "license", "author", "version"):
            if not fm.get(field):
                findings.append(f"{d.name}: frontmatter missing `{field}`")

    # --- sibling layout parity per product
    by_product: dict[str, list[Path]] = defaultdict(list)
    for d in skill_dirs:
        p = product_of(d.name)
        if p and d.name not in parity_exempt:
            by_product[p].append(d)
    for product, dirs in sorted(by_product.items()):
        layouts: dict[str, set[str]] = {}
        union: set[str] = set()
        for d in dirs:
            files = {
                str(f.relative_to(d)) for f in d.rglob("*")
                if f.is_file() and f.suffix in {".md", ".json"}
                and "fixtures" not in f.parts and f.name != "SKILL.md"
            }
            layouts[d.name] = files
            union |= files
        for name, files in sorted(layouts.items()):
            for f in sorted(union - files):
                findings.append(f"{name}: sibling-parity — missing `{f}` "
                                f"(present in other {product}* skills)")

    # --- routing table sync (always over the full catalog)
    root = skills_dir / router / "SKILL.md"
    if root.exists():
        # Anchor to known product prefixes so prose backticks can't false-positive.
        prefix_alt = "|".join(re.escape(p) for p in prefixes)
        referenced = set(re.findall(rf"`((?:{prefix_alt})[a-z0-9-]+)`", root.read_text()))
        all_dirs = {d.name for d in list_skill_dirs(skills_dir, exclude={router})}
        for name in sorted(all_dirs - referenced):
            findings.append(f"routing: `{name}` exists but is not referenced in {router}/SKILL.md")
        for name in sorted(referenced - all_dirs):
            findings.append(f"routing: {router}/SKILL.md references `{name}` which does not exist")

    if findings:
        print(f"{len(findings)} finding(s):\n")
        for f in findings:
            print(f"  ✗ {f}")
        sys.exit(1)
    print(f"OK — {len(skill_dirs)} skill(s) linted, no findings")


if __name__ == "__main__":
    main()
