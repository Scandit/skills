"""Judging for the assertion evals: deterministic checks first, an LLM judge for the rest.

An assertion phrased "X is [NOT] present|called|enabled", where X looks like code, is a
substring check on the output. Anything else, or anything marked "(semantic", goes to the
judge, all of one eval's assertions in a single call.
"""
import re

SUBSTRING_RE = re.compile(
    r"^(.+?)\s+is\s+(NOT\s+)?present(?:\s+in\s+(?:the\s+)?(?:output\s+)?file)?(\s*\(.*\))?\s*$", re.IGNORECASE
)
CALLED_RE = re.compile(r"^(.+?)\s+is\s+(NOT\s+)?called(\s*\(.*\))?\s*$", re.IGNORECASE)
ENABLED_RE = re.compile(r"^(.+?)\s+is\s+(NOT\s+)?enabled(\s*\(.*\))?\s*$", re.IGNORECASE)
CODE_LIKE_RE = re.compile(r"[(.<>=:]|[A-Z][a-z]+[A-Z]|[A-Za-z][_-]|[a-z]\.[a-z]")
CODE_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
NEGATIVE_RE = re.compile(
    r"\b(?:is|are|was|were)\s+NOT\b|\bnot\s+(?:present|constructed|used|called|imported|introduced|written)\b"
    r"|\bno\s+occurrence\b|\bis\s+absent\b|\bdoes\s+NOT\b|^no\s+",
    re.IGNORECASE,
)
VERDICT_RE = re.compile(r"^\s*(\d+)\.\s*(PASS|FAIL)\b.*$", re.MULTILINE | re.IGNORECASE)

JUDGE_SYSTEM = (
    "You judge whether assertions hold against an AI agent's code generation output. "
    "Rules:\n"
    "1. If the assertion says 'X is present' and X literally appears in the output → PASS.\n"
    "2. If the assertion says 'X is NOT present' and X does not appear → PASS.\n"
    "3. If your reasoning describes the assertion as matched, fulfilled, or correct, "
    "you MUST output PASS. Never contradict your own reasoning.\n"
    "4. 'X is enabled' means X is among enabled values; it does NOT require X to be the only enabled value.\n"
    "5. 'mentions X' means X appears anywhere in the relevant section, not necessarily as a literal heading.\n"
    "6. Be strict on what literally appears; do not invent absences.\n"
    "7. Judge each assertion independently."
)


def is_semantic(assertion):
    return "(semantic" in assertion.lower()


def is_negative(assertion):
    return bool(NEGATIVE_RE.search(assertion.strip()))


def extract_code(output):
    """Fenced code only: migration answers name the old API in prose, so absence checks skip it."""
    blocks = CODE_FENCE_RE.findall(output)
    return "\n".join(blocks) if blocks else output


def _token_check(token, output):
    token = token.strip().strip("'\"`")
    m = re.match(r"^Import from\s+['\"`]?([\w\-/.@_]+)['\"`]?$", token, re.IGNORECASE) or re.match(
        r"^([\w\-/.@_]+)\s+import$", token, re.IGNORECASE
    )
    if not m:
        return token in output
    pkg = re.escape(m.group(1))
    if re.search(r"""(?:from\s+|import\s+)['"`][^'"`]*""" + pkg + r"""[^'"`]*['"`]""", output):
        return True
    return bool(re.search(r"^\s*import\s+[\w.]*" + pkg + r"[\w.]*", output, re.MULTILINE))


def deterministic_check(output, assertion):
    """(passed, reason) when the assertion is a literal check, else None."""
    if is_semantic(assertion):
        return None
    for rx, kind in ((SUBSTRING_RE, "present"), (CALLED_RE, "called"), (ENABLED_RE, "enabled")):
        m = rx.match(assertion.strip())
        if not m:
            continue
        token = m.group(1).strip()
        if len(token) < 3 or not CODE_LIKE_RE.search(token):
            return None
        alternatives = [alt.strip() for alt in re.split(r"\s+or\s+", token)]
        found = any(_token_check(alt, output) for alt in alternatives)
        rendered = " | ".join(repr(alt) for alt in alternatives)
        if m.group(2):
            return not found, f"deterministic[{kind}]: {rendered} {'present' if found else 'absent'} (req absent)"
        return found, f"deterministic[{kind}]: {rendered} {'present' if found else 'absent'} (req present)"
    return None


def scoped_output(output, assertion, migration):
    return extract_code(output) if migration and is_negative(assertion) else output


def judge_prompt(output, assertions):
    listing = "\n".join(f"{i}. {a}" for i, a in enumerate(assertions, 1))
    return (
        f"=== ASSERTIONS ===\n{listing}\n\n=== AGENT OUTPUT ===\n{output}\n\n"
        "Output exactly one line per assertion, in order: "
        "`<n>. PASS: <reason>` or `<n>. FAIL: <reason>`. Nothing else."
    )


def parse_verdicts(text, count):
    verdicts = {int(m[1]): (m[2].upper() == "PASS", m[0].strip()[:200]) for m in VERDICT_RE.finditer(text)}
    return [verdicts.get(i, (False, "JUDGE_PARSE_ERROR")) for i in range(1, count + 1)]
