#!/usr/bin/env python3
"""Build a feature × platform eval-coverage matrix for one product.

Usage: python3 coverage_matrix.py <taxonomy.yaml> [--repo-root PATH] [--json]

Coverage source, in priority order:
  1. explicit `tags` on an eval (once suites are tagged)
  2. taxonomy `match` regexes against prompt + expected_output + assertion texts (bootstrap)

Exit code 1 if any `required: true` feature is uncovered on a supported platform,
so the same script doubles as the CI gate.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import REPO_ROOT, load_taxonomy, load_manifest


def eval_text(e: dict) -> str:
    parts = [e.get("prompt", ""), e.get("expected_output", "")]
    parts += [a.get("text", "") for a in e.get("assertions", [])]
    return " ".join(parts).lower()


def load_evals(skill_dir: Path):
    for f in sorted(skill_dir.glob("evals/*.json")):
        if "fixtures" in f.parts:
            continue
        try:
            data = json.loads(f.read_text())
        except json.JSONDecodeError as exc:
            print(f"WARN: unparseable {f}: {exc}", file=sys.stderr)
            continue
        evals = data.get("evals", data if isinstance(data, list) else [])
        for e in evals:
            yield f.name, e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("taxonomy", type=Path)
    ap.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    ap.add_argument("--json", action="store_true", help="emit machine-readable report")
    args = ap.parse_args()

    tax = load_taxonomy(args.taxonomy)
    prefix = tax["skill_prefix"]
    features = tax["features"]
    skills_dir = args.repo_root / "skills"
    # platform_aliases (manifest): map a skill dir name -> a canonical skill dir name so that
    # several skills fold into one logical platform whose evals are aggregated. Empty for most
    # products (then this is a no-op). e.g. matrixscan-ar-{annotation,highlight}-ios -> matrixscan-ar-ios.
    aliases = load_manifest().get("platform_aliases", {})
    plat_dirs: dict[str, list] = {}  # platform suffix -> source skill dirs (aggregated)
    for d in skills_dir.glob(f"{prefix}*"):
        if not d.is_dir():
            continue
        canon = aliases.get(d.name, d.name)
        plat_dirs.setdefault(canon[len(prefix):], []).append(d)
    platforms = sorted(plat_dirs)
    if not platforms:
        sys.exit(f"no skills matching {prefix}* under {skills_dir}")

    # Per-feature: compiled bootstrap patterns, platform exclusions, empty matrix row.
    compiled: dict[str, list] = {}
    excluded: dict[str, set] = {}
    matrix: dict[str, dict[str, list]] = {}  # [feature][platform] -> list of "file#id" hits
    for feat in features:
        fid = feat["id"]
        compiled[fid] = [re.compile(p, re.I) for p in feat.get("match", [])]
        excluded[fid] = set(feat.get("excluded_platforms", []))
        matrix[fid] = {p: [] for p in platforms}

    totals = {p: 0 for p in platforms}
    for plat in platforms:
        for d in plat_dirs[plat]:
            # When aggregated (>1 source dir), prefix the ref with the source skill so evidence
            # stays traceable to the right iOS sub-skill.
            tag = f"{d.name}/" if len(plat_dirs[plat]) > 1 else ""
            for fname, e in load_evals(d):
                totals[plat] += 1
                text = eval_text(e)
                tags = set(e.get("tags", []))
                ref = f"{tag}{fname}#{e.get('id', '?')}"
                for feat in features:
                    fid = feat["id"]
                    if fid in tags or any(rx.search(text) for rx in compiled[fid]):
                        matrix[fid][plat].append(ref)

    gaps = [
        {"feature": feat["id"], "platform": plat, "required": feat["required"]}
        for feat in features
        for plat in platforms
        if plat not in excluded[feat["id"]] and not matrix[feat["id"]][plat]
    ]

    if args.json:
        print(json.dumps({"product": tax["product"], "platforms": platforms,
                          "totals": totals, "matrix": matrix, "gaps": gaps}, indent=1))
    else:
        wide = max(len(f["id"]) for f in features) + 2
        print(f"# {tax['product']} eval coverage  (evals per platform: "
              + ", ".join(f"{p}={totals[p]}" for p in platforms) + ")\n")
        print("".rjust(wide) + "".join(p[:9].center(10) for p in platforms))
        for feat in features:
            fid = feat["id"]
            row = fid.ljust(wide)
            for plat in platforms:
                n = len(matrix[fid][plat])
                if plat in excluded[fid]:
                    cell = "—"
                else:
                    cell = str(n) if n else ("✗!" if feat["required"] else "✗")
                row += cell.center(10)
            print(row)
        req_gaps = [g for g in gaps if g["required"]]
        print(f"\ngaps: {len(gaps)} total, {len(req_gaps)} on required features"
              " (✗! = required, uncovered)")

    sys.exit(1 if any(g["required"] for g in gaps) else 0)


if __name__ == "__main__":
    main()
