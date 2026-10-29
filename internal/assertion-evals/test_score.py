import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score import deterministic_check, extract_code, judge_prompt, parse_verdicts, scoped_output  # noqa: E402

OUTPUT = """Replace `forLicenseKey` with the new API.

```kotlin
import com.scandit.datacapture.barcode.capture.BarcodeCapture
val context = DataCaptureContext.initialize(licenseKey)
settings.enableSymbology(Symbology.CODE128, true)
```
"""


class DeterministicCheck(unittest.TestCase):
    def test_present(self):
        self.assertTrue(deterministic_check(OUTPUT, "DataCaptureContext.initialize( is present")[0])
        self.assertFalse(deterministic_check(OUTPUT, "Camera.getDefaultCamera( is called")[0])

    def test_not_present(self):
        self.assertTrue(deterministic_check(OUTPUT, "com.google.zxing is NOT present")[0])
        self.assertFalse(deterministic_check(OUTPUT, "Symbology.CODE128 is NOT enabled")[0])

    def test_disjunction(self):
        self.assertTrue(deterministic_check(OUTPUT, "Symbology.QR or Symbology.CODE128 is enabled")[0])

    def test_kotlin_import(self):
        self.assertTrue(deterministic_check(OUTPUT, "Import from com.scandit.datacapture.barcode is present")[0])
        self.assertTrue(deterministic_check(OUTPUT, "com.scandit.datacapture import IS present")[0])
        self.assertTrue(deterministic_check(OUTPUT, "com.google.zxing import is NOT present")[0])

    def test_prose_and_semantic_go_to_judge(self):
        self.assertIsNone(deterministic_check(OUTPUT, "the camera is present"))
        self.assertIsNone(deterministic_check(OUTPUT, "DataCaptureContext.initialize( is present (semantic)"))
        self.assertIsNone(deterministic_check(OUTPUT, "Lifecycle is handled correctly"))


class MigrationScope(unittest.TestCase):
    def test_absence_ignores_prose(self):
        scoped = scoped_output(OUTPUT, "forLicenseKey is NOT present", migration=True)
        self.assertTrue(deterministic_check(scoped, "forLicenseKey is NOT present")[0])
        self.assertFalse(deterministic_check(OUTPUT, "forLicenseKey is NOT present")[0])

    def test_presence_and_integration_keep_prose(self):
        self.assertEqual(scoped_output(OUTPUT, "X is present", migration=True), OUTPUT)
        self.assertEqual(scoped_output(OUTPUT, "X is NOT present", migration=False), OUTPUT)

    def test_no_fence_falls_back_to_output(self):
        self.assertEqual(extract_code("plain"), "plain")


class Verdicts(unittest.TestCase):
    def test_parse_in_order_with_missing(self):
        text = "1. PASS: found\n3. fail: missing\nnoise"
        self.assertEqual(
            [p for p, _ in parse_verdicts(text, 3)], [True, False, False]
        )
        self.assertEqual(parse_verdicts(text, 3)[1][1], "JUDGE_PARSE_ERROR")

    def test_prompt_numbers_assertions(self):
        self.assertIn("2. b", judge_prompt("out", ["a", "b"]))


if __name__ == "__main__":
    unittest.main()
