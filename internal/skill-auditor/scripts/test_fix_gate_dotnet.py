"""Tests for fix_gate_dotnet.sh.

The end-to-end cases restore the real Scandit NuGet packages, so they need dotnet 8 and
network access. They run only with FIX_GATE_E2E=1:

    FIX_GATE_E2E=1 python3 -m unittest internal/skill-auditor/scripts/test_fix_gate_dotnet.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import eval_dir  # noqa: E402

GATE = Path(__file__).resolve().parent / "fix_gate_dotnet.sh"
FIXTURES = eval_dir("barcode-capture-net-maui") / "fixtures"
VERSION = "8.6.1"
DOTNET = shutil.which("dotnet") or str(Path.home() / ".dotnet" / "dotnet")

PLAIN = """using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Barcode.Capture;

public static class Gate
{
    public static BarcodeCaptureSettings Make()
    {
        var settings = BarcodeCaptureSettings.Create();
        settings.EnableSymbology(Symbology.Code128, true);
        return settings;
    }
}
"""


class FixGateDotnetToolchainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def run_gate(self, *args, env=None):
        return subprocess.run(
            [shutil.which("bash") or "/bin/bash", str(GATE), *args], capture_output=True, text=True, env=env, timeout=60,
        )

    def test_missing_dotnet_skips(self):
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        for tool in ("mktemp", "mkdir", "cp", "cat", "rm", "dirname", "basename"):
            (bin_dir / tool).symlink_to(str(shutil.which(tool)))
        snippet = self.tmp / "Gate.cs"
        snippet.write_text(PLAIN)

        result = self.run_gate(str(snippet), VERSION, env={"PATH": str(bin_dir), "HOME": str(self.tmp)})

        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertIn("GATE-SKIP", result.stdout)

    def test_maui_input_is_checked_before_the_toolchain(self):
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        snippet = self.tmp / "Gate.cs"
        snippet.write_text(PLAIN)

        result = self.run_gate("--maui", str(snippet), VERSION, env={"PATH": str(bin_dir), "HOME": str(self.tmp)})

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_maui_without_the_xaml_sibling_is_refused(self):
        code_behind = self.tmp / "Page.xaml.cs"
        code_behind.write_text("public partial class Page {}\n")

        result = self.run_gate("--maui", str(code_behind), VERSION)

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("GATE-FAIL", result.stdout)

    def test_maui_with_a_plain_cs_file_is_refused(self):
        plain = self.tmp / "Gate.cs"
        plain.write_text(PLAIN)

        result = self.run_gate("--maui", str(plain), VERSION)

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("GATE-FAIL", result.stdout)


@unittest.skipUnless(os.environ.get("FIX_GATE_E2E") == "1", "set FIX_GATE_E2E=1 (needs dotnet and network)")
class FixGateDotnetTest(unittest.TestCase):
    def setUp(self):
        if not os.access(DOTNET, os.X_OK):
            self.fail("FIX_GATE_E2E=1 but dotnet is neither on PATH nor in ~/.dotnet")
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def run_gate(self, *args):
        return subprocess.run(["bash", str(GATE), *args], capture_output=True, text=True, timeout=900)

    def maui_page(self, misspell=False):
        for name in ("IntegratedMainPage.xaml", "IntegratedMainPage.xaml.cs"):
            text = (FIXTURES / name).read_text()
            if misspell:
                text = text.replace("Symbology.Code128", "Symbology.Code128x")
            (self.tmp / name).write_text(text)
        return self.tmp / "IntegratedMainPage.xaml.cs"

    def test_maui_page_with_its_xaml_passes(self):
        result = self.run_gate("--maui", str(self.maui_page()), VERSION)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("GATE-PASS", result.stdout)

    def test_maui_page_with_a_misspelt_symbology_fails(self):
        result = self.run_gate("--maui", str(self.maui_page(misspell=True)), VERSION)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("GATE-FAIL", result.stdout)
        self.assertIn("error CS", result.stdout)

    def test_plain_mode_passes_and_fails_as_before(self):
        snippet = self.tmp / "Gate.cs"
        snippet.write_text(PLAIN)
        good = self.run_gate(str(snippet), VERSION)
        self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
        self.assertIn("GATE-PASS", good.stdout)

        snippet.write_text(PLAIN.replace("Symbology.Code128", "Symbology.Code128x"))
        bad = self.run_gate(str(snippet), VERSION)
        self.assertEqual(bad.returncode, 1, bad.stdout + bad.stderr)
        self.assertIn("error CS", bad.stdout)


if __name__ == "__main__":
    unittest.main()
