import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import report
import run
import score

EVALS_DIR = score.eval_dir("barcode-capture-flutter")
SKILL = "barcode-capture-flutter"
SUITE = score.SUITES[SKILL]
ENTRIES = {e["id"]: e for e in json.loads((EVALS_DIR / "third-party-migration-evals.json").read_text())["evals"]}

MIGRATED_PAGE = """
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
final settings = BarcodeCaptureSettings()
  ..enableSymbologies({Symbology.ean13Upca, Symbology.code128, Symbology.qr});
"""
GATE_OK = (0, "Analyzing lib...\nNo issues found!\nANALYZE-PASS: x\n")
GATE_TWO_ERRORS = (
    1,
    "  error • Undefined name 'MobileScanner' • lib/a.dart:1:2 • undefined_identifier\n"
    "  error • Target of URI doesn't exist • lib/a.dart:3:4 • uri_does_not_exist\n"
    "ANALYZE-FAIL: x\n",
)


def gate_returning(result):
    return lambda _command: result


class ScoreCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def output_for(self, eval_id, main_text):
        name = Path(ENTRIES[eval_id]["files"][0]).name
        (self.tmp / "lib").mkdir(exist_ok=True)
        (self.tmp / "lib" / name).write_text(main_text)
        return self.tmp

    def score(self, eval_id, main_text, gate_result):
        out = self.output_for(eval_id, main_text)
        return score.score_eval(SUITE, ENTRIES[eval_id], out, EVALS_DIR, gate_returning(gate_result))

    def test_known_good_output_compiles_and_keeps_symbologies(self):
        row = self.score(1, MIGRATED_PAGE, GATE_OK)
        self.assertIs(row["compiles"], True)
        self.assertEqual(row["errors_left"], 0)
        self.assertIs(row["kept"], True)

    def test_unmigrated_fixture_fails_and_keeps_nothing(self):
        original = (EVALS_DIR / ENTRIES[1]["files"][0]).read_text()
        row = self.score(1, original, GATE_TWO_ERRORS)
        self.assertIs(row["compiles"], False)
        self.assertEqual(row["errors_left"], 2)
        self.assertIs(row["kept"], False)

    def test_expected_symbologies_per_fixture(self):
        expected = {
            1: ["ean13upca", "code128", "qr"],
            5: ["qr"],
            2: score.load_mapping()["default_set"],
            7: score.load_mapping()["default_set"],
        }
        for eval_id, ids in expected.items():
            with self.subTest(eval_id=eval_id):
                row = self.score(eval_id, "", GATE_OK)
                self.assertEqual(sorted(row["expected"]), sorted(ids))

    def test_narrowing_to_qr_is_not_kept(self):
        row = self.score(1, "settings.enableSymbologies({Symbology.qr});", GATE_OK)
        self.assertIs(row["kept"], False)
        self.assertIs(row["narrowed"], False)
        self.assertIn("code128", row["missing"])
        self.assertNotIn("qr", row["missing"])

    def test_default_all_original_narrowed_is_kept(self):
        row = self.score(2, "settings.enableSymbologies({Symbology.qr});", GATE_OK)
        self.assertIs(row["kept"], True)
        self.assertIs(row["narrowed"], True)
        self.assertEqual(row["found"], ["qr"])
        self.assertEqual(report.kept_cell(row), "1/12 narrowed (enabled: qr)")

    def test_default_all_original_with_nothing_enabled_is_not_kept(self):
        row = self.score(2, "// no symbologies", GATE_OK)
        self.assertIs(row["kept"], False)
        self.assertIs(row["narrowed"], False)

    def test_symbologies_enabled_in_migrated_stub_count(self):
        stubs = self.tmp / "lib" / "stubs"
        stubs.mkdir(parents=True)
        (stubs / Path(ENTRIES[5]["files"][1]).name).write_text("settings.enableSymbologies({Symbology.qr});")
        row = self.score(5, "// no settings here", GATE_OK)
        self.assertIs(row["kept"], True)

    def test_commented_out_symbology_does_not_count(self):
        text = MIGRATED_PAGE.replace("Symbology.code128", "/* Symbology.code128 */ // Symbology.code128\n Symbology.qr")
        row = self.score(1, text, GATE_OK)
        self.assertEqual(row["missing"], ["code128"])

    def found(self, text, eval_id=2):
        return self.score(eval_id, text, GATE_OK)["found"]

    def test_switch_over_every_symbology_does_not_count(self):
        cases = "\n".join(f"case Symbology.{n}: break;" for n in ["qr", "code128", "ean8", "aztec"])
        text = f"s..enableSymbologies({{Symbology.qr}});\nswitch (b.symbology) {{ {cases} }}"
        self.assertEqual(self.found(text), ["qr"])

    def test_symbology_in_string_literal_does_not_count(self):
        text = "s.enableSymbologies({Symbology.ean8});\nfinal a = 'Symbology.qr'; final b = \"x(Symbology.qr\";"
        self.assertEqual(self.found(text), ["ean8"])

    def test_identifier_argument_resolves_to_its_collection(self):
        text = (
            "static const _all = <Symbology>{Symbology.qr, Symbology.aztec};\n"
            "s..enableSymbologies(allowsAll ? _all : config.allowedFormats);"
        )
        self.assertEqual(sorted(self.found(text)), ["aztec", "qr"])

    def test_enable_symbology_true_counts_and_false_does_not(self):
        text = (
            "s..enableSymbology(Symbology.qr, true)\n..enableSymbology(Symbology.ean8, false);\n"
            "s.settingsForSymbology(Symbology.aztec).isEnabled = true;"
        )
        self.assertEqual(sorted(self.found(text)), ["aztec", "qr"])

    def test_exit_one_without_error_lines_is_resolve_fail(self):
        row = self.score(1, MIGRATED_PAGE, (1, "Because x depends on y, version solving failed.\nANALYZE-FAIL: x\n"))
        self.assertEqual(row["status"], "resolve-fail")
        self.assertIs(row["compiles"], False)

    def test_gate_skip_is_not_a_failure(self):
        row = self.score(1, MIGRATED_PAGE, (3, "ANALYZE-SKIP: flutter not found\n"))
        self.assertEqual(row["status"], "skip")
        self.assertIsNone(row["compiles"])

    def test_formats_list_parsing(self):
        default = score.load_mapping()["default_set"]
        cases = {
            "formats: [BarcodeFormat.all]": default,
            "formats: const <BarcodeFormat>[BarcodeFormat.ean13, BarcodeFormat.upcA, BarcodeFormat.aztec]":
                ["ean13upca", "aztec"],
            "formats: [BarcodeFormat.unknown, BarcodeFormat.qrCode]": ["qr"],
            "formats: [BarcodeFormat.unknown]": default,
            "// formats: [BarcodeFormat.qrCode]\nMobileScanner()": default,
        }
        for source, ids in cases.items():
            with self.subTest(source=source):
                self.assertEqual(score.expected_symbologies(source, SUITE, score.load_mapping()), ids)

    def test_missing_stub_is_not_passed_to_gate(self):
        commands = []
        out = self.output_for(2, MIGRATED_PAGE)
        score.score_eval(SUITE, ENTRIES[2], out, EVALS_DIR, lambda c: commands.append(c) or GATE_OK)
        self.assertEqual(len(commands[0]), 3)

    def test_missing_output_file(self):
        row = score.score_eval(SUITE, ENTRIES[1], self.tmp, EVALS_DIR, gate_returning(GATE_OK))
        self.assertEqual(row["status"], "missing")
        self.assertIsNone(row["compiles"])


def ts_entries(skill):
    evals_dir = score.eval_dir(skill)
    entries = json.loads((evals_dir / "third-party-migration-evals.json").read_text())["evals"]
    return evals_dir, score.SUITES[skill], {e["id"]: e for e in entries}


RN_DIR, RN, RN_ENTRIES = ts_entries("barcode-capture-rn")
CAP_DIR, CAP, CAP_ENTRIES = ts_entries("barcode-capture-capacitor")
RN_AIO_SCREEN = """
import { Symbology } from 'scandit-react-native-datacapture-barcode';
export const Screen = () => (
  <BarcodeCaptureAioView symbologies={[Symbology.EAN13UPCA, Symbology.Code128, Symbology.QR]} didScan={onScan} />
);
"""
TS_GATE_OK = (0, "GATE-PASS: x\n")
TS_GATE_TWO_ERRORS = (
    1,
    "src/A.tsx(14,8): error TS2307: Cannot find module 'react-native-vision-camera'.\n"
    "src/A.tsx(30,3): error TS2304: Cannot find name 'useCodeScanner'.\nGATE-FAIL: x\n",
)


class TsScoreCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def score(self, suite, evals_dir, entry, texts, gate_result=TS_GATE_OK, commands=None, **kwargs):
        for name, text in zip(score.fixture_paths(suite, entry), texts):
            (self.tmp / name).write_text(text)

        def gate(command):
            if commands is not None:
                commands.append(command)
            return gate_result
        return score.score_eval(suite, entry, self.tmp, evals_dir, gate, **kwargs)

    def test_rn_good_output_compiles_and_keeps(self):
        row = self.score(RN, RN_DIR, RN_ENTRIES[1], [RN_AIO_SCREEN])
        self.assertIs(row["compiles"], True)
        self.assertIs(row["kept"], True)

    def test_rn_unmigrated_output_counts_ts_errors(self):
        original = (RN_DIR / RN_ENTRIES[1]["files"][0]).read_text()
        row = self.score(RN, RN_DIR, RN_ENTRIES[1], [original], TS_GATE_TWO_ERRORS)
        self.assertIs(row["compiles"], False)
        self.assertEqual(row["leftover_imports"], 1)
        self.assertEqual(row["errors_left"], 3)
        self.assertIs(row["kept"], False)

    def test_rn_expected_symbologies(self):
        default = score.load_mapping()["default_set"]
        expected = {1: ["ean13upca", "code128", "qr"], 2: default, 3: ["ean13upca", "code128", "qr"]}
        for eval_id, ids in expected.items():
            with self.subTest(eval_id=eval_id):
                self.assertEqual(self.score(RN, RN_DIR, RN_ENTRIES[eval_id], [""])["expected"], ids)

    def test_capacitor_mlkit_ean13_maps_to_ean13upca(self):
        ids = score.expected_symbologies("formats: [BarcodeFormat.Ean13]", CAP, score.load_mapping())
        self.assertEqual(ids, ["ean13upca"])

    def test_capacitor_id1_unions_both_lists(self):
        row = self.score(CAP, CAP_DIR, CAP_ENTRIES[1], [""])
        self.assertEqual(row["expected"], ["ean13upca", "ean8", "code128", "qr"])

    def test_leftover_mlkit_import_fails_even_when_gate_passes(self):
        text = (
            "import { BarcodeScanner } from '@capacitor-mlkit/barcode-scanning';\n"
            "settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.EAN8, Symbology.Code128, Symbology.QR]);"
        )
        row = self.score(CAP, CAP_DIR, CAP_ENTRIES[1], [text])
        self.assertEqual(row["status"], "fail")
        self.assertIs(row["compiles"], False)
        self.assertEqual(row["errors_left"], 1)
        self.assertEqual(row["leftover_imports"], 1)

    def test_capacitor_two_file_gate_command(self):
        commands = []
        self.score(CAP, CAP_DIR, CAP_ENTRIES[3], ["", ""], commands=commands)
        self.assertEqual(
            commands[0],
            ["env", "FIX_GATE_TS_ANY_MODULE=1", "bash", str(CAP.gate), "capacitor",
             str(self.tmp / "Scan.tsx"), score.DEFAULT_SDK_VERSION, str(self.tmp / "Scan.types.ts")],
        )

    def test_missing_extra_file_is_not_passed_to_gate(self):
        commands = []
        self.score(CAP, CAP_DIR, CAP_ENTRIES[3], [""], commands=commands)
        self.assertEqual(commands[0][-2:], [str(self.tmp / "Scan.tsx"), score.DEFAULT_SDK_VERSION])

    def test_sdk_version_reaches_gate(self):
        commands = []
        self.score(RN, RN_DIR, RN_ENTRIES[1], [RN_AIO_SCREEN], commands=commands, sdk_version="9.9.9")
        self.assertEqual(commands[0], ["env", "FIX_GATE_TS_ANY_MODULE=1", "bash", str(RN.gate), "rn",
                                       str(self.tmp / "VisionCameraScanner.tsx"), "9.9.9"])

    def test_capacitor_default_all_narrowed_to_qr_is_kept(self):
        row = self.score(CAP, CAP_DIR, CAP_ENTRIES[2], ["barcodeCapture = new BarcodeCapture(s);\n"
                                                       "s.enableSymbologies([Symbology.QR]);"])
        self.assertIs(row["narrowed"], True)
        self.assertIs(row["kept"], True)
        self.assertEqual(report.kept_cell(row), "1/12 narrowed (enabled: qr)")

    def test_typed_identifier_and_jsx_identifier_resolve(self):
        text = (
            "const syms: Symbology[] = [Symbology.EAN13UPCA, Symbology.QR];\n"
            "const more = [Symbology.Code128];\n"
            "settings.enableSymbologies(syms);\n<BarcodeCaptureAioView symbologies={more} />"
        )
        row = self.score(RN, RN_DIR, RN_ENTRIES[1], [text])
        self.assertEqual(sorted(row["found"]), ["code128", "ean13upca", "qr"])

    def test_symbologies_passed_through_a_function_parameter_count(self):
        text = (
            "const SINGLE = [Symbology.EAN13UPCA, Symbology.QR];\nconst LOOP = [Symbology.Code128];\n"
            "function createSettings(symbologies: Symbology[]) { s.enableSymbologies(symbologies); }\n"
            "createSettings(SINGLE); createSettings(LOOP);"
        )
        row = self.score(RN, RN_DIR, RN_ENTRIES[1], [text])
        self.assertEqual(sorted(row["found"]), ["code128", "ean13upca", "qr"])

    def test_leftover_import_keeps_a_skipped_gate_skipped(self):
        text = "import { BarcodeScanner } from '@capacitor-mlkit/barcode-scanning';"
        row = self.score(CAP, CAP_DIR, CAP_ENTRIES[1], [text], (3, "GATE-SKIP: node not found\n"))
        self.assertEqual(row["status"], "skip")
        self.assertIsNone(row["compiles"])
        self.assertEqual(row["leftover_imports"], 1)

    def test_leftover_import_forms(self):
        banned = ("@capacitor-mlkit/barcode-scanning",)
        cases = {
            "export { X } from '@capacitor-mlkit/barcode-scanning';": 1,
            "const m = await import('@capacitor-mlkit/barcode-scanning');": 1,
            'const m = require("@capacitor-mlkit/barcode-scanning");': 1,
            "import '@capacitor-mlkit/barcode-scanning';": 1,
            "// import x from '@capacitor-mlkit/barcode-scanning'": 0,
            "import a from '@capacitor-mlkit/barcode-scanning-extra';": 0,
        }
        for text, n in cases.items():
            with self.subTest(text=text):
                self.assertEqual(score.leftover_imports(text, banned), n)

    def test_rn_bans_only_the_old_scanner_packages(self):
        helpers = "import RNFS from 'react-native-fs';\nimport { File } from 'expo-file-system';\n"
        self.assertEqual(self.score(RN, RN_DIR, RN_ENTRIES[1], [helpers + RN_AIO_SCREEN])["status"], "pass")
        leftovers = "".join(f"import x from '{m}';\n" for m in
                            ["react-native-vision-camera", "react-native-vision-camera-barcode-scanner", "expo-camera"])
        self.assertEqual(self.score(RN, RN_DIR, RN_ENTRIES[1], [leftovers + RN_AIO_SCREEN])["leftover_imports"], 3)

    def test_symbologies_prop_traced_for_js_only(self):
        self.assertEqual(score.enabled_names("x.symbologies = {Symbology.QR}", "js"), {"QR"})
        self.assertEqual(score.enabled_names("x.symbologies = {Symbology.qr}", "dart"), set())

    def test_fixture_paths_and_gate_command_per_suite(self):
        entry = {"files": ["a/x.dart", "b/stub.dart"]}
        self.assertEqual(score.fixture_paths(SUITE, entry), ["lib/x.dart", "lib/stubs/stub.dart"])
        self.assertEqual(score.fixture_paths(CAP, {"files": ["a/Scan.tsx", "c/T.ts"]}), ["Scan.tsx", "T.ts"])
        self.assertEqual(score.gate_command(SUITE, Path("m.dart"), [Path("s.dart")], "9.9.9"),
                         ["bash", str(SUITE.gate), "m.dart", "s.dart"])

    def test_vue_output_symbologies_are_found(self):
        text = '<template><div/></template>\n<script lang="ts">\ns.enableSymbology(Symbology.QR, true);\n</script>'
        row = self.score(CAP, CAP_DIR, CAP_ENTRIES[5], [text])
        self.assertEqual(row["found"], ["qr"])


class RunTsCase(unittest.TestCase):
    def test_flat_prepare_workdir_copies_both_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            run.prepare_workdir(CAP, CAP_DIR, CAP_ENTRIES[3], Path(tmp))
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ["Scan.tsx", "Scan.types.ts"])

    def test_sdk_version_flag_reaches_scoring_and_report(self):
        seen = []
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "barcode-capture-rn" / "1").mkdir(parents=True)
            with mock.patch.object(run, "score_eval", lambda *a, **k: seen.append(k["sdk_version"]) or {
                "id": 1, "fixture": "x.tsx", "status": "pass", "compiles": True, "errors_left": 0,
                "expected": [], "missing": [], "kept": True}), redirect_stdout(io.StringIO()):
                run.main(["--skill", "barcode-capture-rn", "--score-only", tmp, "--sdk-version", "8.7.0"])
            written = json.loads((Path(tmp) / "report.json").read_text())
        self.assertEqual(seen, ["8.7.0"])
        self.assertEqual(written["sdk_version"], "8.7.0")


class ReportCase(unittest.TestCase):
    def test_report_totals_and_markdown(self):
        good = {"id": 1, "fixture": "A.dart", "status": "pass", "compiles": True, "errors_left": 0,
                "expected": ["qr"], "found": ["qr"], "missing": [], "kept": True,
                "claude": {"exit_code": 0, "num_turns": 7, "cost_usd": 0.5}}
        bad = {"id": 2, "fixture": "B.dart", "status": "fail", "compiles": False, "errors_left": 3,
               "expected": ["qr", "ean8"], "found": ["qr"], "missing": ["ean8"], "kept": False}
        with tempfile.TemporaryDirectory() as out:
            data = report.write_report({"skill-x": [good, bad]}, out, skills_sha="abc123", dirty=True)
            on_disk = json.loads((Path(out) / "report.json").read_text())
            markdown = (Path(out) / "report.md").read_text()
        self.assertEqual(on_disk["skills_sha"], "abc123")
        self.assertEqual(
            on_disk["skills"]["skill-x"]["totals"],
            {"fixtures": 2, "compiles": 1, "errors_left": 3, "symbologies_kept": 1},
        )
        self.assertEqual(data["skills"]["skill-x"]["totals"]["fixtures"], 2)
        self.assertIn("`abc123` (dirty)", markdown)
        self.assertIn("| 2 | B.dart | no (fail) | 3 | 1/2 (missing: ean8) |", markdown)
        self.assertIn("| **total** | 2 | 1/2 | 3 | 1/2 | |", markdown)

    def test_claude_cell(self):
        full = {"claude": {"exit_code": 1, "timed_out": True, "num_turns": 3, "cost_usd": 0.456}}
        self.assertEqual(report.claude_cell(full), "exit 1, timeout, 3 turns, $0.46")
        self.assertEqual(report.claude_cell({"claude": {"num_turns": 3, "cost_usd": 0.5}}), "3 turns, $0.50")
        self.assertEqual(report.claude_cell({}), "")

    def test_score_only_reloads_run_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "run.json").write_text('{"exit_code": null, "timed_out": true}')
            (out / "claude.json").write_text('{"num_turns": 4')
            info = run.read_claude_info(out)
        self.assertEqual(info, {"exit_code": None, "timed_out": True})
        self.assertEqual(report.claude_cell({"claude": info}), "timeout")

    def test_score_only_keeps_saved_fixtures_and_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            saved = Path(tmp) / SKILL / "3"
            saved.mkdir(parents=True)
            (saved / "run.json").write_text('{"exit_code": 0, "timed_out": false, "model": "sonnet"}')
            scored = []
            with mock.patch.object(run, "score_eval", lambda _s, e, *_a, **_k: scored.append(e["id"]) or {
                "id": e["id"], "fixture": "x.dart", "status": "pass", "compiles": True, "errors_left": 0,
                "expected": [], "missing": [], "kept": True}), redirect_stdout(io.StringIO()):
                run.main(["--skill", SKILL, "--score-only", tmp])
            written = json.loads((Path(tmp) / "report.json").read_text())
        self.assertEqual(scored, [3])
        self.assertEqual(written["model"], "sonnet")


@unittest.skipUnless(os.environ.get("MIGRATION_EVALS_FLUTTER"), "set MIGRATION_EVALS_FLUTTER=1 to run the real gate")
class RealGateCase(unittest.TestCase):
    def test_unmigrated_fixture_fails_real_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            lib = Path(tmp) / "lib"
            lib.mkdir()
            shutil.copy(EVALS_DIR / ENTRIES[1]["files"][0], lib)
            row = score.score_eval(SUITE, ENTRIES[1], tmp, EVALS_DIR)
        self.assertEqual(row["status"], "fail")
        self.assertGreaterEqual(row["errors_left"], 1)


if __name__ == "__main__":
    unittest.main()
