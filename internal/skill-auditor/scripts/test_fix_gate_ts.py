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
    "web.ts": """
import { DataCaptureView, FrameSourceState } from "@scandit/web-datacapture-core";
import { Symbology } from "@scandit/web-datacapture-barcode";
const view = new DataCaptureView();
view.connectToElement(document.getElementById("data-capture-view")!);
export const state: FrameSourceState = FrameSourceState.On;
export const symbology: Symbology = Symbology.EAN13UPCA;
export const pixelRatio: number = window.devicePixelRatio;
""",
    "rn.ts": """
import { FrameSourceState } from "scandit-react-native-datacapture-core";
import { Symbology } from "scandit-react-native-datacapture-barcode";
export const state: FrameSourceState = FrameSourceState.On;
export const symbology: Symbology = Symbology.EAN13UPCA;
""",
    "capacitor.ts": """
import { FrameSourceState } from "scandit-capacitor-datacapture-core";
import { Symbology } from "scandit-capacitor-datacapture-barcode";
export const state: FrameSourceState = FrameSourceState.On;
export const symbology: Symbology = Symbology.EAN13UPCA;
export const pixelRatio: number = window.devicePixelRatio;
""",
    "web.tsx": """
import { useEffect, useRef } from "react";
import { DataCaptureView, FrameSourceState } from "@scandit/web-datacapture-core";
export function Scanner() {
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    new DataCaptureView().connectToElement(host.current!);
  }, []);
  return <div ref={host} data-state={FrameSourceState.On} />;
}
""",
    "rn.tsx": """
import { View } from "react-native";
import { FrameSourceState } from "scandit-react-native-datacapture-core";
export function Scanner() {
  const state: FrameSourceState = FrameSourceState.On;
  return <View testID={state} />;
}
""",
    "capacitor.js": """
import { Capacitor } from "@capacitor/core";
import { FrameSourceState } from "scandit-capacitor-datacapture-core";
import { Symbology } from "scandit-capacitor-datacapture-barcode";
export const isWeb = Capacitor.getPlatform() === "web";
export const state = FrameSourceState.On;
export const symbology = Symbology.EAN13UPCA;
export const pixelRatio = window.devicePixelRatio;
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
        snippet.write_text(VALID["web.ts"])

        result = subprocess.run(
            [shutil.which("bash"), str(GATE), "web", str(snippet), VERSION],
            capture_output=True,
            text=True,
            env={"PATH": str(bin_dir)},
            timeout=60,
        )

        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertIn("GATE-SKIP", result.stdout)


@unittest.skipUnless(shutil.which("node") and shutil.which("npm"), "needs node and npm on PATH")
class FixGateTsInputTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_two_files_with_one_basename_are_refused(self):
        for first, second in (("a/index.ts", "b/index.ts"), ("Scan.vue", "Scan.ts")):
            with self.subTest(files=(first, second)):
                paths = []
                for name in (first, second):
                    path = self.tmp / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("export {};\n")
                    paths.append(str(path))
                result = subprocess.run(
                    ["bash", str(GATE), "capacitor", paths[0], VERSION, paths[1]],
                    capture_output=True, text=True, timeout=60,
                )
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("rename one", result.stdout)


@unittest.skipUnless(os.environ.get("FIX_GATE_E2E") == "1", "set FIX_GATE_E2E=1 (needs npm and network)")
class FixGateTsTest(unittest.TestCase):
    def setUp(self):
        if shutil.which("npm") is None:
            self.fail("FIX_GATE_E2E=1 but npm is not on PATH")
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def run_gate(self, snippet_name, source):
        snippet = self.tmp / snippet_name
        snippet.write_text(source)
        platform = snippet.stem
        return subprocess.run(
            ["bash", str(GATE), platform, str(snippet), VERSION],
            capture_output=True,
            text=True,
            timeout=600,
        )

    def test_valid_snippet_passes(self):
        for snippet_name, source in VALID.items():
            with self.subTest(snippet=snippet_name):
                result = self.run_gate(snippet_name, source)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("GATE-PASS", result.stdout)

    def test_misspelled_api_fails(self):
        for snippet_name, source in VALID.items():
            with self.subTest(snippet=snippet_name):
                result = self.run_gate(snippet_name, source + MISSPELLED_API)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("GATE-FAIL", result.stdout)
                self.assertIn("StandBy", result.stdout)

    def run_files(self, platform, files, env=None):
        paths = []
        for name, source in files.items():
            (self.tmp / name).write_text(source)
            paths.append(str(self.tmp / name))
        return subprocess.run(
            ["bash", str(GATE), platform, paths[0], VERSION, *paths[1:]],
            capture_output=True, text=True, timeout=600, env={**os.environ, **(env or {})},
        )

    def test_extra_file_resolves_relative_import(self):
        main = 'import { Kind } from "./Scan.types";\nexport const kind: Kind = "qr";\n'
        types = 'export type Kind = "qr" | "ean13";\n'
        result = self.run_files("capacitor", {"Scan.ts": main, "Scan.types.ts": types})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.run_files("capacitor", {"Scan.ts": main}).returncode, 1)
        wrong = {"Scan.ts": main.replace('"qr"', '"upc"'), "Scan.types.ts": types}
        self.assertEqual(self.run_files("capacitor", wrong, {"FIX_GATE_TS_ANY_MODULE": "1"}).returncode, 1)

    def test_vue_script_block_is_gated(self):
        vue = (
            "<template><div /></template>\n"
            '<script setup lang="ts">\n'
            'import { FrameSourceState } from "scandit-capacitor-datacapture-core";\n'
            "export const state: FrameSourceState = FrameSourceState.On;\n"
            "</script>\n"
        )
        self.assertEqual(self.run_files("capacitor", {"Scan.vue": vue}).returncode, 0)
        bad = self.run_files("capacitor", {"Scan.vue": vue.replace("State.On;", "State.StandBy;")})
        self.assertEqual(bad.returncode, 1, bad.stdout)
        self.assertIn("StandBy", bad.stdout)

    def test_vue_script_without_lang_is_gated(self):
        vue = (
            "<template><div /></template>\n<script setup>\n"
            'import { FrameSourceState } from "scandit-capacitor-datacapture-core";\n'
            "export const state = FrameSourceState.StandBy;\n</script>\n"
        )
        result = self.run_files("capacitor", {"Scan.vue": vue})
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("Scan.ts(4,", result.stdout)

    def test_vue_one_line_script_gates_its_code_and_not_the_template(self):
        vue = (
            '<script setup lang="ts">import { FrameSourceState } from "scandit-capacitor-datacapture-core"; '
            "const state = FrameSourceState.StandBy;</script>\n"
            '<template><div :class="{ on: state < 1 }" /></template>\n'
        )
        result = self.run_files("capacitor", {"Scan.vue": vue})
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("Scan.ts(1,", result.stdout)
        self.assertNotIn("Scan.ts(2,", result.stdout)
        good = self.run_files("capacitor", {"Scan.vue": vue.replace("State.StandBy", "State.On")})
        self.assertEqual(good.returncode, 0, good.stdout)

    def test_vue_script_setup_macros_resolve(self):
        vue = (
            '<script setup lang="ts">\n'
            'import { FrameSourceState } from "scandit-capacitor-datacapture-core";\n'
            'const props = withDefaults(defineProps<{ title?: string }>(), { title: "Scan" });\n'
            'const emit = defineEmits<{ (e: "scanned", data: string): void }>();\n'
            "const state: FrameSourceState = FrameSourceState.On;\n"
            "defineExpose({ state });\n"
            'defineOptions({ name: "Scan" });\n'
            "const code = defineModel<FrameSourceState>();\n"
            "code.value = state;\n"
            'emit("scanned", props.title ?? "");\n'
            "</script>\n"
        )
        result = self.run_files("capacitor", {"Scan.vue": vue})
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_any_module_shim_lets_app_types_and_env_through(self):
        app = (
            'import { Subject, Observable } from "rxjs";\n'
            "export const s: Subject<string> = new Subject<string>();\n"
            "export function f(o: Observable): Observable { return o; }\n"
            "export const url: string = import.meta.env.VITE_URL;\n"
            'import { defineComponent } from "vue";\n'
            'import type { Render } from "@app/types";\n'
            "export const c = defineComponent({ setup(props) { return props; } });\n"
            "export const r: Render = props => props;\n"
            "export async function q(): Promise<void> {\n"
            '  const { default: Q } = await import("qr-scanner");\n'
            "  new Q(1, async ({ data }) => data);\n}\n"
            'import { useBarcodeScannerOutput } from "react-native-vision-camera-barcode-scanner";\n'
            "export const o = useBarcodeScannerOutput({ onError: error => error.message });\n"
        )
        result = self.run_files("capacitor", {"Scan.ts": app}, {"FIX_GATE_TS_ANY_MODULE": "1"})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("error TS", result.stdout)

    def test_any_module_shim_keeps_implicit_any_on_untyped_scandit_listeners(self):
        cap = (
            'import { Subject } from "rxjs";\n'
            'import { BarcodeCapture } from "scandit-capacitor-datacapture-barcode";\n'
        )
        rn = (
            'import { useMemo, useRef } from "react";\n'
            'import { BarcodeCapture } from "scandit-react-native-datacapture-barcode";\n'
            "export function useListener(bc: BarcodeCapture | null) {\n"
        )
        did_scan = "{ didScan: async (_m, session) => session.newlyRecognizedBarcodes }"
        cases = {
            "object": ("capacitor", "Scan.ts", cap + "export function wire(bc: BarcodeCapture, out: Subject<string>): void {\n"
                       "  const listener = { didScan: async (_m, session) => out.next(session.newlyRecognizedBarcodes[0].data) };\n"
                       "  bc.addListener(listener);\n}\n"),
            "class": ("capacitor", "Scan.ts", cap + "export class Listener { didScan(_m, session) { return session.newlyRecognizedBarcodes; } }\n"
                      "export const bc: BarcodeCapture | null = null;\n"),
            "freeze": ("capacitor", "Scan.ts", cap + f"export const listener = Object.freeze({did_scan});\n"),
            "factory": ("capacitor", "Scan.ts", cap + f"export const make = (out: Subject<string>) => ({did_scan});\n"),
            "useRef": ("rn", "Scan.tsx", rn + f"  return useRef({did_scan});\n}}\n"),
            "useMemo": ("rn", "Scan.tsx", rn + f"  return useMemo(() => ({did_scan}), []);\n}}\n"),
        }
        for name, (platform, file_name, source) in cases.items():
            with self.subTest(case=name):
                result = self.run_files(platform, {file_name: source}, {"FIX_GATE_TS_ANY_MODULE": "1"})
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("error TS7006: Parameter 'session'", result.stdout)

    def test_any_module_shim_fails_closed_when_the_callback_filter_crashes(self):
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        node = bin_dir / "node"
        node.write_text(f'#!/bin/sh\ncase "$2" in *shimmedCallback*) exit 1;; esac\nexec {shutil.which("node")} "$@"\n')
        node.chmod(0o755)
        app = 'import Q from "qr-scanner";\nexport const q = new Q(1, async ({ data }) => data);\n'
        shim = {"FIX_GATE_TS_ANY_MODULE": "1"}
        self.assertEqual(self.run_files("capacitor", {"Scan.ts": app}, shim).returncode, 0)
        result = self.run_files("capacitor", {"Scan.ts": app}, {**shim, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"})
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("GATE-FAIL", result.stdout)

    def test_any_module_shim_is_opt_in_and_keeps_scandit_checks(self):
        app_import = 'import { thing } from "../../app/store";\nexport const t: number = thing;\n'
        shim = {"FIX_GATE_TS_ANY_MODULE": "1"}
        self.assertEqual(self.run_files("capacitor", {"Scan.ts": app_import}).returncode, 1)
        self.assertEqual(self.run_files("capacitor", {"Scan.ts": app_import}, {"FIX_GATE_TS_ANY_MODULE": "0"}).returncode, 1)
        self.assertEqual(self.run_files("capacitor", {"Scan.ts": app_import}, shim).returncode, 0)
        misspelled = VALID["capacitor.ts"] + MISSPELLED_API
        result = self.run_files("capacitor", {"Scan.ts": misspelled}, shim)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("StandBy", result.stdout)

    def test_any_module_shim_never_covers_scandit(self):
        shim = {"FIX_GATE_TS_ANY_MODULE": "1"}
        cases = {
            "TS2307": 'import { Symbology } from "scandit-capacitor-datacapture-barcod";\nexport const s = Symbology.X;\n',
            "TS2694": 'import * as SDC from "scandit-capacitor-datacapture-barcode";\nexport let x: SDC.NotAType;\n',
            "TS2709": 'import * as SDC from "scandit-capacitor-datacapture-barcode";\nexport let x: SDC;\n',
        }
        for code, source in cases.items():
            with self.subTest(code=code):
                result = self.run_files("capacitor", {"Scan.ts": source}, shim)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn(f"error {code}", result.stdout)

    def test_react_native_rejects_dom_globals(self):
        result = self.run_gate("rn.ts", VALID["rn.ts"] + DOM_ONLY_GLOBAL)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("GATE-FAIL", result.stdout)
        self.assertIn("document", result.stdout)


if __name__ == "__main__":
    unittest.main()
