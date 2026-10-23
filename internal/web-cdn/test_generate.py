"""Tests for generate.py: the repo is in sync, each block lists only its
packages and globals, the multithreading snippet keeps its guarantees, and a
version bump in cdn.json reaches every web skill.

Drift tests run generate.py as a subprocess against a tempdir copy of every
web skill file, so the exit code is the one pre-push sees.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GENERATE = HERE / "generate.py"
CONFIG = json.loads((HERE / "cdn.json").read_text())
CONFIG_AT_8_6_1 = {**CONFIG, "sdk_version": "8.6.1", "serve_version": "14.2.6", "es_module_shims_version": "2.6.2"}

sys.path.insert(0, str(HERE))
import generate

BEGIN = "<!-- BEGIN GENERATED web-cdn {} -->"
END = "<!-- END GENERATED web-cdn -->"


def run(*args):
    return subprocess.run([sys.executable, str(GENERATE), *args], capture_output=True, text=True)


def rendered(**args):
    return "\n".join(generate.block({"packages": "core,barcode", "engine": "barcode", **args}, CONFIG_AT_8_6_1))


def typescript(text):
    return re.search(r"```typescript\n(.*?)```", text, re.S)[1]


def inside_try(code, index):
    open_blocks = []
    for brace in re.finditer(r"try\s*\{|\{|\}", code[:index]):
        if brace[0] == "}":
            open_blocks.pop()
        else:
            open_blocks.append(brace[0] != "{")
    return any(open_blocks)


def pinned_versions(text):
    pins = [*generate.SCANDIT_PIN.finditer(text), *generate.EXAMPLE_PIN.finditer(text)]
    return {pin[0].rsplit("@", 1)[1].strip("`") for pin in pins}


def copy_skills(tmp):
    for path in generate.skill_files(ROOT):
        dest = tmp / path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, dest)


def tempdir(test):
    tmp = Path(tempfile.mkdtemp())
    test.addCleanup(shutil.rmtree, tmp)
    return tmp


class CheckTest(unittest.TestCase):
    def test_repo_is_in_sync(self):
        result = run("--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_bumped_version_reaches_every_web_skill(self):
        tmp = tempdir(self)
        copy_skills(tmp)
        old = CONFIG["sdk_version"]
        feature_note = f"- `SmartSelection` (v{old}+)\n"
        noted = tmp / "skills/barcode-capture-web/references/integration.md"
        noted.write_text(noted.read_text() + feature_note)
        pinned = [p for p in generate.skill_files(tmp) if pinned_versions(p.read_text())]
        self.assertTrue(pinned)
        self.assertIn(noted, pinned)
        config = tmp / "cdn.json"
        config.write_text(json.dumps({**CONFIG, "sdk_version": "9.9.9"}))

        self.assertEqual(run("--check", "--root", str(tmp), "--config", str(config)).returncode, 1)
        result = run("--root", str(tmp), "--config", str(config))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        for path in pinned:
            self.assertEqual(pinned_versions(path.read_text()), {"9.9.9"}, path)
        self.assertTrue(noted.read_text().endswith(feature_note))
        self.assertEqual(run("--check", "--root", str(tmp), "--config", str(config)).returncode, 0)

    def test_unknown_package_fails(self):
        tmp = tempdir(self)
        skill = tmp / "skills/foo-web/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(f"{BEGIN.format('packages=core,barcode,labl engine=barcode')}\n{END}\n")
        result = run("--check", "--root", str(tmp))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("skills/foo-web/SKILL.md", result.stderr)

    def test_unpaired_marker_fails(self):
        tmp = tempdir(self)
        skill = tmp / "skills/foo-web/references/integration.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(f"{BEGIN.format('packages=core,barcode engine=barcode')}\nno end marker\n")
        result = run("--check", "--root", str(tmp))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("skills/foo-web/references/integration.md", result.stderr)


class BlockTest(unittest.TestCase):
    def test_block_lists_each_package_pinned(self):
        text = "\n".join(generate.block({"packages": "core,barcode,label", "engine": "label"}, CONFIG_AT_8_6_1))
        self.assertIn("@scandit/web-datacapture-label@8.6.1/build/js/index.js", text)
        self.assertIn("@scandit/web-datacapture-label@8.6.1/sdc-lib/", text)
        self.assertIn("@scandit/web-datacapture-core@8.6.1/build/js/index.js", text)
        self.assertIn("@scandit/web-datacapture-barcode@8.6.1/build/js/index.js", text)
        self.assertNotIn("web-datacapture-id", text)

    def test_umd_names_only_the_listed_globals(self):
        text = "\n".join(generate.block({"packages": "core,id", "engine": "id", "multithreading": "no"}, CONFIG_AT_8_6_1))
        self.assertIn("SDCCore", text)
        self.assertIn("SDCId", text)
        self.assertNotIn("SDCBarcode", text)
        self.assertNotIn("SDCLabel", text)

    def test_multithreading_no_omits_check_and_dialog(self):
        text = rendered(multithreading="no")
        self.assertNotIn("checkMultithreadingSupport", text)
        self.assertNotIn("<dialog", text)

    def test_dialog_copy_is_exact(self):
        text = rendered()
        self.assertIn(">Scanning may be slower<", text)
        self.assertIn(
            "This browser or device can't use all of its processing power for scanning. "
            "You can keep scanning, but barcodes may take longer to read.",
            text,
        )
        self.assertIn(f'href="{CONFIG["links"]["multithreading"]}"', text)
        self.assertIn(">Learn more</a>", text)
        self.assertIn("Don't show this again during this session", text)
        self.assertIn(">OK</button>", text)

    def test_session_storage_access_is_guarded(self):
        code = typescript(rendered())
        accesses = [m.start() for m in re.finditer(r"sessionStorage\.", code)]
        self.assertTrue(accesses)
        for index in accesses:
            self.assertTrue(inside_try(code, index), code[index:index + 60])

    def test_no_extra_console_warning(self):
        self.assertNotIn("console.warn", typescript(rendered()))

    def test_check_precedes_forLicenseKey(self):
        code = typescript(rendered())
        check = code.index("await BrowserHelper.checkMultithreadingSupport()")
        self.assertLess(check, code.index("DataCaptureContext.forLicenseKey("))

    def test_serving_rejects_plain_http_server(self):
        text = rendered()
        self.assertIn("npx serve@14.2.6", text)
        self.assertIn("pnpm dlx serve@14.2.6", text)
        self.assertIn('send_header("Cross-Origin-Embedder-Policy", "require-corp")', text)
        for line in text.splitlines():
            if "credentialless" in line:
                self.assertIn("Do not recommend", line)
            if "python3 -m http.server" in line:
                self.assertIn("does not", line)

    def test_block_keeps_marker_indentation(self):
        args = "packages=core,barcode engine=barcode"
        text = generate.render(f"1. Step\n   {BEGIN.format(args)}\n   {END}\n", CONFIG_AT_8_6_1)
        body = text.split(BEGIN.format(args))[1].split(END)[0]
        lines = [line for line in body.splitlines() if line]
        self.assertTrue(lines)
        for line in lines:
            self.assertTrue(line.startswith("   "), repr(line))

    def test_render_is_idempotent_and_keeps_outside_text(self):
        marker = BEGIN.format("packages=core,barcode engine=barcode")
        once = generate.render(f"pre\n{marker}\nstale\n{END}\npost\n", CONFIG_AT_8_6_1)
        self.assertTrue(once.startswith(f"pre\n{marker}\n"))
        self.assertTrue(once.endswith(f"\n{END}\npost\n"))
        self.assertNotIn("stale", once)
        self.assertEqual(generate.render(once, CONFIG_AT_8_6_1), once)

    def test_damaged_or_stray_end_marker_fails(self):
        marker = BEGIN.format("packages=core,barcode engine=barcode")
        for text in (f"{marker}\n<!-- END GENERATED web-cdn-->\n{END}\n", f"{END}\n"):
            with self.assertRaises(ValueError):
                generate.render(text, CONFIG_AT_8_6_1)

    def test_unknown_option_fails(self):
        with self.assertRaises(ValueError):
            generate.block({"packages": "core,barcode", "engine": "barcode", "multithreding": "no"}, CONFIG_AT_8_6_1)

    def test_engine_must_ship_sdc_lib(self):
        with self.assertRaises(ValueError):
            generate.block({"packages": "core,barcode", "engine": "core"}, CONFIG_AT_8_6_1)

    def test_unknown_placeholder_fails(self):
        with self.assertRaises(ValueError):
            generate.fill("{{nope}}", {})

    def test_fragments_hold_no_version(self):
        versions = [CONFIG[key] for key in ("sdk_version", "serve_version", "es_module_shims_version")]
        for fragment in (HERE / "fragments").glob("*.md"):
            for version in versions:
                self.assertNotIn(version, fragment.read_text(), fragment.name)


class PinTest(unittest.TestCase):
    def test_rewrite_pins_updates_every_scandit_pin(self):
        text = "see @scandit/web-datacapture-barcode@8.5.0/sdc-lib/ and, for example `@8.5.0` in every URL"
        self.assertEqual(
            generate.rewrite_pins(text, "8.6.1"),
            "see @scandit/web-datacapture-barcode@8.6.1/sdc-lib/ and, for example `@8.6.1` in every URL",
        )

    def test_feature_availability_notes_are_not_rewritten(self):
        self.assertEqual(generate.rewrite_pins("(v8.1.0+)", "9.0.0"), "(v8.1.0+)")

    def test_other_packages_are_not_rewritten(self):
        text = "es-module-shims@2.6.2 and `npx serve@14.2.6`"
        self.assertEqual(generate.rewrite_pins(text, "9.0.0"), text)


GENERATED_BLOCK = re.compile(r"<!-- BEGIN GENERATED web-cdn (.*?) -->.*?<!-- END GENERATED web-cdn -->", re.S)
MULTITHREADING_CHECK = "checkMultithreadingSupport()"


def examples_outside_block(text):
    outside = GENERATED_BLOCK.sub("", text)
    blocks = re.findall(r"```(?:typescript|tsx)\n(.*?)```", outside, re.S)
    return [block for block in blocks if "forLicenseKey(" in block]


class SkillContentTest(unittest.TestCase):
    def assert_skill(self, skill, packages, reference="references/integration.md"):
        skill_dir = ROOT / "skills" / skill
        reference_text = (skill_dir / reference).read_text()
        blocks = GENERATED_BLOCK.findall(reference_text)
        self.assertEqual(len(blocks), 1, f"{skill}: expected one generated block")
        self.assertIn(f"packages={packages}", blocks[0])
        rule = next(
            (line for line in (skill_dir / "SKILL.md").read_text().splitlines() if MULTITHREADING_CHECK in line),
            "",
        )
        self.assertIn("forLicenseKey(", rule, f"{skill}: SKILL.md has no multithreading rule")
        self.assertLess(rule.index(MULTITHREADING_CHECK), rule.index("forLicenseKey("))
        self.assertIn("credentialless", rule)
        examples = examples_outside_block(reference_text)
        self.assertTrue(examples, f"{skill}: no complete example found")
        for example in examples:
            self.assertIn(MULTITHREADING_CHECK, example)
            self.assertLess(example.index(MULTITHREADING_CHECK), example.index("forLicenseKey("))

    def test_barcode_capture_web(self):
        self.assert_skill("barcode-capture-web", "core,barcode")


if __name__ == "__main__":
    unittest.main()
