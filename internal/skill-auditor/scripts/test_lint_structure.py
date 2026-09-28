"""Tests for the scoped sibling-parity behaviour of lint_structure.lint().

Fixture tree in a tempdir: skills/p-a, p-b, p-c (product prefix "p-", platforms
a/b/c) plus their evals/ dirs. manifest is a plain dict, passed straight to
lint() — no repo checkout, no ../manifest.json involved.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lint_structure import lint

FRONTMATTER = """---
name: {name}
description: p thing for testing
license: MIT
author: scandit
version: "1.0.0"
---

# {name}
"""

MANIFEST = {
    "router_skill": "router",  # no skills/router/SKILL.md in the fixture -> routing check no-ops
    "product_prefixes": ["p-"],
    "parity_exempt": [],
    "parity_scope": {
        "p-": {
            "references/foo.md": ["a", "b"],  # in scope for a, b only
            "references/baz.md": {"except": ["c"]},
            "references/qux.md": ["a", "b", "z"],  # z is no sibling's platform
        },
    },
    "parity_known_gaps": {
        "p-b": ["references/bar.md"],
        "p-a": ["references/stale.md"],
    },
}


class LintScopedParityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        skills = self.root / "skills"
        evals = self.root / "evals"
        for name in ("p-a", "p-b", "p-c"):
            (skills / name / "references").mkdir(parents=True)
            (skills / name / "SKILL.md").write_text(FRONTMATTER.format(name=name))
            (evals / name).mkdir(parents=True)

        # references/foo.md: in scope [a, b] -> p-a has it, p-b is missing it (finding),
        # p-c is out of scope so its absence is not a finding.
        (skills / "p-a" / "references" / "foo.md").write_text("foo")

        # references/bar.md: default scope (all siblings) -> p-b is a known gap (no
        # finding); give p-a/p-c the file so bar.md contributes no other findings.
        (skills / "p-a" / "references" / "bar.md").write_text("bar")
        (skills / "p-c" / "references" / "bar.md").write_text("bar")

        # references/stale.md: manifest claims p-a is missing it, but it exists ->
        # stale-known-gap finding. Give every sibling the file so nothing else fires.
        for name in ("p-a", "p-b", "p-c"):
            (skills / name / "references" / "stale.md").write_text("stale")

        # references/baz.md: scope "all but c" -> p-b missing it is a finding, p-c is not.
        (skills / "p-a" / "references" / "baz.md").write_text("baz")

        # references/qux.md: on every in-scope sibling, so only the unknown platform fires.
        for name in ("p-a", "p-b"):
            (skills / name / "references" / "qux.md").write_text("qux")

    def test_in_scope_missing_file_is_a_finding(self):
        findings, _ = lint(self.root, MANIFEST)
        self.assertIn(
            "p-b: sibling-parity — missing `references/foo.md` (present in other p-* skills)",
            findings,
        )

    def test_out_of_scope_missing_file_is_not_a_finding(self):
        findings, _ = lint(self.root, MANIFEST)
        self.assertFalse(any("references/foo.md" in f and f.startswith("p-c") for f in findings))

    def test_known_gap_is_not_a_finding(self):
        findings, _ = lint(self.root, MANIFEST)
        self.assertFalse(any("references/bar.md" in f and f.startswith("p-b") for f in findings))

    def test_stale_known_gap_is_a_finding(self):
        findings, _ = lint(self.root, MANIFEST)
        self.assertIn(
            "p-a: parity_known_gaps lists `references/stale.md` but it exists — "
            "remove it from manifest.json",
            findings,
        )

    def test_except_scope_requires_every_platform_but_the_excepted(self):
        findings, _ = lint(self.root, MANIFEST)
        self.assertIn(
            "p-b: sibling-parity — missing `references/baz.md` (present in other p-* skills)",
            findings,
        )
        self.assertFalse(any("references/baz.md" in f and f.startswith("p-c") for f in findings))

    def test_unknown_scope_platform_is_a_finding(self):
        findings, _ = lint(self.root, MANIFEST)
        self.assertIn(
            "manifest.json: parity_scope `p-` `references/qux.md` names unknown platform `z`",
            findings,
        )
        self.assertFalse(any("sibling-parity" in f and "qux.md" in f for f in findings))

    def test_routing_counts_any_backticked_skill_dir(self):
        skills = self.root / "skills"
        (skills / "standalone-tool").mkdir()
        (skills / "router").mkdir()
        (skills / "router" / "SKILL.md").write_text(
            "`p-a` `p-b` `p-c` `standalone-tool` `p-nonexistent` `ghost-tool`\n")
        findings, _ = lint(self.root, MANIFEST)
        routing = [f for f in findings if f.startswith("routing:")]
        self.assertEqual(
            routing,
            ["routing: router/SKILL.md references `p-nonexistent` which does not exist"],
        )


if __name__ == "__main__":
    unittest.main()
