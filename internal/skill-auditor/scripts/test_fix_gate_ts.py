"""Tests for fix_gate_ts.sh.

The end-to-end cases npm-install the real Scandit packages, so they need npm and
network access. They run only with FIX_GATE_E2E=1:

    FIX_GATE_E2E=1 python3 -m unittest internal/skill-auditor/scripts/test_fix_gate_ts.py
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

GATE = Path(__file__).resolve().parent / "fix_gate_ts.sh"
VERSION = "8.6.1"

VALID = {
    "web": """
import { DataCaptureView, FrameSourceState } from "@scandit/web-datacapture-core";
import { Symbology } from "@scandit/web-datacapture-barcode";
const view = new DataCaptureView();
view.connectToElement(document.getElementById("data-capture-view")!);
export const state: FrameSourceState = FrameSourceState.On;
export const symbology: Symbology = Symbology.EAN13UPCA;
export const pixelRatio: number = window.devicePixelRatio;
""",
    "rn": """
import { FrameSourceState } from "scandit-react-native-datacapture-core";
import { Symbology } from "scandit-react-native-datacapture-barcode";
export const state: FrameSourceState = FrameSourceState.On;
export const symbology: Symbology = Symbology.EAN13UPCA;
""",
    "capacitor": """
import { FrameSourceState } from "scandit-capacitor-datacapture-core";
import { Symbology } from "scandit-capacitor-datacapture-barcode";
export const state: FrameSourceState = FrameSourceState.On;
export const symbology: Symbology = Symbology.EAN13UPCA;
export const pixelRatio: number = window.devicePixelRatio;
""",
}

MISSPELLED_API = "export const misspelled = FrameSourceState.StandBy;\n"
DOM_ONLY_GLOBAL = "export const title: string = document.title;\n"
TOOLS_THE_GATE_NEEDS_BESIDES_NODE_AND_NPM = ("mktemp", "mkdir", "cp", "cat", "rm")


class FixGateTsToolchainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_npm_without_node_skips(self):
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        for tool in TOOLS_THE_GATE_NEEDS_BESIDES_NODE_AND_NPM:
            (bin_dir / tool).symlink_to(shutil.which(tool))
        npm_shim = bin_dir / "npm"
        npm_shim.write_text("#!/bin/sh\nexit 0\n")
        npm_shim.chmod(0o755)
        snippet = self.tmp / "web.ts"
        snippet.write_text(VALID["web"])

        result = subprocess.run(
            [shutil.which("bash"), str(GATE), "web", str(snippet), VERSION],
            capture_output=True,
            text=True,
            env={"PATH": str(bin_dir)},
            timeout=60,
        )

        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertIn("GATE-SKIP", result.stdout)


@unittest.skipUnless(os.environ.get("FIX_GATE_E2E") == "1", "set FIX_GATE_E2E=1 (needs npm and network)")
class FixGateTsTest(unittest.TestCase):
    def setUp(self):
        if shutil.which("npm") is None:
            self.fail("FIX_GATE_E2E=1 but npm is not on PATH")
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def run_gate(self, platform, source):
        snippet = self.tmp / f"{platform}.ts"
        snippet.write_text(source)
        return subprocess.run(
            ["bash", str(GATE), platform, str(snippet), VERSION],
            capture_output=True,
            text=True,
            timeout=600,
        )

    def test_valid_snippet_passes(self):
        for platform, source in VALID.items():
            with self.subTest(platform=platform):
                result = self.run_gate(platform, source)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("GATE-PASS", result.stdout)

    def test_misspelled_api_fails(self):
        for platform, source in VALID.items():
            with self.subTest(platform=platform):
                result = self.run_gate(platform, source + MISSPELLED_API)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("GATE-FAIL", result.stdout)
                self.assertIn("StandBy", result.stdout)

    def test_react_native_rejects_dom_globals(self):
        result = self.run_gate("rn", VALID["rn"] + DOM_ONLY_GLOBAL)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("GATE-FAIL", result.stdout)
        self.assertIn("document", result.stdout)


if __name__ == "__main__":
    unittest.main()
