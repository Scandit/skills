"""Tests for accuracy_review.py --dry-run, run as a subprocess so exit codes and stderr are real."""
import json
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
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


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
        dirs = [s["dir"] for s in out["skills"]]
        self.assertEqual(len(dirs), 87)
        self.assertEqual(dirs, sorted(set(dirs)))
        by_dir = {s["dir"]: s for s in out["skills"]}
        for shared in ("barcode-capture-net-maui", "scandit-xamarin-to-net-migration"):
            self.assertEqual(by_dir[shared]["platforms"], ["net-ios", "net-android"])
        platforms = {p["key"]: p for p in out["platforms"]}
        self.assertEqual(platforms["titanium"]["status"], "gap")
        self.assertEqual(platforms["ios"]["status"], "ok")
        self.assertEqual(len([s for s in out["skills"] if s["status"] == "not-assessed"]), 2)
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
        self.assertUsageError("--docs", str(self.docs), needle="only --dry-run is implemented")


if __name__ == "__main__":
    unittest.main()
