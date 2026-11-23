"""Prepare the two full packages for the SDC-36388 discovery comparison."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

import yaml


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASE = "5fc47c9f1e51b04237864c8b65026dc2665cd822"
PACKAGE_HASHES = {
    "baseline": "beaea17fb0277a7400b721d60267ae44c773e534c1d547dedb282aa3c12d56df",
    "candidate": "45b586a467deb25d1f69010486c5531fb85feadc3137ff22b39c2f66ec9ddd87",
    "split": "08cc3909bb978977a91f293f5ba90a0b209c2941bdb20d621968c229d723e6ad",
}


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args])


def replace_description(path, description):
    lines = path.read_text().splitlines(keepends=True)
    end = lines.index("---\n", 1)
    index, = (i for i in range(1, end) if lines[i].startswith("description: "))
    lines[index] = "description: " + json.dumps(description, ensure_ascii=False) + "\n"
    assert yaml.safe_load("".join(lines[1:end]))["description"] == description
    path.write_text("".join(lines))


def fingerprint(root):
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def checked_fingerprint(root):
    checksum = fingerprint(root)
    if checksum != PACKAGE_HASHES[root.name]:
        raise ValueError(f"{root.name} differs from the frozen pilot package: {checksum}")
    return checksum


def stage(out):
    if out.exists():
        raise SystemExit(f"Choose a new output directory: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        result = Path(tmp) / "packages"
        baseline = result / "baseline"
        candidate = result / "candidate"
        publish = yaml.safe_load(git("show", f"{BASE}:.github/workflows/publish-dist.yml"))
        paths = publish["jobs"]["publish"]["env"]["PUBLISH"].split()
        with zipfile.ZipFile(io.BytesIO(git("archive", "--format=zip", BASE, "--", *paths))) as dist:
            dist.extractall(baseline)
        linux = baseline / "skills/scandit-linux-sdk/SKILL.md"
        raw = linux.read_text().splitlines()[2].removeprefix("description: ")
        replace_description(linux, raw)
        if not git("hash-object", str(linux)).decode().startswith("c0b386d7"):
            raise ValueError("Unexpected Linux document after applying #153")
        shutil.copytree(baseline, candidate)
        for name, description in json.loads((HERE / "candidate.json").read_text()).items():
            replace_description(candidate / "skills" / name / "SKILL.md", description)
        manifest = {"base": BASE, "linux_correction": "Scandit/skills#153",
                    "sha256": {p.name: checked_fingerprint(p) for p in (baseline, candidate)}}
        (result / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        result.rename(out)
    print(out / "manifest.json")


def stage_guides(out):
    baseline = out / "baseline"
    expected = checked_fingerprint(baseline)
    with tempfile.TemporaryDirectory(dir=out) as tmp:
        split = Path(tmp) / "split"
        shutil.copytree(baseline, split)
        skill = Path("skills/matrixscan-count-rn")
        recipe = json.loads((HERE / "fixtures/guide-split.json").read_text())
        for name, spec in recipe.items():
            source = (baseline / skill / spec["source"]).read_text().splitlines(keepends=True)
            with (split / skill / name).open("w", encoding="utf-8", newline="\n") as target:
                for chunk in spec["lines"]:
                    if isinstance(chunk, str):
                        target.write(chunk + "\n")
                    else:
                        first, last = chunk  # Inclusive, one-based baseline line numbers.
                        target.writelines(source[first - 1:last])
        manifest = {"original": expected, "split": checked_fingerprint(split)}
        split.rename(out / "split")
    (out / "guide-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def matrix(out, mode):
    import claude
    import codex

    out.mkdir(parents=True, exist_ok=False)
    packages = out / "packages"
    stage(packages)
    if mode != "matrix":
        stage_guides(packages)
    variants = ("baseline", "candidate" if mode == "matrix" else "split")
    cases = {"matrix": claude.CASES, "guide-matrix": ("rn-integration", "toolbar"),
             "controlled-toolbar": ("toolbar-controlled",)}[mode]
    for variant in variants:
        subprocess.run([sys.executable, HERE / "validate.py", packages / variant], check=True)
    failures = []
    claude_result = subprocess.run([sys.executable, HERE / "claude.py", "--stages", packages,
                                   "--output", out / "claude", "--round", "initial",
                                   "--variant", *variants, "--case", *cases])
    if claude_result.returncode:
        failures.append(str(out / "claude" / "initial"))
    for model in codex.MODELS:
        for case in cases:
            for variant in variants:
                dest = out / "codex" / model / case / variant
                result = subprocess.run([sys.executable, HERE / "codex.py", "--package",
                                         packages / variant, "--case", case, "--model", model,
                                         "--out", dest, "--measure"])
                if result.returncode:
                    failures.append(str(dest))
    if failures:
        raise SystemExit("Incomplete runs. Inspect these outputs:\n" + "\n".join(failures))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["stage", "guides", "matrix", "guide-matrix", "controlled-toolbar"])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if args.command in ("matrix", "guide-matrix", "controlled-toolbar"):
        matrix(out, args.command)
    elif args.command == "stage":
        stage(out)
    else:
        stage_guides(out)
