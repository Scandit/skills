"""Tests for accuracy_review.py --dry-run, run as a subprocess so exit codes and stderr are real."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from common import AUDITOR_ROOT, REPO_ROOT, list_skill_dirs

SCRIPT = Path(__file__).resolve().parent / "accuracy_review.py"
REGISTRY = AUDITOR_ROOT / "accuracy" / "registry.json"
REAL_SKILLS = [d.name for d in list_skill_dirs(REPO_ROOT / "skills")]
NOTES = [f"docs/sdks/{p}/release-notes.md" for p in (
    "ios", "android", "web", "cordova", "react-native", "flutter", "kmp",
    "capacitor", "titanium", "net/ios", "net/android", "linux")]


def run(*args):
    with tempfile.TemporaryDirectory() as out:
        return subprocess.run([sys.executable, str(SCRIPT), *args, "--out", out], capture_output=True, text=True)


class AccuracyDryRunTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.docs = self.tmp / "docs-clone"
        for rel in NOTES:
            notes = self.docs / rel
            notes.parent.mkdir(parents=True)
            notes.write_text("# notes\n")

    def dry(self, *extra):
        return run("--dry-run", "--docs", str(self.docs), *extra)

    def skills_tree(self, names):
        skills = self.tmp / "skills"
        for name in names:
            (skills / name).mkdir(parents=True)
        return skills

    def registry_with(self, mutate):
        data = json.loads(REGISTRY.read_text())
        mutate(data)
        path = self.tmp / "registry.json"
        path.write_text(json.dumps(data))
        return path

    def assertUsageError(self, *args, needle="accuracy_review:"):
        proc = run(*args)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn(needle, proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def assertDryUsageError(self, *extra, needle="accuracy_review:"):
        self.assertUsageError("--dry-run", "--docs", str(self.docs), *extra, needle=needle)

    def test_real_tree_inventory(self):
        proc = self.dry()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        registry = json.loads(REGISTRY.read_text())
        dirs = [s["dir"] for s in out["skills"]]
        self.assertEqual(dirs, sorted(set(REAL_SKILLS)))
        by_dir = {s["dir"]: s for s in out["skills"]}
        for shared in ("barcode-capture-net-maui", "scandit-xamarin-to-net-migration"):
            self.assertEqual(by_dir[shared]["platforms"], ["net-ios", "net-android"])
        for p in out["platforms"]:
            expected = "ok" if registry["platforms"][p["key"]]["skills"] else "gap"
            self.assertEqual(p["status"], expected, p["key"])
        self.assertEqual({s["dir"] for s in out["skills"] if s["status"] == "not-assessed"},
                         set(registry["not_assessed"]))
        self.assertEqual(len([s for s in out["skills"] if s["status"] == "gap"]), 0)

    def test_unregistered_dir_is_gap(self):
        skills = self.skills_tree(REAL_SKILLS + ["made-up-skill"])
        proc = self.dry("--skills", str(skills))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        gaps = [s["dir"] for s in json.loads(proc.stdout)["skills"] if s["status"] == "gap"]
        self.assertEqual(gaps, ["made-up-skill"])

    def test_platform_filter_keeps_full_inventory(self):
        out = json.loads(self.dry("--platform", "ios").stdout)
        self.assertEqual([p["key"] for p in out["platforms"]], ["ios"])
        self.assertEqual([s["dir"] for s in out["skills"]], REAL_SKILLS)

    def test_unknown_platform_exits_2(self):
        self.assertDryUsageError("--platform", "nope")

    def test_missing_notes_file_exits_2(self):
        (self.docs / "docs/sdks/ios/release-notes.md").unlink()
        self.assertDryUsageError()

    def test_unselected_missing_notes_file_is_fine(self):
        (self.docs / "docs/sdks/ios/release-notes.md").unlink()
        self.assertEqual(self.dry("--platform", "web").returncode, 0)

    def test_unreadable_registry_exits_2(self):
        bad = self.tmp / "registry.json"
        bad.write_text("{")
        self.assertDryUsageError("--registry", str(bad))

    def test_skills_not_a_directory_exits_2(self):
        self.assertDryUsageError("--skills", str(self.tmp / "nope"), needle="--skills is not a directory")

    def test_unlistable_skills_dir_exits_2(self):
        skills = self.skills_tree(REAL_SKILLS)
        skills.chmod(0o000)
        self.addCleanup(skills.chmod, 0o755)
        self.assertDryUsageError("--skills", str(skills), needle="cannot list --skills")

    @unittest.skipIf(os.geteuid() == 0, "chmod does not restrict root")
    def test_untraversable_docs_dir_exits_2(self):
        locked = self.docs / "docs"
        locked.chmod(0o000)
        self.addCleanup(locked.chmod, 0o755)
        self.assertDryUsageError("--platform", "ios", needle="notes file for ios")

    @unittest.skipIf(os.geteuid() == 0, "chmod does not restrict root")
    def test_untraversable_skills_parent_exits_2(self):
        skills = self.skills_tree(REAL_SKILLS)
        self.tmp.chmod(0o000)
        self.addCleanup(self.tmp.chmod, 0o755)
        self.assertDryUsageError("--skills", str(skills), needle="--skills")

    def test_registry_missing_rules_field_exits_2(self):
        for field in ("products", "sections"):
            with self.subTest(field=field):
                path = self.registry_with(lambda d: d.pop(field))
                self.assertDryUsageError("--registry", str(path), needle=repr(field))

    def test_registry_malformed_rules_field_exits_2(self):
        cases = {
            "must map product names": lambda d: d.update(products={"Barcode": "barcode-"}),
            "must be a non-empty list": lambda d: d.update(sections=[]),
        }
        for needle, mutate in cases.items():
            with self.subTest(needle=needle):
                path = self.registry_with(mutate)
                self.assertDryUsageError("--registry", str(path), needle=needle)

    def test_notes_path_outside_docs_exits_2(self):
        outside = self.tmp / "other-clone" / "notes.md"
        outside.parent.mkdir()
        outside.write_text("# notes\n")
        path = self.registry_with(lambda d: d["platforms"]["ios"].update(notes=str(outside)))
        self.assertDryUsageError("--registry", str(path), needle="outside --docs")

    def test_registry_skills_not_directories_listed_together(self):
        skills = self.skills_tree([n for n in REAL_SKILLS if n not in ("id-bolt", "scandit-linux-sdk")])
        self.assertDryUsageError("--skills", str(skills), needle="id-bolt, scandit-linux-sdk")

    def test_platform_entry_missing_skills_exits_2(self):
        self.assertDryUsageError("--registry", str(self.registry_with(
            lambda d: d["platforms"]["ios"].pop("skills"))))

    def test_non_string_skill_entry_exits_2(self):
        self.assertDryUsageError("--registry", str(self.registry_with(
            lambda d: d["platforms"]["ios"]["skills"].append(["x"]))))

    def test_skill_both_mapped_and_not_assessed_exits_2(self):
        path = self.registry_with(lambda d: d["not_assessed"].update({"scandit-linux-sdk": "x"}))
        self.assertDryUsageError("--registry", str(path), needle="scandit-linux-sdk")

    def test_without_dry_run_exits_2(self):
        self.assertUsageError("--docs", str(self.docs), needle="--max-calls")


if __name__ == "__main__":
    unittest.main()
