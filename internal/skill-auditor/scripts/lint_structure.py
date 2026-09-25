#!/usr/bin/env python3
"""Deterministic structure linter for the Scandit skill repo.

Usage: python3 lint_structure.py [--prefix sparkscan-] [--repo-root PATH]

Checks (per skill, and across siblings sharing a product prefix):
  frontmatter   name matches directory, description present, license, author, version,
                description within the always-on token budget and naming the product
  layout        every sibling has the same reference files and eval suite files
  licence       every non-exempt skill carries a `## Licence key` section naming the product
                and licence platforms from references/licence-platforms.md, and carries the
                dashboard provisioning link nowhere else
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
from common import (REPO_ROOT, frontmatter, list_skill_dirs, load_manifest, eval_dir,
                    eval_suite_files, licence_platforms, resolve_licence)

# Descriptions are injected into every user session for every installed skill —
# they are trigger metadata, not documentation. 600 chars ≈ 150 tokens each.
DESCRIPTION_BUDGET = 600

LICENCE_REFERENCE_REL = "internal/skill-auditor/references/licence-platforms.md"


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
        desc = fm.get("description") or ""
        if len(desc) > DESCRIPTION_BUDGET:
            findings.append(
                f"{d.name}: description {len(desc)} chars > budget {DESCRIPTION_BUDGET} "
                "(descriptions are always-on context for every installed user; "
                "trigger metadata only — teaching content belongs in the body)"
            )
        product = product_of(d.name)
        # Naming rule: every .NET target framework uses a `net-<target>` suffix
        # (net-android, net-ios, net-maui). A bare `-maui` slug is the historical
        # inconsistency this convention replaced — reject it so it cannot regress.
        if product and d.name.endswith("-maui") and not d.name.endswith("-net-maui"):
            findings.append(
                f"{d.name}: .NET MAUI skills must use the `-net-maui` suffix "
                f"(every .NET target is `net-<target>`) — rename to "
                f"{d.name[: -len('-maui')]}-net-maui"
            )
        if product and desc:
            product_tokens = product.rstrip("-").replace("-", " ")
            normalized = re.sub(r"[^a-z0-9]+", " ", desc.lower())
            if product_tokens not in normalized:
                findings.append(
                    f"{d.name}: description does not mention product name "
                    f"{product_tokens!r} — the product name is the primary trigger token"
                )

    # --- licence-key section (product + platforms named, dashboard flow not duplicated)
    #
    # Every skill must tell the agent how to get a key, and must say it once. The
    # product and platform values are checked against the reference file rather
    # than a copy here, so the MCP server's own mapping stays the only source.
    # A broken reference table is a finding, not a traceback: this script's output is
    # parsed downstream, so it has to fail in the shape callers already handle.
    try:
        licence_map = licence_platforms()
    except (OSError, ValueError) as e:
        licence_map = {}
        findings.append(f"{LICENCE_REFERENCE_REL}: {e}")
    licence_exempt: set[str] = set(manifest["licence_key_exempt"])
    licence_link_allow: set[str] = set(manifest["licence_link_allow"])
    for d in skill_dirs:
        if d.name in licence_exempt:
            continue
        sk = d / "SKILL.md"
        if not sk.exists():
            continue  # already reported above
        body = sk.read_text()
        section = re.search(r"^## Licence key\n(.*?)(?=^## |\Z)", body, re.S | re.M)
        if not section:
            findings.append(f"{d.name}: SKILL.md missing `## Licence key` section")
        else:
            expected = resolve_licence(d.name, licence_map)
            if expected is None:
                findings.append(f"{d.name}: no row in {LICENCE_REFERENCE_REL} — "
                                "add one before the licence-key section can be checked")
            else:
                product, platforms = expected
                for token in [product, *platforms]:
                    if f"`{token}`" not in section.group(1):
                        findings.append(
                            f"{d.name}: licence-key section does not name `{token}` "
                            f"(per {LICENCE_REFERENCE_REL})")
        # The dashboard fallback lives in the licence-key section and nowhere else,
        # so a skill never carries two competing provisioning instructions.
        for f in sorted(d.rglob("*.md")):
            rel = str(f.relative_to(skills_dir))
            if rel in licence_link_allow:
                continue
            text = f.read_text()
            if f == sk and section:
                text = text.replace(section.group(0), "")
            if "ssl.scandit.com" in text:
                findings.append(f"{rel}: licence provisioning link outside the "
                                "`## Licence key` section — point readers at that section instead")

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
            # Eval suites live outside the published skill dir (evals/<skill>/), but
            # still participate in sibling-parity as if they were skills/<skill>/evals/*
            # — re-prefixed so finding text matches the pre-relocation convention.
            ed = eval_dir(d.name)
            files |= {f"evals/{f.relative_to(ed)}" for f in eval_suite_files(d.name)}
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
