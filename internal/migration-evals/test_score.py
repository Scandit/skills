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
            "// formats: [BarcodeFormat.qrCode]\nMobileScanner()": default,
            "final u = 'https://x'; final c = MobileScannerController(formats: [BarcodeFormat.qrCode]);": ["qr"],
        }
        for source, ids in cases.items():
            with self.subTest(source=source):
                self.assertEqual(score.expected_symbologies(source, SUITE, score.load_mapping()), ids)

    def test_unreadable_format_list_item_raises(self):
        for source in ["formats: [BarcodeFormat.unknown]", "formats: [TYPES[0], BarcodeFormat.qrCode]",
                       "formats: [...BASE, BarcodeFormat.qrCode]", "formats: [`qrCode`]"]:
            with self.subTest(source=source), self.assertRaises(ValueError):
                score.expected_symbologies(source, SUITE, score.load_mapping())

    def test_every_fixture_format_list_is_readable(self):
        for skill, suite in score.SUITES.items():
            evals_dir = score.eval_dir(skill)
            for entry in json.loads((evals_dir / "third-party-migration-evals.json").read_text())["evals"]:
                with self.subTest(skill=skill, id=entry["id"]):
                    score.expected_symbologies((evals_dir / entry["files"][0]).read_text(), suite, score.load_mapping())

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
# Real gate output for the unmigrated RN fixture 1: the shim types the old scanner as `any`.
TS_GATE_UNMIGRATED_RN = (
    0, "GATE-PASS: VisionCameraScanner.tsx vs scandit-react-native-datacapture-barcode 8.6.1 (rn)\n"
)


class FlatSuiteScoring(unittest.TestCase):
    """Writes migrated texts into a temp workdir and scores them with a recorded, canned gate."""

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


class TsScoreCase(FlatSuiteScoring):
    def test_rn_good_output_compiles_and_keeps(self):
        row = self.score(RN, RN_DIR, RN_ENTRIES[1], [RN_AIO_SCREEN])
        self.assertIs(row["compiles"], True)
        self.assertIs(row["kept"], True)

    def test_rn_unmigrated_output_counts_ts_errors(self):
        original = (RN_DIR / RN_ENTRIES[1]["files"][0]).read_text()
        row = self.score(RN, RN_DIR, RN_ENTRIES[1], [original], TS_GATE_UNMIGRATED_RN)
        self.assertEqual(row["status"], "fail")
        self.assertIs(row["compiles"], False)
        self.assertEqual(row["leftover_imports"], 1)
        self.assertEqual(row["errors_left"], 1)
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

    def test_parameter_counts_only_lists_passed_to_its_function(self):
        text = (
            "const REQUIRED = [Symbology.EAN13UPCA, Symbology.QR];\nconst UI_OPTIONS = [Symbology.Code128];\n"
            "function apply(symbologies: Symbology[]): void { s.enableSymbologies(symbologies); }\n"
            "apply(REQUIRED);"
        )
        row = self.score(RN, RN_DIR, RN_ENTRIES[1], [text])
        self.assertEqual(sorted(row["found"]), ["ean13upca", "qr"])

    def test_parameter_traced_through_a_caller_parameter(self):
        text = (
            "const ONE = [Symbology.EAN13UPCA];\nconst TWO = [Symbology.Code128, Symbology.QR];\n"
            "function createSettings(symbologies: Symbology[]) { s.enableSymbologies(symbologies); }\n"
            "async function begin(syms: Symbology[], done: () => void): Promise<void> { createSettings(syms); }\n"
            "begin(ONE, () => {}); const go = async () => begin(TWO, () => {});"
        )
        row = self.score(RN, RN_DIR, RN_ENTRIES[1], [text])
        self.assertEqual(sorted(row["found"]), ["code128", "ean13upca", "qr"])

    def test_leftover_import_keeps_a_skipped_gate_skipped(self):
        text = "import { BarcodeScanner } from '@capacitor-mlkit/barcode-scanning';"
        row = self.score(CAP, CAP_DIR, CAP_ENTRIES[1], [text], (3, "GATE-SKIP: node not found\n"))
        self.assertEqual(row["status"], "skip")
        self.assertIsNone(row["compiles"])
        self.assertEqual(row["errors_left"], 0)
        self.assertEqual(row["leftover_imports"], 1)

    def test_leftover_import_keeps_a_resolve_fail(self):
        text = "import { BarcodeScanner } from '@capacitor-mlkit/barcode-scanning';"
        row = self.score(CAP, CAP_DIR, CAP_ENTRIES[1], [text], (1, "GATE-FAIL: npm install\n"))
        self.assertEqual(row["status"], "resolve-fail")
        self.assertEqual(row["errors_left"], 0)
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
            "import a from '@capacitor-mlkit/barcode-scanning/web';": 1,
            "const u = 'https://x'; import a from '@capacitor-mlkit/barcode-scanning';": 1,
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
        self.assertEqual(score.enabled_names("<V symbologies={[Symbology.QR]} />", "js"), {"QR"})
        self.assertEqual(score.enabled_names("<V symbologies={[Symbology.qr]} />", "dart"), set())

    def test_symbologies_object_assignment_is_not_the_prop(self):
        self.assertEqual(score.enabled_names("const symbologies = { [Symbology.QR]: 'QR' };", "js"), set())

    def test_parameter_shadows_a_same_named_literal(self):
        text = ("const symbologies = [Symbology.QR];\n"
                "function apply(symbologies) { s.enableSymbologies(symbologies); }\napply([Symbology.EAN8]);")
        self.assertEqual(score.enabled_names(text, "js"), {"EAN8"})

    def test_jsx_prop_before_its_const_resolves(self):
        text = "<V symbologies={symbologies} />;\nconst symbologies = [Symbology.QR];"
        self.assertEqual(score.enabled_names(text, "js"), {"QR"})

    def test_parameter_traced_only_into_the_enabling_function(self):
        text = ("function log(syms) {}\nfunction apply(syms) { s.enableSymbologies(syms); }\n"
                "log([Symbology.QR]); apply([Symbology.EAN8]);")
        self.assertEqual(score.enabled_names(text, "js"), {"EAN8"})

    def test_parameter_defined_inside_its_function_counts(self):
        cases = {
            "function apply(syms = [Symbology.QR]) { s.enableSymbologies(syms) } apply()": {"QR"},
            "function apply(syms: Symbology[] = [Symbology.QR]) { s.enableSymbologies(syms) } apply()": {"QR"},
            "class A { setup(syms = [Symbology.UPCE]) { s.enableSymbologies(syms) } }": {"UPCE"},
            "function apply(syms){ syms = [Symbology.QR]; s.enableSymbologies(syms) }": {"QR"},
            "const symbologies = [Symbology.QR];\nfunction apply(symbologies = [Symbology.EAN8]) "
            "{ s.enableSymbologies(symbologies); }\napply([Symbology.UPCE]);": {"EAN8", "UPCE"},
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(score.enabled_names(text, "js"), expected)

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


MAUI_DIR, MAUI, MAUI_ENTRIES = ts_entries("barcode-capture-net-maui")
MAUI_PAGE = """
using Scandit.DataCapture.Barcode.Capture;
using Scandit.DataCapture.Barcode.Data;
public partial class ScannerPage : ContentPage
{
    void Setup()
    {
        var settings = BarcodeCaptureSettings.Create();
        settings.EnableSymbology(Symbology.Ean13Upca, true);
        settings.EnableSymbology(Symbology.Code128, true);
        settings.EnableSymbology(Symbology.Qr, true);
    }
}
"""
MAUI_GATE_FAIL = (
    1,
    "/tmp/x/ZxingMauiPage.xaml.cs(9,22): error CS0246: The type or namespace name 'ZXing' could not be found [/tmp/x/gate.csproj]\n"
    "/tmp/x/ZxingMauiPage.xaml.cs(15,9): error CS0103: The name 'cameraView' does not exist [/tmp/x/gate.csproj]\n"
    "GATE-FAIL: x vs Scandit.DataCapture.* 8.6.1\n",
)


class MauiScoreCase(FlatSuiteScoring):
    def maui(self, eval_id, code, xaml="", gate_result=TS_GATE_OK, **kwargs):
        return self.score(MAUI, MAUI_DIR, MAUI_ENTRIES[eval_id], [code, xaml], gate_result, **kwargs)

    def test_good_output_compiles_and_keeps_symbologies(self):
        row = self.maui(1, MAUI_PAGE)
        self.assertIs(row["compiles"], True)
        self.assertIs(row["kept"], True)

    def test_expected_symbologies_come_from_the_zxing_flags(self):
        self.assertEqual(self.maui(1, "")["expected"], ["ean13upca", "code128", "qr"])
        self.assertEqual(self.maui(2, "")["expected"], ["ean13upca", "datamatrix"])

    def test_gate_command_runs_the_maui_gate_on_the_code_behind(self):
        commands = []
        self.maui(1, MAUI_PAGE, commands=commands)
        self.assertEqual(
            commands[0],
            ["bash", str(MAUI.gate), "--maui", str(self.tmp / "ZxingMauiPage.xaml.cs"), score.DEFAULT_SDK_VERSION],
        )

    def test_sdk_version_reaches_the_maui_gate(self):
        commands = []
        self.maui(1, MAUI_PAGE, commands=commands, sdk_version="9.9.9")
        self.assertEqual(commands[0][-1], "9.9.9")

    def test_csharp_enable_forms_are_traced(self):
        text = (
            "settings.EnableSymbology(Symbology.Qr, true);\n"
            "settings.EnableSymbology(Symbology.Ean8, false);\n"
            "settings.GetSymbologySettings(Symbology.Aztec).Enabled = true;\n"
        )
        self.assertEqual(sorted(self.maui(1, text)["found"]), ["qr"])
        self.assertEqual(sorted(self.maui(2, "settings.GetSymbologySettings(Symbology.DataMatrix).Enabled = true;")["found"]),
                         ["datamatrix"])

    def test_csharp_collections_resolve_through_enable_symbologies(self):
        cases = {
            "var s = new HashSet<Symbology> { Symbology.Ean13Upca, Symbology.Code128 };": ["code128", "ean13upca"],
            "Symbology[] s = { Symbology.Ean13Upca, Symbology.Code128 };": ["code128", "ean13upca"],
            "var s = new[] { Symbology.Ean13Upca, Symbology.Code128 };": ["code128", "ean13upca"],
            "var s = new List<Symbology> { Symbology.Ean13Upca, Symbology.Code128 };": ["code128", "ean13upca"],
            "HashSet<Symbology> s = [Symbology.Ean13Upca, Symbology.Code128];": ["code128", "ean13upca"],
        }
        for definition, ids in cases.items():
            with self.subTest(definition=definition):
                text = f"{definition}\nsettings.EnableSymbologies(s);"
                self.assertEqual(sorted(self.maui(1, text)["found"]), ids)

    def test_csharp_inline_enable_symbologies_literal(self):
        text = "settings.EnableSymbologies(new HashSet<Symbology> { Symbology.Qr, Symbology.Code128 });"
        self.assertEqual(sorted(self.maui(1, text)["found"]), ["code128", "qr"])

    def test_default_all_original_narrowed_to_one_is_kept(self):
        original = MAUI_DIR / "fixtures" / "ZxingMauiPage.xaml.cs"
        entry = {"id": 9, "files": ["fixtures/AllFormats.xaml.cs", "fixtures/AllFormats.xaml"]}
        (self.tmp / "orig").mkdir()
        (self.tmp / "orig" / "fixtures").mkdir()
        all_formats = original.read_text().replace(
            "Formats = BarcodeFormat.Ean13 | BarcodeFormat.Code128 | BarcodeFormat.QrCode,", "")
        self.assertNotIn("Formats =", all_formats)
        (self.tmp / "orig" / "fixtures" / "AllFormats.xaml.cs").write_text(all_formats)
        row = self.score(MAUI, self.tmp / "orig", entry, ["settings.EnableSymbology(Symbology.Qr, true);", ""])
        self.assertIs(row["narrowed"], True)
        self.assertIs(row["kept"], True)
        self.assertEqual(report.kept_cell(row), "1/12 narrowed (enabled: qr)")

    def test_leftover_zxing_using_fails_even_when_the_gate_passes(self):
        row = self.maui(1, "using ZXing.Net.Maui;\n" + MAUI_PAGE)
        self.assertEqual(row["status"], "fail")
        self.assertIs(row["compiles"], False)
        self.assertEqual(row["leftover_imports"], 1)
        self.assertEqual(row["errors_left"], 1)

    def test_leftover_zxing_xaml_namespace_fails(self):
        xaml = '<ContentPage xmlns:zxing="clr-namespace:ZXing.Net.Maui.Controls;assembly=ZXing.Net.MAUI.Controls" />'
        row = self.maui(1, MAUI_PAGE, xaml)
        self.assertEqual(row["status"], "fail")
        self.assertEqual(row["leftover_imports"], 1)

    def test_clean_migrated_xaml_namespace_is_not_a_leftover(self):
        xaml = '<ContentPage xmlns:scandit="clr-namespace:Scandit.DataCapture.Core.UI.Maui;assembly=ScanditCaptureCoreMaui" />'
        self.assertEqual(self.maui(1, MAUI_PAGE, xaml)["status"], "pass")

    def test_csharp_leftover_using_forms(self):
        banned = ("ZXing.Net.Maui",)
        cases = {
            "using ZXing.Net.Maui;": 1,
            "using ZXing.Net.Maui.Controls;": 1,
            "using static ZXing.Net.Maui.BarcodeFormat;": 1,
            "using Zx = ZXing.Net.Maui;": 1,
            "// using ZXing.Net.Maui;": 0,
            "using ZXing.Net.MauiExtra;": 0,
            "using Scandit.DataCapture.Barcode.Data;": 0,
        }
        for text, n in cases.items():
            with self.subTest(text=text):
                self.assertEqual(score.leftover_imports(text, banned), n)

    def test_zxing_all_flag_expands_to_the_default_set(self):
        mapping = score.load_mapping()
        for source in ("Formats = BarcodeFormat.All,", "Formats = BarcodeFormat.Ean13 | BarcodeFormats.All,"):
            with self.subTest(source=source):
                self.assertEqual(score.expected_symbologies(source, MAUI, mapping), mapping["default_set"])

    def test_unmapped_zxing_flag_is_refused(self):
        with self.assertRaisesRegex(ValueError, "unreadable Formats item"):
            score.expected_symbologies("Formats = BarcodeFormat.NoSuchFormat,", MAUI, score.load_mapping())

    def test_flags_split_across_lines_are_all_read(self):
        source = "Formats = BarcodeFormat.Ean13 |\n    BarcodeFormat.QrCode\n    | BarcodeFormat.Code128,"
        self.assertEqual(score.expected_symbologies(source, MAUI, score.load_mapping()),
                         ["ean13upca", "qr", "code128"])

    def test_csharp_typed_array_literal_resolves(self):
        text = "var s = new Symbology[] { Symbology.Qr, Symbology.Code128 };\nsettings.EnableSymbologies(s);"
        self.assertEqual(sorted(self.maui(1, text)["found"]), ["code128", "qr"])

    def test_xaml_namespace_prefix_match_is_not_a_leftover(self):
        for ns in ("ZXing.Net.MauiExtra", "ZXing.Net.Maui2"):
            with self.subTest(ns=ns):
                self.assertEqual(score.leftover_imports(f'xmlns:z="clr-namespace:{ns}"', ("ZXing.Net.Maui",)), 0)

    def test_error_cs_lines_are_counted(self):
        row = self.maui(1, MAUI_PAGE, gate_result=MAUI_GATE_FAIL)
        self.assertEqual(row["status"], "fail")
        self.assertEqual(row["errors_left"], 2)


class RunTsCase(unittest.TestCase):
    def test_colliding_basenames_are_refused(self):
        entry = {"files": ["a/index.ts", "b/index.ts"]}
        with self.assertRaises(ValueError):
            score.fixture_paths(CAP, entry)
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            run.prepare_workdir(CAP, CAP_DIR, entry, Path(tmp))

    def test_flat_prepare_workdir_copies_both_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            run.prepare_workdir(CAP, CAP_DIR, CAP_ENTRIES[3], Path(tmp))
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ["Scan.tsx", "Scan.types.ts"])

    def test_prompt_names_the_gate_sdk_version(self):
        self.assertTrue(run.build_prompt(RN, RN_ENTRIES[1], "8.6.1").endswith(
            "Edit them in place. The app uses Scandit SDK 8.6.1."))
        self.assertNotIn("Scandit SDK", run.build_prompt(SUITE, ENTRIES[1], "8.6.1").split("\n\n")[-1])

    def test_sdk_version_flag_reaches_claude(self):
        seen = []
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(run.subprocess, "run", lambda cmd, **k: seen.append(cmd[2]) or mock.Mock(
                    returncode=0, stdout="{}", stderr="")):
            run.run_claude(RN, RN_DIR, RN_ENTRIES[1], Path(tmp) / "1", None, 5, sdk_version="8.7.0")
            saved = json.loads((Path(tmp) / "1" / "run.json").read_text())
        self.assertTrue(seen[0].endswith("The app uses Scandit SDK 8.7.0."))
        self.assertEqual(saved["sdk_version"], "8.7.0")

    def score_only_sdk(self, saved_run_json, *flags):
        seen = []
        with tempfile.TemporaryDirectory() as tmp:
            saved = Path(tmp) / "barcode-capture-rn" / "1"
            saved.mkdir(parents=True)
            (saved / "run.json").write_text(saved_run_json)
            with mock.patch.object(run, "score_eval", lambda *a, **k: seen.append(k["sdk_version"]) or {
                "id": 1, "fixture": "x.tsx", "status": "pass", "compiles": True, "errors_left": 0,
                "expected": [], "missing": [], "kept": True}), redirect_stdout(io.StringIO()):
                run.main(["--skill", "barcode-capture-rn", "--score-only", tmp, *flags])
            written = json.loads((Path(tmp) / "report.json").read_text())
        return seen[0], written["sdk_version"]

    def test_score_only_uses_the_saved_sdk_version(self):
        self.assertEqual(self.score_only_sdk('{"exit_code": 0, "sdk_version": "8.7.0"}'), ("8.7.0", "8.7.0"))
        self.assertEqual(self.score_only_sdk('{"exit_code": 0}'), ("8.6.1", "8.6.1"))
        flag = ("--sdk-version", "9.0.0")
        self.assertEqual(self.score_only_sdk('{"sdk_version": "8.7.0"}', *flag), ("9.0.0", "9.0.0"))

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


@unittest.skipUnless(os.environ.get("FIX_GATE_E2E") == "1", "set FIX_GATE_E2E=1 to run the real .NET gate")
class RealMauiGateCase(unittest.TestCase):
    def test_unmigrated_fixture_fails_real_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in score.fixture_paths(MAUI, MAUI_ENTRIES[1]):
                shutil.copy(MAUI_DIR / "fixtures" / name, tmp)
            row = score.score_eval(MAUI, MAUI_ENTRIES[1], tmp, MAUI_DIR)
        self.assertEqual(row["status"], "fail")
        self.assertGreaterEqual(row["errors_left"], 1)


if __name__ == "__main__":
    unittest.main()
