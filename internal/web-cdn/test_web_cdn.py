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


def typescript(text, containing):
    blocks = [block for block in re.findall(r"```typescript\n(.*?)```", text, re.S) if containing in block]
    if len(blocks) != 1:
        raise AssertionError(f"expected one typescript block containing {containing!r}, found {len(blocks)}")
    return blocks[0]


def dialog_helper(text):
    return typescript(text, "export function showMultithreadingWarning")


def check_start(text):
    return typescript(text, "forLicenseKey(")


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
        pinned = [p for p in generate.skill_files(tmp) if generate.rewrites_pins(p) and pinned_versions(p.read_text())]
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

    def test_migration_guides_keep_the_versions_they_quote(self):
        tmp = tempdir(self)
        quoted = "npm install @scandit/web-datacapture-core@7.6.0, for example `@7.6.0`\n"
        references = tmp / "skills/foo-web/references"
        references.mkdir(parents=True)
        guides = [references / "migration.md", references / "third-party-migration.md"]
        integration = references / "integration.md"
        for path in (*guides, integration):
            path.write_text(quoted)

        result = run("--root", str(tmp))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        for guide in guides:
            self.assertEqual(guide.read_text(), quoted, guide.name)
        self.assertEqual(pinned_versions(integration.read_text()), {CONFIG["sdk_version"]})
        result = run("--check", "--root", str(tmp))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

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

    def test_umd_loads_only_the_listed_packages(self):
        text = "\n".join(generate.block({"packages": "core,id", "engine": "id", "multithreading": "no"}, CONFIG_AT_8_6_1))
        per_skill = [line for line in text.splitlines() if "exposes exactly one global" in line]
        self.assertEqual(len(per_skill), 2)
        self.assertIn("SDCCore", per_skill[0])
        self.assertIn("SDCId", per_skill[1])
        scripts = re.findall(r'<script src="[^"]*umd/index.js"', text)
        self.assertEqual(len(scripts), 2)
        self.assertNotIn("web-datacapture-parser@", text)

    def test_umd_documents_all_five_globals(self):
        text = rendered()
        for name in ("SDCCore", "SDCBarcode", "SDCLabel", "SDCId", "SDCParser"):
            self.assertIn(f"`{name}`", text)
        self.assertEqual(
            {pkg["global"] for pkg in CONFIG["packages"].values()},
            {"SDCCore", "SDCBarcode", "SDCLabel", "SDCId", "SDCParser"},
        )

    def test_parser_bundle_only_needs_core(self):
        text = "\n".join(generate.block({"packages": "core,id", "engine": "id", "multithreading": "no"}, CONFIG_AT_8_6_1))
        parser_note = next(line for line in text.splitlines() if "`SDCParser` is only for" in line)
        self.assertNotIn("barcode", parser_note)
        self.assertIn("after the core bundle", parser_note)

    def test_parser_is_not_an_engine(self):
        with self.assertRaises(ValueError):
            generate.block({"packages": "core,barcode,parser", "engine": "parser"}, CONFIG_AT_8_6_1)

    def test_multithreading_no_omits_check_and_dialog(self):
        text = rendered(multithreading="no")
        self.assertNotIn("checkMultithreadingSupport", text)
        self.assertNotIn("showMultithreadingWarning", text)
        self.assertNotIn("<dialog", text)

    def test_dialog_copy_is_exact(self):
        text = rendered()
        self.assertIn(">Scanning may be slower<", text)
        self.assertIn(
            "This browser or device can't use all of its processing power for scanning. "
            "You can keep scanning, but scanning may take longer.",
            text,
        )
        self.assertIn(f'href="{CONFIG["links"]["multithreading"]}"', text)
        self.assertIn(">Learn more</a>", text)
        self.assertIn("Don't show this again during this session", text)
        self.assertIn(">OK</button>", text)

    def test_dialog_helper_is_a_standalone_module(self):
        helper = dialog_helper(rendered())
        for name in ("showMultithreadingWarning", "isMultithreadingWarningDismissed", "rememberMultithreadingWarningDismissed"):
            self.assertIn(f"export function {name}()", helper)
        self.assertNotIn("forLicenseKey", helper)
        self.assertNotIn("await", helper)
        self.assertNotIn("import ", helper)

    def test_dialog_helper_needs_no_page_markup(self):
        text = rendered()
        html_dialogs = [block for block in re.findall(r"```html\n(.*?)```", text, re.S) if "<dialog" in block]
        self.assertEqual(html_dialogs, [])
        helper = dialog_helper(text)
        self.assertIn('document.querySelector("dialog#multithreading-warning")', helper)
        self.assertIn('document.createElement("dialog")', helper)
        self.assertIn('dialog.id = "multithreading-warning"', helper)
        self.assertIn("`multithreading-warning.js`", text)
        self.assertIn('"./multithreading-warning"', text)

    def test_dialog_shows_at_most_once_per_page_load(self):
        helper = dialog_helper(rendered())
        self.assertIn("let multithreadingWarningShown = false", helper)
        shown = helper.index("multithreadingWarningShown = true")
        self.assertLess(helper.index("if (multithreadingWarningShown"), shown)
        self.assertLess(shown, helper.index(".showModal()"))

    def test_check_runs_in_parallel_with_forLicenseKey(self):
        start = check_start(rendered())
        self.assertIn('import { showMultithreadingWarning } from "./multithreading-warning.js";', start)
        self.assertNotIn("await BrowserHelper.checkMultithreadingSupport()", start)
        check = start.index("BrowserHelper.checkMultithreadingSupport()")
        license_key = start.index("await DataCaptureContext.forLicenseKey(")
        self.assertLess(check, license_key)
        not_awaited = start[check:license_key]
        self.assertIn(".then(", not_awaited)
        self.assertIn("showMultithreadingWarning()", not_awaited)
        self.assertIn(".catch(", not_awaited)

    def test_session_storage_access_is_guarded(self):
        code = dialog_helper(rendered())
        accesses = [m.start() for m in re.finditer(r"sessionStorage\.", code)]
        self.assertTrue(accesses)
        for index in accesses:
            self.assertTrue(inside_try(code, index), code[index:index + 60])

    def test_no_extra_console_warning(self):
        text = rendered()
        self.assertNotIn("console.warn", dialog_helper(text))
        self.assertNotIn("console.warn", check_start(text))

    def test_python_server_listens_only_on_localhost(self):
        text = rendered()
        self.assertIn("open `http://localhost:8000`", text)
        self.assertIn('ThreadingHTTPServer(("127.0.0.1", 8000), CrossOriginIsolatedHandler)', text)
        self.assertNotIn('("", 8000)', text)

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
AWAITED_CHECK = re.compile(r"await\W+BrowserHelper\.checkMultithreadingSupport", re.I)
HELPER_IMPORT = 'import { showMultithreadingWarning } from "./multithreading-warning";'
HELPER_POINTER = "import `showMultithreadingWarning` from the `multithreading-warning` helper module"
OLD_HELPER_POINTERS = ("dialog markup and the `showMultithreadingWarning()` helper", "Define the helper in the same module")


def examples_outside_block(text):
    outside = GENERATED_BLOCK.sub("", text)
    blocks = re.findall(r"```(?:typescript|tsx)\n(.*?)```", outside, re.S)
    return [block for block in blocks if "forLicenseKey(" in block]


def web_skill_texts_outside_blocks():
    paths = [*generate.skill_files(ROOT), *sorted(ROOT.glob("skills/*-web/**/*.tsx"))]
    return {path.relative_to(ROOT): GENERATED_BLOCK.sub("", path.read_text()) for path in paths}


def setup_checklist(text):
    lines = GENERATED_BLOCK.sub("", text).splitlines()
    start = next(index for index, line in enumerate(lines) if line.rstrip().endswith("checklist:"))
    items = []
    for line in lines[start + 1:]:
        if re.match(r"\d+\. ", line):
            items.append(line)
        elif items and not line.startswith(" "):
            break
    return items


def react_example(skill):
    text = (ROOT / "skills" / skill / "references/integration.md").read_text()
    return next(
        block
        for block in re.findall(r"```tsx\n(.*?)```", GENERATED_BLOCK.sub("", text), re.S)
        if "forLicenseKey(" in block
    )


def sparkscan_provider_in_guide():
    text = (ROOT / "skills/sparkscan-web/references/react.md").read_text()
    return next(block for block in re.findall(r"```tsx\n(.*?)```", text, re.S) if "forLicenseKey(" in block)


def sparkscan_provider_fixture():
    return (ROOT / "skills/sparkscan-web/references/fixtures/ScanditProvider.tsx").read_text()


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
        self.assertIn("in parallel", rule)
        self.assertIn(HELPER_POINTER, rule)
        self.assertIn("component state", rule)
        self.assertIn("credentialless", rule)
        examples = examples_outside_block(reference_text)
        self.assertTrue(examples, f"{skill}: no complete example found")
        for example in examples:
            self.assertIn(MULTITHREADING_CHECK, example)
            self.assertLess(example.index(MULTITHREADING_CHECK), example.index("forLicenseKey("))

    def test_barcode_capture_web(self):
        self.assert_skill("barcode-capture-web", "core,barcode")

    def test_matrixscan_batch_web(self):
        self.assert_skill("matrixscan-batch-web", "core,barcode")

    def test_matrixscan_ar_web(self):
        self.assert_skill("matrixscan-ar-web", "core,barcode")

    def test_sparkscan_web(self):
        self.assert_skill("sparkscan-web", "core,barcode")

    def test_label_capture_web(self):
        self.assert_skill("label-capture-web", "core,barcode,label")
        text = (ROOT / "skills/label-capture-web/references/integration.md").read_text()
        self.assertIn("engine=label", GENERATED_BLOCK.search(text).group(1))
        skill = (ROOT / "skills/label-capture-web/SKILL.md").read_text()
        self.assertIn("pin one exact version", skill)

    def test_id_capture_web(self):
        skill_dir = ROOT / "skills/id-capture-web"
        text = (skill_dir / "references/cdn.md").read_text()
        blocks = GENERATED_BLOCK.findall(text)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0], "packages=core,id engine=id multithreading=no")
        skill = (skill_dir / "SKILL.md").read_text()
        self.assertIn("(references/cdn.md)", skill)
        self.assertIn("pin one exact version", skill)
        for path in skill_dir.rglob("*.md"):
            content = path.read_text()
            for forbidden in ("checkMultithreadingSupport", "showMultithreadingWarning", "multithreading-warning"):
                self.assertNotIn(forbidden, content, f"{path}: {forbidden}")

    def test_no_web_skill_waits_for_the_check(self):
        for path, text in web_skill_texts_outside_blocks().items():
            self.assertIsNone(AWAITED_CHECK.search(text), path)

    def test_examples_import_the_dialog_helper(self):
        for path, text in web_skill_texts_outside_blocks().items():
            for example in re.findall(r"```(?:typescript|tsx)\n(.*?)```", text, re.S):
                if "showMultithreadingWarning(" in example and "import " in example:
                    self.assertIn(HELPER_IMPORT, example, path)

    def test_helper_pointers_name_the_module(self):
        for path, text in web_skill_texts_outside_blocks().items():
            for old in OLD_HELPER_POINTERS:
                self.assertNotIn(old, text, path)
            if "showMultithreadingWarning" in text:
                self.assertIn(HELPER_POINTER.lower(), text.lower(), path)

    def test_setup_checklists_add_the_helper_module(self):
        for skill in ("barcode-capture-web", "matrixscan-batch-web", "matrixscan-ar-web", "sparkscan-web", "label-capture-web"):
            text = (ROOT / "skills" / skill / "references/integration.md").read_text()
            dialog_steps = [item for item in setup_checklist(text) if "dialog" in item]
            self.assertEqual(len(dialog_steps), 1, skill)
            self.assertIn("`multithreading-warning.js`", dialog_steps[0])
            self.assertIn("no markup", dialog_steps[0])

    def test_barcode_capture_web_react_example_checks_cancelled_before_flag(self):
        self.assert_react_check_waits_for_cancelled(react_example("barcode-capture-web"))

    def test_matrixscan_batch_web_react_example_checks_cancelled_before_flag(self):
        self.assert_react_check_waits_for_cancelled(react_example("matrixscan-batch-web"))

    def test_sparkscan_web_react_guide_checks_cancelled_before_flag(self):
        self.assert_react_check_waits_for_cancelled(sparkscan_provider_in_guide())

    def test_sparkscan_web_react_fixture_checks_cancelled_before_flag(self):
        self.assert_react_check_waits_for_cancelled(sparkscan_provider_fixture())

    def assert_react_check_waits_for_cancelled(self, code):
        self.assertIn("let cancelled = false", code)
        self.assertIn("cancelled = true;", code)
        check = code.index("BrowserHelper.checkMultithreadingSupport()")
        self.assertLess(check, code.index("DataCaptureContext.forLicenseKey("))
        self.assertIn(".catch(", code[check:])
        on_result = code[check:code.index(".catch(", check)]
        self.assertIn(".then(", on_result)
        self.assertIn("if (cancelled) return;", on_result)
        self.assertIn("multithreadingWarningShown = true", on_result)
        self.assertLess(on_result.index("if (cancelled) return;"), on_result.index("multithreadingWarningShown = true"))

    def test_sparkscan_web_has_no_console_warn_for_multithreading(self):
        text = (ROOT / "skills/sparkscan-web/references/integration.md").read_text()
        self.assertNotIn("console.warn", text)

    def test_sparkscan_web_migration_snippet_checks_multithreading_first(self):
        text = (ROOT / "skills/sparkscan-web/references/migration.md").read_text()
        after = text[text.index("**New (v8):**"):]
        snippet = re.search(r"```typescript\n(.*?)```", after, re.S).group(1)
        self.assertIn(MULTITHREADING_CHECK, snippet)
        self.assertIn(HELPER_IMPORT, snippet)
        self.assertLess(snippet.index(MULTITHREADING_CHECK), snippet.index("DataCaptureContext.forLicenseKey("))
        self.assertIn("references/integration.md", after[: after.index("```typescript")])

    def test_sparkscan_web_react_provider_shows_dialog_from_state(self):
        for provider in (sparkscan_provider_in_guide(), sparkscan_provider_fixture()):
            self.assertNotIn("showMultithreadingWarning(", provider)
            self.assertIn("<dialog", provider)
            self.assertIn("scandit-multithreading-warning-dismissed", provider)
            component_start = provider.index("export function ScanditProvider")
            self.assertIn("let multithreadingWarningShown = false", provider[:component_start])
            accesses = [match.start() for match in re.finditer(r"sessionStorage", provider)]
            self.assertTrue(accesses)
            for index in accesses:
                self.assertTrue(inside_try(provider, index), "sessionStorage access outside try")
            self.assertNotIn("console.warn", provider)

    def test_sparkscan_web_single_threaded_fallback_leaves_dialog_out(self):
        text = (ROOT / "skills/sparkscan-web/references/troubleshooting.md").read_text()
        fallback = next(p for p in text.split("\n\n") if p.startswith("**Single-threaded fallback"))
        self.assertIn("multithreading dialog", fallback)
        credentialless = next(line for line in text.splitlines() if "COEP: credentialless" in line)
        self.assertIn("dialog", credentialless)

    def test_headers_fragment_scopes_credentialless_rule_to_sdk_set_up(self):
        text = (ROOT / "internal/web-cdn/fragments/headers.md").read_text()
        rule = next(line for line in text.splitlines() if "Do not recommend" in line)
        self.assertIn("SDK set-up", rule)

    def test_matrixscan_ar_web_migration_snippet_checks_multithreading_first(self):
        text = (ROOT / "skills/matrixscan-ar-web/references/migration.md").read_text()
        after = text[text.index("**After (BarcodeAr):**"):]
        snippet = re.search(r"```typescript\n(.*?)```", after, re.S).group(1)
        self.assertIn(MULTITHREADING_CHECK, snippet)
        self.assertIn(HELPER_IMPORT, snippet)
        self.assertLess(snippet.index(MULTITHREADING_CHECK), snippet.index("DataCaptureContext.forLicenseKey("))
        self.assertIn("references/integration.md", after[: after.index("```typescript")])

    def test_matrixscan_ar_web_has_no_console_warn_for_multithreading(self):
        text = (ROOT / "skills/matrixscan-ar-web/references/integration.md").read_text()
        self.assertNotIn("console.warn", text)

    def test_matrixscan_batch_web_has_no_console_warn_for_multithreading(self):
        text = (ROOT / "skills/matrixscan-batch-web/references/integration.md").read_text()
        self.assertNotIn("console.warn", text)

    def test_barcode_capture_web_react_example_shows_dialog_from_state(self):
        self.assert_react_example_shows_dialog_from_state("barcode-capture-web")

    def test_matrixscan_batch_web_react_example_shows_dialog_once_per_page_load(self):
        self.assert_react_example_shows_dialog_from_state("matrixscan-batch-web")

    def assert_react_example_shows_dialog_from_state(self, skill):
        react = react_example(skill)
        self.assertNotIn("showMultithreadingWarning(", react)
        self.assertIn("<dialog", react)
        component_start = react.index("export const")
        self.assertIn("let multithreadingWarningShown = false", react[:component_start])
        accesses = [match.start() for match in re.finditer(r"sessionStorage", react)]
        self.assertTrue(accesses)
        for index in accesses:
            self.assertTrue(inside_try(react, index), "sessionStorage access outside try")


PARALLEL_CHECK_ASSERTION = (
    "`BrowserHelper.checkMultithreadingSupport()` is started no later than `DataCaptureContext.forLicenseKey(` "
    "and set-up does not wait for it; when it resolves false the dialog is shown (semantic)"
)


def eval_assertions(skill):
    path = ROOT / "evals" / skill / "integration-evals.json"
    return [assertion["text"] for case in json.loads(path.read_text())["evals"] for assertion in case["assertions"]]


class EvalTest(unittest.TestCase):
    def test_eval_assertions_do_not_require_awaiting_the_check(self):
        for path in sorted(ROOT.glob("evals/*-web/integration-evals.json")):
            for text in eval_assertions(path.parent.name):
                self.assertIsNone(AWAITED_CHECK.search(text), f"{path.relative_to(ROOT)}: {text}")

    def test_expected_outputs_do_not_await_the_check(self):
        for path in sorted(ROOT.glob("evals/*-web/integration-evals.json")):
            for case in json.loads(path.read_text())["evals"]:
                self.assertIsNone(AWAITED_CHECK.search(case["expected_output"]), f"{path.relative_to(ROOT)} eval {case['id']}")

    def test_evals_assert_the_parallel_check(self):
        for skill in ("barcode-capture-web", "matrixscan-batch-web", "matrixscan-ar-web", "sparkscan-web", "label-capture-web"):
            self.assertIn(PARALLEL_CHECK_ASSERTION, eval_assertions(skill), skill)

    def test_id_capture_web_eval_still_rules_the_check_out(self):
        self.assertIn("`BrowserHelper.checkMultithreadingSupport` is NOT used (semantic)", eval_assertions("id-capture-web"))


REACT_DIALOGS = (
    "skills/barcode-capture-web/references/integration.md",
    "skills/matrixscan-batch-web/references/integration.md",
    "skills/sparkscan-web/references/react.md",
    "skills/sparkscan-web/references/fixtures/ScanditProvider.tsx",
)


def squeezed(text):
    return " ".join(text.split())


def generated_dialog_copy():
    dialog = re.search(r'<form method="dialog">.*?</form>', rendered(), re.S)[0]
    copy = {
        "title": re.search(r"<h2>(.*?)</h2>", dialog)[1],
        "text": re.search(r"<p>(This browser.*?)</p>", dialog)[1],
        "link text": re.search(r"<a [^>]*>(.*?)</a>", dialog)[1],
        "checkbox label": re.search(r"/> (.*?)</label>", dialog)[1],
        "button": re.search(r"<button[^>]*>(.*?)</button>", dialog)[1],
        "href": re.search(r'<a href="(.*?)"', dialog)[1],
    }
    return copy


def missing_dialog_copy(text):
    haystack = squeezed(text)
    return [name for name, expected in generated_dialog_copy().items() if squeezed(expected) not in haystack]


class ReactDialogDriftTest(unittest.TestCase):
    def test_generated_dialog_copy_has_every_part(self):
        self.assertEqual(len(generated_dialog_copy()), 6)

    def test_react_dialogs_repeat_the_generated_copy(self):
        for path in REACT_DIALOGS:
            text = (ROOT / path).read_text()
            self.assertEqual(missing_dialog_copy(text), [], path)

    def test_drift_in_a_react_dialog_is_detected(self):
        text = (ROOT / REACT_DIALOGS[0]).read_text()
        drifted = text.replace("Scanning may be slower", "Scanning may be slow")
        self.assertEqual(missing_dialog_copy(drifted), ["title"])


if __name__ == "__main__":
    unittest.main()
