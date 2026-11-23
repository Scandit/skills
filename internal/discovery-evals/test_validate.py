import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
LINUX_SKILL = Path("skills/scandit-linux-sdk/SKILL.md")


class PackageValidationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.package = Path(directory.name)
        self.skill = self.package / LINUX_SKILL
        self.skill.parent.mkdir(parents=True)
        shutil.copyfile(HERE / "fixtures/scandit-linux-sdk-invalid.md", self.skill)

    def validate(self):
        return subprocess.run(
            [sys.executable, HERE / "validate.py", self.package],
            capture_output=True, text=True, check=False,
        )

    def test_reports_linux_yaml_error_at_original_file_position(self):
        result = self.validate()
        self.assertEqual(result.returncode, 1)
        self.assertIn("skills/scandit-linux-sdk/SKILL.md:3:77:", result.stderr)

    def test_reports_each_invalid_manifest_in_one_run(self):
        second = self.package / "skills/second/SKILL.md"
        second.parent.mkdir()
        second.write_text("missing frontmatter\n")

        result = self.validate()
        self.assertEqual(result.returncode, 1)
        self.assertIn("skills/scandit-linux-sdk/SKILL.md:3:77:", result.stderr)
        self.assertIn("skills/second/SKILL.md:1:1:", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_accepts_complete_catalog_after_quoting_linux_description(self):
        root = HERE.parents[1]
        manifests = list(root.glob("skills/*/SKILL.md"))
        for manifest in manifests:
            relative = manifest.relative_to(root)
            if relative != LINUX_SKILL:
                target = self.package / relative
                target.parent.mkdir()
                shutil.copyfile(manifest, target)
        lines = self.skill.read_text().splitlines(keepends=True)
        description = lines[2].removeprefix("description: ").rstrip("\n")
        lines[2] = f"description: \"{description}\"\n"
        self.skill.write_text("".join(lines))

        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"Validated {len(manifests)} skills", result.stdout)
