"""Scores a migrated fixture: does it compile, and did it keep the symbologies the original scanned."""
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "internal" / "skill-auditor" / "scripts"))
from common import eval_dir  # noqa: E402

MAPPING = REPO / "internal" / "symbology-map" / "mapping.json"
FORMATS_LIST = re.compile(r"\bformats\s*:\s*(?:const\s*)?(?:<[^>]*>\s*)?\[(.*?)\]", re.DOTALL)
FORMAT_NAME = re.compile(r"BarcodeFormat\.(\w+)")
COMMENTS = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)
GATE_SKIPPED = 3


@dataclass(frozen=True)
class Suite:
    gate: Path
    source: str
    lang: str
    error_line: re.Pattern
    allowed_tools: str
    prompt_suffix: str


SUITES = {
    "barcode-capture-flutter": Suite(
        gate=eval_dir("barcode-capture-flutter") / "analyze_migration.sh",
        source="mobile_scanner",
        lang="dart",
        error_line=re.compile(r"^\s*error • ", re.MULTILINE),
        allowed_tools="Read Edit Write Glob Grep Skill Bash(flutter:*) Bash(dart:*)",
        prompt_suffix="\n\nThe project is in the current directory (lib/{main}). Edit the files in place.",
    ),
}


@lru_cache(maxsize=None)
def load_mapping():
    return json.loads(MAPPING.read_text())


def fixture_paths(eval_entry):
    """Paths under lib/ of the migrated main file and its stubs."""
    main, *stubs = eval_entry["files"]
    return [Path(main).name, *(str(Path("stubs") / Path(f).name) for f in stubs)]


def run_gate(command):
    proc = subprocess.run(command, capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def strip_comments(text):
    return COMMENTS.sub("", text)


def expected_symbologies(source_text, suite, mapping):
    default = list(mapping["default_set"])
    match = FORMATS_LIST.search(strip_comments(source_text))
    if not match:
        return default
    names = FORMAT_NAME.findall(match.group(1))
    if not names or "all" in names:
        return default
    by_name = {
        name: key
        for key, native in mapping["sources"][suite.source]["rows"].items()
        for name in native
    }
    ids = []
    for name in names:
        key = by_name.get(name)
        symbology = mapping["formats"][key]["symbology"] if key else None
        if symbology and symbology not in ids:
            ids.append(symbology)
    return ids or default


def symbologies_found(output_text, ids, suite, mapping):
    code = strip_comments(output_text)
    return [
        sid for sid in ids
        if re.search(rf"\bSymbology\.{re.escape(mapping['symbologies'][sid][suite.lang])}\b", code)
    ]


def gate_status(exit_code, errors_left):
    if exit_code == 0:
        return "pass"
    if exit_code == GATE_SKIPPED:
        return "skip"
    return "fail" if errors_left else "resolve-fail"


def score_eval(suite, eval_entry, output_dir, evals_dir, gate_runner=None):
    original = Path(evals_dir) / eval_entry["files"][0]
    main, *stubs = [Path(output_dir) / "lib" / p for p in fixture_paths(eval_entry)]
    mapping = load_mapping()
    expected = expected_symbologies(original.read_text(), suite, mapping)
    row = {"id": eval_entry["id"], "fixture": original.name, "expected": expected}
    if not main.is_file():
        return {**row, "status": "missing", "compiles": None, "errors_left": 0,
                "found": [], "missing": expected, "kept": False, "narrowed": False}
    stubs = [s for s in stubs if s.is_file()]
    code, output = (gate_runner or run_gate)(["bash", str(suite.gate), str(main), *map(str, stubs)])
    errors_left = len(suite.error_line.findall(output))
    status = gate_status(code, errors_left)
    found = symbologies_found("\n".join(p.read_text() for p in [main, *stubs]), expected, suite, mapping)
    missing = [s for s in expected if s not in found]
    # An original with no format list scans everything, so a migrated subset is a deliberate narrowing.
    narrowed = bool(missing and found) and expected == list(mapping["default_set"])
    return {
        **row,
        "status": status,
        "compiles": None if status == "skip" else status == "pass",
        "errors_left": errors_left,
        "found": found,
        "missing": missing,
        "kept": not missing or narrowed,
        "narrowed": narrowed,
        "gate_output": output,
    }
