"""Validate SKILL.md frontmatter in a staged skill package. Requires PyYAML 6.x."""

import argparse
import sys
from pathlib import Path

import yaml


def position_after(prefix, first_line):
    prefix = prefix.replace("\r\n", "\n").replace("\r", "\n")
    lines = prefix.split("\n")
    line = first_line + len(lines) - 1
    return f"{line}:{len(lines[-1]) + 1}"


def validate_skill(path):
    try:
        lines = path.read_bytes().decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        prefix = error.object[:error.start].decode("utf-8")
        return f"{position_after(prefix, 1)}: invalid UTF-8"
    if not lines or lines[0] != "---":
        return "1:1: missing opening frontmatter delimiter"
    try:
        end = lines.index("---", 1)
    except ValueError:
        return "1:1: missing closing frontmatter delimiter"
    header = "\n".join(lines[1:end])
    try:
        metadata = yaml.safe_load(header)
    except yaml.reader.ReaderError as error:
        return f"{position_after(header[:error.position], 2)}: {error.reason}"
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
