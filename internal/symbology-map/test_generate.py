"""Tests for generate.py: the repo is in sync, a hand edit is caught, and
mapping.json only references keys it defines.

Drift tests run generate.py as a subprocess against a tempdir copy of every
third-party-migration guide, so the exit code is the one pre-push sees.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GENERATE = HERE / "generate.py"

sys.path.insert(0, str(HERE))
import generate


def run(*args):
    return subprocess.run([sys.executable, str(GENERATE), *args], capture_output=True, text=True)


class CheckTest(unittest.TestCase):
    def test_repo_is_in_sync(self):
        result = run("--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_edited_cell_fails_check_and_write_restores_it(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        for path in generate.guides(ROOT):
            dest = tmp / path.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(path, dest)
        guide = tmp / "skills/barcode-capture-android/references/third-party-migration.md"
        text = guide.read_text()
        self.assertIn("`Symbology.CODE128`", text)
        guide.write_text(text.replace("`Symbology.CODE128`", "`Symbology.CODE_128`", 1))

        result = run("--check", "--root", str(tmp))
        self.assertEqual(result.returncode, 1)
        self.assertIn("barcode-capture-android", result.stdout)

        self.assertEqual(run("--root", str(tmp)).returncode, 0)
        self.assertEqual(guide.read_text(), text)
        self.assertEqual(run("--check", "--root", str(tmp)).returncode, 0)


class MappingTest(unittest.TestCase):
    def setUp(self):
        self.mapping = json.loads((HERE / "mapping.json").read_text())

    def test_every_symbology_has_every_style(self):
        for key, names in self.mapping["symbologies"].items():
            self.assertEqual(set(names), set(generate.STYLES), key)

    def test_formats_and_default_set_resolve(self):
        symbologies = self.mapping["symbologies"]
        for key, fmt in self.mapping["formats"].items():
            self.assertTrue(fmt["symbology"] is None or fmt["symbology"] in symbologies, key)
        for key in self.mapping["default_set"]:
            self.assertIn(key, symbologies)

    def test_source_rows_use_known_formats(self):
        for name in self.mapping["sources"]:
            for fmt in generate.rows(name, self.mapping):
                self.assertIn(fmt, self.mapping["formats"], f"{name}: {fmt}")

    def test_unknown_source_in_marker_is_an_error(self):
        text = "<!-- BEGIN GENERATED symbology-table sources=nope style=js -->\n<!-- END GENERATED symbology-table -->\n"
        with self.assertRaises(ValueError):
            generate.render(text, self.mapping)


FIX = {
    "symbologies": {"qr": {"kotlin": "QR", "swift": "qr", "dart": "qr", "js": "QR", "csharp": "Qr"}},
    "formats": {
        "qr": {"symbology": "qr", "note": {"js": "**not** `QRCode`"}},
        "all": {"symbology": None, "note": "No equivalent."},
        "gap": {"symbology": "qr"},
    },
    "default_set": ["qr"],
    "sources": {
        "a": {"label": "A", "rows": {"qr": ["QR_CODE", "QRC"], "all": {"names": [], "note": "none"}}},
        "b": {"label": "B", "rows_from": "a"},
    },
}


class TableTest(unittest.TestCase):
    def test_source_cell_shapes(self):
        self.assertEqual(generate.source_cell(None), "—")
        self.assertEqual(generate.source_cell(["X", "Y"]), "`X` / `Y`")
        self.assertEqual(generate.source_cell({"names": ["X"], "note": "n"}), "`X` (n)")
        self.assertEqual(generate.source_cell({"names": [], "note": "n"}), "(n)")

    def test_table_literal(self):
        lines = generate.table({"sources": "a,b", "style": "csharp", "namespace": "Scandit.Symbology"}, FIX)
        self.assertEqual(lines[:4], [
            "| A | B | Scandit `Scandit.Symbology` |",
            "|---|---|---|",
            "| `QR_CODE` / `QRC` | `QR_CODE` / `QRC` | `Scandit.Symbology.Qr` |",
            "| (none) | (none) | No equivalent. |",
        ])
        self.assertEqual(len(lines), 6)  # "gap" has no source row
        self.assertTrue(lines[-1].endswith(": `Scandit.Symbology.Qr`."))

    def test_style_note_and_swift_header(self):
        self.assertIn("`Symbology.QR` (**not** `QRCode`)", generate.table({"sources": "a", "style": "js"}, FIX)[2])
        lines = generate.table({"sources": "a", "style": "swift"}, FIX)
        self.assertEqual(lines[0], "| A | Scandit `Symbology` |")
        self.assertTrue(lines[-1].endswith(": `.qr`."))

    def test_unknown_style_is_an_error(self):
        with self.assertRaises(ValueError):
            generate.table({"sources": "a", "style": "rust"}, FIX)


class RenderTest(unittest.TestCase):
    B = "<!-- BEGIN GENERATED symbology-table sources=a style=kotlin -->"
    E = "<!-- END GENERATED symbology-table -->"

    def test_missing_end_marker_is_an_error(self):
        with self.assertRaises(ValueError):
            generate.render(self.B + "\n", FIX)

    def test_damaged_marker_is_an_error(self):
        with self.assertRaises(ValueError):
            generate.render(f"{self.B}\n<!-- END GENERATED symbology-table-->\n{self.E}\n", FIX)

    def test_indent_applied_and_outside_text_kept(self):
        out = generate.render(f"pre\n  {self.B}\n  stale\n  {self.E}\npost\n", FIX)
        self.assertTrue(out.startswith(f"pre\n  {self.B}\n  | A | Scandit `Symbology` |\n  |---|---|\n"))
        self.assertTrue(out.endswith(f"\n  {self.E}\npost\n"))
        self.assertNotIn("stale", out)
        self.assertNotIn(" \n", out)

    def test_two_blocks_and_idempotent(self):
        once = generate.render(f"{self.B}\n{self.E}\nmid\n{self.B}\n{self.E}\n", FIX)
        self.assertEqual(once.count("| A |"), 2)
        self.assertIn("\nmid\n", once)
        self.assertEqual(generate.render(once, FIX), once)


if __name__ == "__main__":
    unittest.main()
