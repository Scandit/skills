import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import report
import score

EVALS_DIR = score.eval_dir("barcode-capture-flutter")
SUITE = score.SUITES["barcode-capture-flutter"]
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
        row = self.score(2, "final s = {Symbology.qr};", GATE_OK)
        self.assertIs(row["kept"], False)
        self.assertIn("code128", row["missing"])
        self.assertNotIn("qr", row["missing"])

    def test_symbologies_enabled_in_migrated_stub_count(self):
        stubs = self.tmp / "lib" / "stubs"
        stubs.mkdir(parents=True)
        (stubs / Path(ENTRIES[5]["files"][1]).name).write_text("final s = {Symbology.qr};")
        row = self.score(5, "// no settings here", GATE_OK)
        self.assertIs(row["kept"], True)

    def test_commented_out_symbology_does_not_count(self):
        text = MIGRATED_PAGE.replace("Symbology.code128", "/* Symbology.code128 */ // Symbology.code128\n Symbology.qr")
        row = self.score(1, text, GATE_OK)
        self.assertEqual(row["missing"], ["code128"])

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
