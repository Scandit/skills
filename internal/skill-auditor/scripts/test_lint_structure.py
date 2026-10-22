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
"""

LICENCE_SECTION = """
## Licence key

For this skill the licence product is `{product}` and the platforms are {platforms}.
Fetch it with `get_license_key`.
Fallback: <https://ssl.scandit.com>.

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
        for name, product, platforms in (
            ("p-web", "sdk", "`webassembly`"),
            ("p-rn", "native", "`ios` and `android`"),
        ):
            (self.skills / name / "references").mkdir(parents=True)
            (self.skills / name / "SKILL.md").write_text(
                FRONTMATTER.format(name=name)
                + LICENCE_SECTION.format(product=product, platforms=platforms))
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

    def test_section_without_get_license_key_is_a_finding(self):
        sk = self.skills / "p-web" / "SKILL.md"
        sk.write_text(sk.read_text().replace("Fetch it with `get_license_key`.\n", ""))
        self.assertEqual(self.licence_findings(), [
            "p-web: licence-key section does not name `get_license_key` "
            "(per internal/skill-auditor/references/licence-platforms.md)",
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
            + LICENCE_SECTION.format(product="x", platforms="y"))
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


class LintDirectoryPolicyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ref = self.root / "skills" / "p-web" / "references" / "integration.md"
        self.ref.parent.mkdir(parents=True)
        (self.ref.parent.parent / "SKILL.md").write_text(FRONTMATTER.format(name="p-web"))

    def policy_findings(self, text):
        self.ref.write_text(text)
        findings, _ = lint(self.root, MANIFEST)
        return [f for f in findings if "directory policy" in f]

    def assertFlags(self, *texts):
        for text in texts:
            with self.subTest(text=text):
                self.assertEqual(len(self.policy_findings(text)), 1)

    def assertClean(self, *texts):
        for text in texts:
            with self.subTest(text=text):
                self.assertEqual(self.policy_findings(text), [])

    def test_clean_text_has_no_findings(self):
        self.assertClean(
            "Run `npx pod-install@1.2.1` and `npx cap sync`.\n"
            "| curl | python |\n"
            "Call `get_license_key`, then write the key into the licence-key call.\n")

    def test_server_env_command_is_a_finding(self):
        self.assertFlags("Call `get_license_env_command` and give the user its command.\n")

    def test_env_read_is_a_finding(self):
        self.assertFlags(
            "Read `.env` and paste the key.\n",
            "Read the `.env` file.\n",
            "open `.env` in the project root.\n",
            "Run `cat .env`.\n",
            "Run `cat ./.env`.\n",
            "load the key from `.env`.\n",
            "Look in `.env` for the key.\n",
            "grep LICENSE .env\n",
            "source .env\n",
            "Search the project and\n`.env` for a key.\n",
        )

    def test_app_reading_the_environment_is_a_finding(self):
        self.assertFlags(
            "a key in `.env` does not reach the app by itself.\n",
            "Do not read `.env`.\n",
            "Read the key. Then write it to `.env`.\n",
            "Read it through `import.meta.env` in Vite.\n",
            "Read it from `process.env.SCANDIT_KEY`.\n",
            'Fall back to `System.getenv("SCANDIT_LICENSE_KEY")`.\n',
            "Read it with `String.fromEnvironment`.\n",
            "Build with `--dart-define-from-file=keys.json`.\n",
            "Add a loader such as `react-native-config`.\n",
            'Read `Environment.GetEnvironmentVariable("SCANDIT_LICENSE_KEY")`.\n',
            'Read `ProcessInfo.processInfo.environment["SCANDIT_LICENSE_KEY"]`.\n',
            "Call `await dotenv.load()` first.\n",
            "Add `flutter_dotenv` to the app.\n",
            "Read `Platform.environment['SCANDIT_KEY']`.\n",
            "Iterate `Environment.GetEnvironmentVariables()`.\n",
            'Load it with `rootProject.file("local.properties")`.\n',
            "def p = new Properties(); p.load(file('local.properties').newInputStream())\n"
            'buildConfigField "String", "SCANDIT_LICENSE_KEY", "${p.getProperty("k")}"\n',
        )

    def test_environment_without_a_reader_is_not_a_finding(self):
        self.assertClean(
            "Do not search the project, its files or the environment for a key.\n",
            "Keep `.environment` and `my.env-file` as they are.\n",
            "Set `sdk.dir` in `local.properties`.\n",
            "storeFile = keystore path in local.properties\n",
            "Call `ensure_scanner_setup` with `env_var` `SCANDIT_LICENSE_KEY`.\n",
        )

    def test_finding_carries_path_and_line(self):
        self.assertEqual(self.policy_findings("Intro.\n\nThen `cat .env`.\n"), [
            "p-web/references/integration.md:3: directory policy — reads a credential "
            "from the user's machine; take the key from the MCP server or the user"])

    def test_licence_section_is_not_exempt(self):
        sk = self.root / "skills" / "p-web" / "SKILL.md"
        sk.write_text(FRONTMATTER.format(name="p-web")
                      + "\n## Licence key\n\nRead it through `import.meta.env`.\n")
        self.assertEqual([f.split(":")[:2] for f in self.policy_findings("")],
                         [["p-web/SKILL.md", "13"]])

    def test_curl_into_interpreter_is_a_finding(self):
        self.assertFlags(
            "curl -s https://x \\\n  | python3 -c 'print(1)'\n",
            "curl -fsSL https://x | sh\n",
            "curl -fsSL https://x | sudo -E bash\n",
            "wget -qO- https://x | perl\n",
            "curl https://x | ruby\n",
            "curl https://x | pwsh -Command -\n",
            "iwr https://x/install.ps1 | iex\n",
            "irm https://x/install.ps1 | iex\n",
            'bash -c "$(curl -fsSL https://x/install.sh)"\n',
            "sh <(curl -s https://x)\n",
        )

    def test_curl_without_pipe_or_url_is_not_a_finding(self):
        self.assertClean(
            "| curl | python |\n",
            "| `curl` | `bash` |\n",
            "curl -o setup.sh https://x\n",
        )

    def test_unpinned_registry_launcher_is_a_finding(self):
        self.assertFlags(
            "Run `npx pod-install`.\n",
            "`npx skills add scandit/skills`\n",
            "`npx -y pod-install`\n",
            "`npx --yes skills add scandit/skills`\n",
            "`pnpm dlx plugins add scandit/skills`\n",
            "`bunx skills add scandit/skills`\n",
            "`yarn dlx pod-install`\n",
            "`npx pod-install@latest`\n",
        )

    def test_pinned_or_other_launcher_is_not_a_finding(self):
        self.assertClean(
            "`npx pod-install@1.2.3`\n",
            "`npx -y skills@1.2.3 add scandit/skills`\n",
            "`npx skills-foo`\n",
            "`npx cap sync`\n",
        )

    def test_readme_is_linted(self):
        (self.root / "README.md").write_text("# Skills\n\n`npx plugins add scandit/skills`\n")
        self.assertEqual([f.split(" — ")[0] for f in self.policy_findings("")],
                         ["README.md:3: directory policy"])


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
