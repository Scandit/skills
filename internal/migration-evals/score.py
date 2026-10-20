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
from common import AUDITOR_ROOT, eval_dir  # noqa: E402

MAPPING = REPO / "internal" / "symbology-map" / "mapping.json"
DEFAULT_SDK_VERSION = "8.6.1"
TS_GATE = AUDITOR_ROOT / "scripts" / "fix_gate_ts.sh"
DOTNET_GATE = AUDITOR_ROOT / "scripts" / "fix_gate_dotnet.sh"
COMMENTS_AND_STRINGS = re.compile(
    r"""'''.*?'''|\"\"\".*?\"\"\"|'(?:\\.|[^'\\\n])*'|"(?:\\.|[^"\\\n])*"|//[^\n]*|/\*.*?\*/""", re.DOTALL
)
SYMBOLOGY = re.compile(r"\bSymbology\.(\w+)")
ENABLE_ONE = re.compile(
    r"\b[eE]nableSymbology\(\s*Symbology\.(\w+)\s*,\s*true\s*\)"
    r"|\b(?:settingsForSymbology|GetSymbologySettings)\(\s*Symbology\.(\w+)\s*\)\s*\.(?:isEnabled|Enabled)\s*=\s*true\b"
)
ENABLE_MANY = re.compile(r"\b[eE]nableSymbologies\s*\(")
ENABLE_PROP = re.compile(r"(?<![\w.])symbologies=\{")
CALLABLE = re.compile(r"\b(\w+)\s*(?:=\s*(?:async\s*)?(?:function\b\s*)?)?\(")
DECLARATION_TAIL = re.compile(r"\s*(?::[^;{}()=]*)?(?:async\s*)?(?:\{|=>)")
KEYWORDS = {"if", "for", "while", "switch", "catch", "return", "function"}
IDENTIFIER = re.compile(r"(?<![.\w])([A-Za-z_]\w*)\b(?!\s*\()")
GATE_SKIPPED = 3
TS_ERROR = re.compile(r"\berror TS\d+")
CS_ERROR = re.compile(r"\berror CS\d+")
TS_TOOLS = "Read Edit Write Glob Grep Skill"
TS_SUFFIX = "\n\nThe files are in the current directory. Edit them in place."


@dataclass(frozen=True)
class Suite:
    gate: Path
    format_lists: dict
    lang: str
    error_line: re.Pattern
    allowed_tools: str
    prompt_suffix: str
    platform: str | None = None
    banned_imports: tuple = ()


SUITES = {
    "barcode-capture-flutter": Suite(
        gate=eval_dir("barcode-capture-flutter") / "analyze_migration.sh",
        format_lists={"formats": "mobile_scanner"},
        lang="dart",
        error_line=re.compile(r"^\s*error • ", re.MULTILINE),
        allowed_tools="Read Edit Write Glob Grep Skill Bash(flutter:*) Bash(dart:*)",
        prompt_suffix="\n\nThe project is in the current directory (lib/{main}). Edit the files in place.",
    ),
    "barcode-capture-rn": Suite(
        gate=TS_GATE,
        format_lists={
            "codeTypes": "vision-camera-v4",
            "barcodeFormats": "vision-camera-v5",
            "barcodeTypes": "expo-camera",
        },
        lang="js",
        error_line=TS_ERROR,
        allowed_tools=TS_TOOLS,
        prompt_suffix=TS_SUFFIX,
        platform="rn",
        banned_imports=("react-native-vision-camera", "react-native-vision-camera-barcode-scanner", "expo-camera"),
    ),
    "barcode-capture-capacitor": Suite(
        gate=TS_GATE,
        format_lists={"formats": "capacitor-mlkit"},
        lang="js",
        error_line=TS_ERROR,
        allowed_tools=TS_TOOLS,
        prompt_suffix=TS_SUFFIX,
        platform="capacitor",
        banned_imports=("@capacitor-mlkit/barcode-scanning",),
    ),
    "barcode-capture-net-maui": Suite(
        gate=DOTNET_GATE,
        format_lists={"Formats": "zxing-net-maui"},
        lang="csharp",
        error_line=CS_ERROR,
        allowed_tools=TS_TOOLS,
        prompt_suffix=TS_SUFFIX,
        platform="maui",
        banned_imports=("ZXing.Net.Maui",),
    ),
}


@lru_cache(maxsize=None)
def load_mapping():
    return json.loads(MAPPING.read_text())


def fixture_paths(suite, eval_entry):
    """Workdir-relative paths of the files a migration run produces."""
    files = eval_entry["files"]
    if suite.platform:
        paths = [Path(f).name for f in files]
    else:
        main, *stubs = files
        paths = [str(Path("lib") / Path(main).name), *(str(Path("lib/stubs") / Path(f).name) for f in stubs)]
    if len(set(paths)) < len(paths):
        raise ValueError(f"eval files must have distinct names, got {files}")
    return paths


def run_gate(command):
    proc = subprocess.run(command, capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def strip_comments(text):
    return COMMENTS_AND_STRINGS.sub(lambda m: m.group() if m.group()[0] in "'\"" else "", text)


def list_items(text, key):
    """Items of every `<key>: [ ... ]` list in text; double-quoted strings normalise to single."""
    pattern = rf"\b{key}\s*:\s*(?:const\s*)?(?:<[^>]*>\s*)?\[(.*?)\]"
    for body in re.findall(pattern, text, re.DOTALL):
        for item in body.split(","):
            item = item.strip()
            if item:
                yield re.sub(r'^"(.*)"$', r"'\1'", item)


def flag_items(text, key):
    """Members of every `<key> = A.X | A.Y` flags assignment in text."""
    for expression in re.findall(rf"\b{key}\s*=\s*((?:[^,;}}|\n]+\s*\|\s*)*[^,;}}|\n]+)", text):
        for item in expression.split("|"):
            if item.strip():
                yield item.strip()


def expected_symbologies(source_text, suite, mapping):
    default = list(mapping["default_set"])
    text = strip_comments(source_text)
    ids = []
    for key, source in suite.format_lists.items():
        by_name = {}
        for row, native in mapping["sources"][source]["rows"].items():
            for name in native["names"] if isinstance(native, dict) else native:
                by_name[name] = row
        items = flag_items(text, key) if suite.lang == "csharp" else list_items(text, key)
        for item in items:
            tail = item.rsplit(".", 1)[-1]
            row = by_name.get(item) or by_name.get(tail)
            if row == "all-formats" or tail.lower() == "all":
                return default
            if not row:
                raise ValueError(f"unreadable {key} item {item!r}: map it in {MAPPING.name} or simplify the fixture")
            symbology = mapping["formats"][row]["symbology"]
            if symbology and symbology not in ids:
                ids.append(symbology)
    return ids or default


def balanced(text, start):
    """Text between the bracket at text[start] and its matching close."""
    depth = 0
    for i in range(start, len(text)):
        depth += text[i] in "([{"
        depth -= text[i] in ")]}"
        if depth == 0:
            return text[start + 1:i]
    return text[start + 1:]


def enabled_names(code, lang="dart"):
    """Symbology names reaching an enabling call; identifier args resolve to their collection literal."""
    names = {a or b for a, b in ENABLE_ONE.findall(code)}
    patterns = [ENABLE_MANY] + ([ENABLE_PROP] if lang == "js" else [])
    for call in (m for pattern in patterns for m in pattern.finditer(code)):
        arg = balanced(code, call.end() - 1)
        names.update(resolve_args(code, arg, set(), call.start()))
    return names


def callables(code):
    """(name, args, body, start) for every `name(...)`; body is the (start, end) span of a declaration, else None."""
    for m in CALLABLE.finditer(code):
        if m.group(1) not in KEYWORDS:
            args = balanced(code, m.end() - 1)
            tail = DECLARATION_TAIL.match(code, m.end() + len(args) + 1)
            yield m.group(1), args, tail and (tail.end(), body_end(code, tail)), m.start()


def body_end(code, tail):
    """End offset of a declaration body: a bracketed block, else an arrow expression up to the line end."""
    i = tail.end() - 1 if tail.group().endswith("{") else len(code) - len(code[tail.end():].lstrip())
    if i < len(code) and code[i] in "({[":
        return i + len(balanced(code, i)) + 2
    newline = code.find("\n", i)
    return len(code) if newline < 0 else newline


def enclosing_function(code, ident, at):
    """(name, span) of the innermost function that declares parameter `ident` and whose body contains offset `at`;
    span covers its parameter list and body. (None, None) when there is none."""
    declared = rf"(?<![\w.]){re.escape(ident)}\b"
    owners = [(body[0], name, (start, body[1])) for name, args, body, start in callables(code)
              if body and body[0] <= at < body[1] and re.search(declared, args)]
    return max(owners)[1:] if owners else (None, None)


def resolve_args(code, arg, seen, at):
    """Symbology names in the argument at offset `at`: a parameter of the enclosing function resolves to its
    literals inside that function plus the function's call sites, any other identifier to its file literals."""
    names = set(SYMBOLOGY.findall(arg))
    for ident in set(IDENTIFIER.findall(arg)):
        owner, span = enclosing_function(code, ident, at)
        if (ident, owner) in seen:
            continue
        seen.add((ident, owner))
        if owner:
            for name, args, body, start in callables(code):
                if name == owner and not body:
                    names.update(resolve_args(code, args, seen, start))
        definitions = re.compile(rf"\b{re.escape(ident)}\s*(?::[^=;{{}}]+)?=\s*(?:const\s*)?(?:new\s*\w*\s*(?:<[^>]*>\s*)?(?:\[\]\s*)?)?(?:<[^>]*>\s*)?[{{\[]")
        for definition in definitions.finditer(code, *(span or (0, len(code)))):
            names.update(SYMBOLOGY.findall(balanced(code, definition.end() - 1)))
    return names


def symbologies_found(output_text, ids, suite, mapping):
    enabled = enabled_names(COMMENTS_AND_STRINGS.sub("", output_text), suite.lang)
    return [sid for sid in ids if mapping["symbologies"][sid][suite.lang] in enabled]


def leftover_imports(text, modules):
    """Import, re-export, dynamic import, require, C# using and XAML clr-namespace naming a banned module."""
    text = strip_comments(text)
    count = 0
    for module in modules:
        specifier = rf"""["']{re.escape(module)}(?:/[^"'\n]*)?["']"""
        count += len(re.findall(rf"\bfrom\s*{specifier}|\bimport\s*\(?\s*{specifier}|\brequire\s*\(\s*{specifier}", text))
        namespace = rf"{re.escape(module)}(?:\.\w+)*"
        count += len(re.findall(rf"\busing\s+(?:static\s+)?(?:\w+\s*=\s*)?{namespace}\s*;|\bclr-namespace:{namespace}(?![\w.])", text))
    return count


def gate_status(exit_code, errors_left):
    if exit_code == 0:
        return "pass"
    if exit_code == GATE_SKIPPED:
        return "skip"
    return "fail" if errors_left else "resolve-fail"


def gate_command(suite, main, extras, sdk_version, original):
    if not suite.platform:
        return ["bash", str(suite.gate), str(main), *map(str, extras)]
    if suite.platform == "maui":
        return ["bash", str(suite.gate), "--maui", str(main), sdk_version]
    shim = ["FIX_GATE_TS_ANY_MODULE=1"] if suite.banned_imports else []
    return ["env", *shim, f"FIX_GATE_TS_BASELINE={original}", "bash", str(suite.gate), suite.platform, str(main), sdk_version, *map(str, extras)]


def score_eval(suite, eval_entry, output_dir, evals_dir, gate_runner=None, sdk_version=DEFAULT_SDK_VERSION):
    original = Path(evals_dir) / eval_entry["files"][0]
    main, *extras = [Path(output_dir) / p for p in fixture_paths(suite, eval_entry)]
    mapping = load_mapping()
    expected = expected_symbologies(original.read_text(), suite, mapping)
    row = {"id": eval_entry["id"], "fixture": original.name, "expected": expected}
    if not main.is_file():
        return {**row, "status": "missing", "compiles": None, "errors_left": 0,
                "found": [], "missing": expected, "kept": False, "narrowed": False}
    extras = [s for s in extras if s.is_file()]
    code, output = (gate_runner or run_gate)(gate_command(suite, main, extras, sdk_version, original))
    errors_left = len(suite.error_line.findall(output))
    status = gate_status(code, errors_left)
    migrated = "\n".join(p.read_text() for p in [main, *extras])
    found = symbologies_found(migrated, expected, suite, mapping)
    missing = [s for s in expected if s not in found]
    # An original with no format list scans everything, so a migrated subset is a deliberate narrowing.
    narrowed = bool(missing and found) and expected == list(mapping["default_set"])
    leftover = leftover_imports(migrated, suite.banned_imports)
    if leftover and status in ("pass", "fail"):
        errors_left += leftover
        status = "fail"
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
        **({"leftover_imports": leftover} if leftover else {}),
    }
