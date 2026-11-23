"""Validate SKILL.md frontmatter in a staged skill package. Requires PyYAML 6.x."""

import argparse
import sys
from pathlib import Path

import yaml


def validate_skill(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return "1:1: missing opening frontmatter delimiter"
    try:
        end = lines.index("---", 1)
    except ValueError:
        return "1:1: missing closing frontmatter delimiter"
    try:
        metadata = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.MarkedYAMLError as error:
        mark = error.problem_mark
        return f"{mark.line + 2}:{mark.column + 1}: {error.problem}"
    if not isinstance(metadata, dict):
        return "2:1: expected a mapping in frontmatter"
    for key in ("name", "description"):
        if not isinstance(metadata.get(key), str) or not metadata[key].strip():
            return f"2:1: expected a nonempty string for {key}"
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path, help="root containing the skills/ directory")
    package = parser.parse_args().package
    skills = sorted(package.glob("skills/*/SKILL.md"))
    if not skills:
        print(f"{package}/skills: no SKILL.md files found", file=sys.stderr)
        return 1
    has_errors = False
    for skill in skills:
        issue = validate_skill(skill)
        if issue:
            print(f"{skill.relative_to(package)}:{issue}", file=sys.stderr)
            has_errors = True
    if has_errors:
        return 1
    print(f"Validated {len(skills)} skills")
    return 0


if __name__ == "__main__":
    sys.exit(main())
