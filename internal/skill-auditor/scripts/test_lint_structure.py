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
from common import resolve_licence
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


LICENCE_REFERENCE = """# Licence products and platforms

## Skill mapping

| Skill | Licence product | Licence platforms |
| --- | --- | --- |
| `-web` | `sdk` | `webassembly` |
| `-ios` | `native` | `ios` |
| `-rn` | `native` | `ios`, `android` |

## Key wiring

| Skill | Wiring |
| --- | --- |
| `-web` | Use the bundler, for example `import.meta.env`. |
| `-ios` | Use `Info.plist`. |
| `-rn` | Use a loader such as `react-native-config`. |
"""

LICENCE_SECTION = """
## Licence key

For this skill the licence product is `{product}` and the platforms are {platforms}.
Fallback: <https://ssl.scandit.com>.
Then: {wiring}

## References
"""

LICENCE_MANIFEST = {
    "router_skill": "router",
    "product_prefixes": ["p-"],
    "parity_exempt": ["p-exempt-ios"],
    "licence_key_exempt": ["p-exempt-ios"],
    "licence_link_allow": ["p-web/references/allowed.md"],
}


class LintLicenceKeyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        ref = self.root / "internal" / "skill-auditor" / "references" / "licence-platforms.md"
        ref.parent.mkdir(parents=True)
        ref.write_text(LICENCE_REFERENCE)
        self.skills = self.root / "skills"
        for name, product, platforms, wiring in (
            ("p-web", "sdk", "`webassembly`", "Use the bundler, for example `import.meta.env`."),
            # wrapped across lines, as a hard-wrapped SKILL.md would carry it
            ("p-rn", "native", "`ios` and `android`",
             "Use a loader such as\n`react-native-config`."),
        ):
            (self.skills / name / "references").mkdir(parents=True)
            (self.skills / name / "SKILL.md").write_text(
                FRONTMATTER.format(name=name)
                + LICENCE_SECTION.format(product=product, platforms=platforms, wiring=wiring))
        (self.skills / "p-exempt-ios").mkdir()
        (self.skills / "p-exempt-ios" / "SKILL.md").write_text(
            FRONTMATTER.format(name="p-exempt-ios"))

    def licence_findings(self):
        findings, _ = lint(self.root, LICENCE_MANIFEST)
        return [f for f in findings if "icence" in f]

    def test_correct_sections_have_no_findings(self):
        self.assertEqual(self.licence_findings(), [])

    def test_missing_section_is_a_finding(self):
        (self.skills / "p-web" / "SKILL.md").write_text(FRONTMATTER.format(name="p-web"))
        self.assertEqual(self.licence_findings(),
                         ["p-web: SKILL.md missing `## Licence key` section"])

    def test_missing_platform_is_a_finding(self):
        sk = self.skills / "p-rn" / "SKILL.md"
        sk.write_text(sk.read_text().replace(" and `android`", ""))
        self.assertEqual(self.licence_findings(), [
            "p-rn: licence-key section does not name `android` "
            "(per internal/skill-auditor/references/licence-platforms.md)",
        ])

    def test_missing_wiring_sentence_is_a_finding(self):
        sk = self.skills / "p-web" / "SKILL.md"
        sk.write_text(sk.read_text().replace("Use the bundler", "Use something"))
        self.assertEqual(self.licence_findings(), [
            "p-web: licence-key section does not carry its key-wiring sentence "
            "(per internal/skill-auditor/references/licence-platforms.md)",
        ])

    def test_missing_wiring_table_is_a_finding_not_a_crash(self):
        ref = self.root / "internal" / "skill-auditor" / "references" / "licence-platforms.md"
        ref.write_text(LICENCE_REFERENCE.split("## Key wiring")[0])
        self.assertEqual(self.licence_findings(), [
            "internal/skill-auditor/references/licence-platforms.md: no `## Key wiring` section",
        ])

    def test_link_outside_the_section_is_a_finding(self):
        (self.skills / "p-web" / "references" / "integration.md").write_text(
            "Get a key at https://ssl.scandit.com\n")
        self.assertEqual(self.licence_findings(), [
            "p-web/references/integration.md: licence provisioning link outside the "
            "`## Licence key` section — point readers at that section instead",
        ])

    def test_allowlisted_link_is_not_a_finding(self):
        (self.skills / "p-web" / "references" / "allowed.md").write_text(
            "Whitelist the dev domain at https://ssl.scandit.com\n")
        self.assertEqual(self.licence_findings(), [])

    def test_unmapped_skill_is_a_finding(self):
        (self.skills / "p-kmp").mkdir()
        (self.skills / "p-kmp" / "SKILL.md").write_text(
            FRONTMATTER.format(name="p-kmp")
            + LICENCE_SECTION.format(product="x", platforms="y", wiring="z"))
        self.assertIn(
            "p-kmp: no row in internal/skill-auditor/references/licence-platforms.md — "
            "add one before the licence-key section can be checked",
            self.licence_findings())

    def test_malformed_reference_is_a_finding_not_a_crash(self):
        ref = self.root / "internal" / "skill-auditor" / "references" / "licence-platforms.md"
        ref.write_text("# no mapping here\n")
        self.assertIn(
            "internal/skill-auditor/references/licence-platforms.md: no `## Skill mapping` section",
            self.licence_findings())


class ResolveLicenceTest(unittest.TestCase):
    MAPPING = {
        "-ios": ("native", ["ios"]),
        "-net-ios": ("other", ["ios", "tvos"]),
        "-bolt": ("native", ["android"]),
        "id-bolt": ("id-bolt", ["webassembly"]),
    }

    def test_longest_suffix_wins(self):
        self.assertEqual(resolve_licence("sparkscan-net-ios", self.MAPPING),
                         ("other", ["ios", "tvos"]))

    def test_exact_name_beats_every_suffix(self):
        self.assertEqual(resolve_licence("id-bolt", self.MAPPING), ("id-bolt", ["webassembly"]))

    def test_unmapped_skill_is_none(self):
        self.assertIsNone(resolve_licence("parser-kmp", self.MAPPING))


if __name__ == "__main__":
    unittest.main()
