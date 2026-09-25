#!/usr/bin/env python3
"""Deterministic structure linter for the Scandit skill repo.

Usage: python3 lint_structure.py [--prefix sparkscan-] [--repo-root PATH]

Checks (per skill, and across siblings sharing a product prefix):
  frontmatter   name matches directory, description present, license, author, version,
                description within the always-on token budget and naming the product
  layout        every sibling has the same reference files and eval suite files,
                scoped by `manifest.json`'s `parity_scope` (a file only applies to
                some platforms) and `parity_known_gaps` (an in-scope file that's
                really missing, not a defect)
  principles    every references/migration.md and third-party-migration.md carries
                its "Migration principles" labels
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
from common import REPO_ROOT, frontmatter, list_skill_dirs, load_manifest, eval_dir, eval_suite_files

# Descriptions are injected into every user session for every installed skill —
# they are trigger metadata, not documentation. 600 chars ≈ 150 tokens each.
DESCRIPTION_BUDGET = 600

# Bold labels every "## Migration principles" block must carry, per guide type.
# Third-party guides have no dual-version case: the old code is not Scandit.
_SHARED_PRINCIPLES = ("Authority", "Behaviour changes", "Compatibility layer")
MIGRATION_PRINCIPLES = {
    "migration.md": _SHARED_PRINCIPLES + ("Dual-version code",),
    "third-party-migration.md": _SHARED_PRINCIPLES,
}


def _scope(entry: list[str] | dict, platforms: set[str]) -> tuple[list[str], set[str]]:
    """A `parity_scope` entry's listed platform names, and the platforms that must carry the file."""
    if isinstance(entry, dict):
        return entry["except"], platforms - set(entry["except"])
    return entry, set(entry)


def lint(repo_root: Path, manifest: dict, prefix: str | None = None) -> tuple[list[str], int]:
    """All findings, and how many skills were linted."""
    prefixes: list[str] = manifest["product_prefixes"]
    parity_exempt: set[str] = set(manifest.get("parity_exempt", []))
    parity_scope: dict = manifest.get("parity_scope", {})
    parity_known_gaps: dict = manifest.get("parity_known_gaps", {})
    router: str = manifest["router_skill"]

    def product_of(name: str) -> str | None:
        return next((p for p in prefixes if name.startswith(p)), None)

    skills_dir = repo_root / "skills"
    evals_root = repo_root / "evals"
    findings: list[str] = []
    skill_dirs = list_skill_dirs(skills_dir, prefix, exclude={router})

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

    # --- sibling layout parity per product
    by_product: dict[str, list[Path]] = defaultdict(list)
    for d in skill_dirs:
        p = product_of(d.name)
        if p and d.name not in parity_exempt:
            by_product[p].append(d)
    for product, dirs in sorted(by_product.items()):
        layouts: dict[str, set[str]] = {}
        union: set[str] = set()
        platforms = {d.name[len(product):] for d in dirs}
        for d in dirs:
            files = {
                str(f.relative_to(d)) for f in d.rglob("*")
                if f.is_file() and f.suffix in {".md", ".json"}
                and "fixtures" not in f.parts and f.name != "SKILL.md"
            }
            # Eval suites live outside the published skill dir (evals/<skill>/), but
            # still participate in sibling-parity as if they were skills/<skill>/evals/*
            # — re-prefixed so finding text matches the pre-relocation convention.
            ed = eval_dir(d.name, evals_root)
            files |= {f"evals/{f.relative_to(ed)}" for f in eval_suite_files(d.name, evals_root)}
            layouts[d.name] = files
            union |= files
        required_on: dict[str, set[str]] = {}
        for f, entry in sorted(parity_scope.get(product, {}).items()):
            names, required_on[f] = _scope(entry, platforms)
            for p in names:
                if p not in platforms:
                    findings.append(f"manifest.json: parity_scope `{product}` `{f}` "
                                    f"names unknown platform `{p}`")
        for name, files in sorted(layouts.items()):
            platform = name[len(product):]
            gaps = set(parity_known_gaps.get(name, []))
            for f in sorted(union - files):
                if f in gaps or platform not in required_on.get(f, platforms):
                    continue
                findings.append(f"{name}: sibling-parity — missing `{f}` "
                                f"(present in other {product}* skills)")
            for f in sorted(gaps & files):
                findings.append(f"{name}: parity_known_gaps lists `{f}` but it exists "
                                f"— remove it from manifest.json")

    # --- migration principles block in every migration guide
    for d in skill_dirs:
        for guide, labels in MIGRATION_PRINCIPLES.items():
            path = d / "references" / guide
            if not path.exists():
                continue
            section = re.search(r"^## Migration principles\n(.*?)(?=^## |\Z)",
                                path.read_text(), re.M | re.S)
            block = section[1] if section else ""
            for label in labels:
                if f"**{label}.**" not in block:
                    findings.append(f"{d.name}: migration-principles — "
                                    f"`references/{guide}` missing \"{label}\"")

    # --- routing table sync (always over the full catalog)
    root = skills_dir / router / "SKILL.md"
    if root.exists():
        text = root.read_text()
        all_dirs = {d.name for d in list_skill_dirs(skills_dir, exclude={router})}
        # Any backticked token naming an existing skill dir counts as a reference —
        # not just ones under a known product prefix (e.g. `scandit-xamarin-to-net-migration`).
        referenced = {m for m in re.findall(r"`([a-z0-9][a-z0-9-]*)`", text) if m in all_dirs}
        for name in sorted(all_dirs - referenced):
            findings.append(f"routing: `{name}` exists but is not referenced in {router}/SKILL.md")
        # Reverse direction stays prefix-anchored so prose backticks can't false-positive.
        prefix_alt = "|".join(re.escape(p) for p in prefixes)
        prefixed_refs = set(re.findall(rf"`((?:{prefix_alt})[a-z0-9-]+)`", text))
        for name in sorted(prefixed_refs - all_dirs):
            findings.append(f"routing: {router}/SKILL.md references `{name}` which does not exist")

    return findings, len(skill_dirs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", help="only lint skills with this prefix")
    ap.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = ap.parse_args()

    findings, linted = lint(args.repo_root, load_manifest(), args.prefix)
    if findings:
        print(f"{len(findings)} finding(s):\n")
        for f in findings:
            print(f"  ✗ {f}")
        sys.exit(1)
    print(f"OK — {linted} skill(s) linted, no findings")


if __name__ == "__main__":
    main()
