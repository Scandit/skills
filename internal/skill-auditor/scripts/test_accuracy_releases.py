"""Tests for accuracy_review.py --from/--to on a temp git repo built from the real docs-notes fixtures."""
import functools
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from common import AUDITOR_ROOT
from test_accuracy_review import REGISTRY, run

FIXTURES = AUDITOR_ROOT / "fixtures" / "release-notes"
HISTORY = ("92a9e4d1", "d63a3be5", "d12a7c9c", "ae41ae70")
PLATFORMS = ("ios", "android", "web", "cordova", "react-native", "flutter", "kmp",
             "capacitor", "titanium", "net-ios", "net-android", "linux")
SPLIT_870 = {"android": 29, "capacitor": 25, "cordova": 25, "flutter": 23, "ios": 30, "kmp": 21,
             "linux": 16, "net-android": 25, "net-ios": 25, "react-native": 29, "titanium": 10, "web": 26}
CORE_ONLY_863 = ("ios", "capacitor", "cordova", "flutter", "react-native")


def git(repo, *args):
    ident = ("-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false")
    return subprocess.run(["git", *ident, "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


class ReleaseCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls._tmp.name)
        cls.docs = cls.tmp / "docs-clone"
        cls.docs.mkdir()
        git(cls.docs, "init", "-q")
        cls.sha = {}
        for name in HISTORY:
            shutil.copytree(FIXTURES / name / "docs", cls.docs / "docs", dirs_exist_ok=True)
            git(cls.docs, "add", "-A")
            git(cls.docs, "commit", "-q", "-m", name)
            cls.sha[name] = git(cls.docs, "rev-parse", "HEAD")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def dry(self, *extra):
        return run("--dry-run", "--docs", str(self.docs), *extra)

    def releases(self, frm="92a9e4d1", to="ae41ae70", *extra):
        out = self._releases(frm, to, *extra)
        self.assertEqual(out[0], 0, out[1])
        return json.loads(out[2])

    @classmethod
    @functools.cache
    def _releases(cls, frm, to, *extra):
        proc = run("--dry-run", "--docs", str(cls.docs), "--from", cls.sha[frm], "--to", cls.sha[to], *extra)
        return proc.returncode, proc.stderr, proc.stdout

    def by_version(self, out):
        return {r["version"]: {p["key"]: p for p in r["platforms"]} for r in out["releases"]}

    def registry_with(self, mutate):
        data = json.loads(REGISTRY.read_text())
        mutate(data)
        path = self.tmp / "registry.json"
        path.write_text(json.dumps(data))
        return path

    def test_lists_new_releases_on_all_platforms(self):
        out = self.releases()
        self.assertEqual([r["version"] for r in out["releases"]], ["8.7.1", "8.7.0", "8.6.3"])
        self.assertEqual((out["from"], out["to"]), (self.sha["92a9e4d1"], self.sha["ae41ae70"]))
        for release in out["releases"]:
            self.assertEqual({p["key"] for p in release["platforms"]}, set(PLATFORMS))

    def test_unknown_from_or_to_exits_2(self):
        for flags in (("--from", "deadbeef"), ("--from", self.sha["92a9e4d1"], "--to", "nope")):
            with self.subTest(flags=flags):
                proc = self.dry(*flags)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("accuracy_review:", proc.stderr)
                self.assertNotIn("Traceback", proc.stderr)

    def test_non_positive_max_batch_bytes_exits_2(self):
        proc = self.dry("--from", self.sha["92a9e4d1"], "--max-batch-bytes", "0")
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("accuracy_review: --max-batch-bytes must be positive", proc.stderr)

    def test_to_without_from_exits_2(self):
        proc = self.dry("--to", self.sha["ae41ae70"])
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("accuracy_review: --to needs --from", proc.stderr)

    def test_not_a_git_repo_exits_2(self):
        plain = self.tmp / "plain"
        shutil.copytree(self.docs / "docs", plain / "docs")
        proc = run("--dry-run", "--docs", str(plain), "--from", "HEAD")
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("accuracy_review:", proc.stderr)

    def test_notes_file_absent_at_from_counts_every_heading_as_new(self):
        repo = self.tmp / "new-platform"
        shutil.copytree(FIXTURES / "ae41ae70" / "docs", repo / "docs")
        kmp = repo / "docs/sdks/kmp/release-notes.md"
        text = kmp.read_text()
        kmp.unlink()
        git(repo, "init", "-q")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "without kmp")
        kmp.write_text(text)
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "kmp")
        proc = run("--dry-run", "--docs", str(repo), "--from", "HEAD~1")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        releases = json.loads(proc.stdout)["releases"]
        self.assertEqual({p["key"] for r in releases for p in r["platforms"]}, {"kmp"})
        self.assertEqual(len(releases), len(re.findall(r"^## \d+\.\d+\.\d+$", text, re.M)))

    def test_link_only_edits_list_no_release(self):
        self.assertEqual(self.releases("d63a3be5", "d12a7c9c")["releases"], [])

    def test_older_to_is_not_an_error(self):
        out = self.releases("ae41ae70", "92a9e4d1")
        self.assertEqual(out["releases"], [])

    def test_item_counts_and_ids(self):
        versions = self.by_version(self.releases())
        self.assertEqual({k: p["items"] for k, p in versions["8.7.0"].items()}, SPLIT_870)
        self.assertEqual(sum(p["items"] for p in versions["8.7.0"].values()), 284)
        self.assertEqual(sum(p["items"] for p in versions["8.7.1"].values()), 0)
        self.assertEqual({k: p["items"] for k, p in versions["8.6.3"].items() if p["items"]},
                         {k: 1 for k in CORE_ONLY_863})
        self.assertEqual(sum(p["items"] for p in versions["8.6.3"].values()), 5)
        ios = versions["8.7.0"]["ios"]["entries"]
        self.assertEqual([e["id"] for e in ios], [f"ios/8.7.0/{n}" for n in range(1, 31)])

    def test_item_text_includes_nested_bullets_and_indented_paragraphs(self):
        versions = self.by_version(self.releases())
        core = versions["8.6.3"]["ios"]["entries"][0]
        self.assertEqual((core["section"], core["product"]), ("New Features", "Core"))
        self.assertIn("add the following sources to your app’s Podfile\n\n```\n"
                      "source 'https://github.com/Scandit/scandit-cocoapods-specs.git'", core["text"])
        self.assertIn("\n\nThen run pod install --repo-update.", core["text"])
        self.assertNotIn("Optimized the capture of AAMVA", core["text"])
        nested = [e for e in versions["8.7.0"]["android"]["entries"]
                  if e["text"].startswith("Changed 1D symbology decoding")]
        self.assertEqual(len(nested), 1)
        self.assertIn("\n- Reduced false scans of EAN-13/UPC-A and Code 93", nested[0]["text"])

    def test_every_item_is_mapped_or_no_skill(self):
        versions = self.by_version(self.releases())
        for version, platforms in versions.items():
            for key, row in platforms.items():
                with self.subTest(version=version, platform=key):
                    self.assertEqual(row["mapped"] + row["no_skill"], row["items"])
                    self.assertEqual(row["mapped"], sum(1 for e in row["entries"] if e["skills"]))
        titanium = versions["8.7.0"]["titanium"]
        self.assertEqual((titanium["mapped"], titanium["no_skill"]), (0, 10))
        self.assertEqual(titanium["planned_calls"], 0)
        core = versions["8.6.3"]["ios"]["entries"][0]
        self.assertIn("barcode-capture-ios", core["skills"])
        self.assertEqual(len(core["skills"]), 10)
        linux = [e for e in versions["8.7.0"]["linux"]["entries"] if e["product"] == "Barcode"]
        self.assertGreater(len(linux), 0)
        self.assertTrue(all(e["skills"] == ["scandit-linux-sdk"] for e in linux))

    def test_docs_inside_another_repo_exits_2(self):
        shutil.copytree(self.docs / "docs", self.docs / "plain" / "docs")
        self.addCleanup(shutil.rmtree, self.docs / "plain")
        proc = run("--dry-run", "--docs", str(self.docs / "plain"), "--from", self.sha["92a9e4d1"])
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("not the root of a git worktree", proc.stderr)

    def test_unreadable_notes_blob_exits_2(self):
        clone = self.tmp / "broken-clone"
        shutil.copytree(self.docs, clone)
        self.addCleanup(shutil.rmtree, clone)
        blob = git(clone, "rev-parse", f"{self.sha['ae41ae70']}:docs/sdks/linux/release-notes.md")
        (clone / ".git" / "objects" / blob[:2] / blob[2:]).unlink()
        proc = run("--dry-run", "--docs", str(clone), "--from", self.sha["92a9e4d1"], "--to", self.sha["ae41ae70"])
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("cannot read docs/sdks/linux/release-notes.md", proc.stderr)

    def test_unknown_product_is_no_skill(self):
        before = self.by_version(self.releases())["8.7.0"]["ios"]
        ids = sum(1 for e in before["entries"] if e["product"] == "Id")
        self.assertGreater(ids, 0)
        registry = self.registry_with(lambda d: [d["products"].pop(k) for k in ("Id", "ID")])
        out = self.releases("92a9e4d1", "ae41ae70", "--registry", str(registry))
        after = self.by_version(out)["8.7.0"]["ios"]
        self.assertEqual(after["no_skill"], before["no_skill"] + ids)
        self.assertEqual(after["mapped"] + after["no_skill"], after["items"])

    def test_platform_filter_limits_release_rows(self):
        out = self.releases("92a9e4d1", "ae41ae70", "--platform", "web")
        self.assertEqual({p["key"] for r in out["releases"] for p in r["platforms"]}, {"web"})

    def test_sizing_on_a_fixture_skills_tree(self):
        skills = self.tmp / "skills"
        for name, files in {"barcode-a": {"a.md": 100, "z/b.md": 250}, "id-capture-b": {"c.md": 40}}.items():
            for rel, size in files.items():
                path = skills / name / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"x" * size)

        def narrow(data):
            for entry in data["platforms"].values():
                entry["skills"] = []
            data["platforms"]["ios"]["skills"] = ["barcode-a", "id-capture-b"]
            data["not_assessed"] = {}
        registry = self.registry_with(narrow)

        def sized(max_batch):
            out = self.releases("92a9e4d1", "ae41ae70", "--skills", str(skills), "--registry", str(registry),
                                "--max-batch-bytes", str(max_batch), "--platform", "ios")
            return self.by_version(out)

        row = sized(400000)["8.6.3"]["ios"]
        item_bytes = len(row["entries"][0]["text"].encode())
        # one Core item, all 3 skill files (100+250+40) fit one batch
        self.assertEqual((row["planned_calls"], row["input_bytes"], row["estimated_tokens"]),
                         (1, item_bytes + 390, (item_bytes + 390) // 4))
        self.assertEqual(row["skills"], ["barcode-a", "id-capture-b"])
        # budget = item + 300: files pack greedily as [100] | [250, 40]
        row = sized(item_bytes + 300)["8.6.3"]["ios"]
        self.assertEqual((row["planned_calls"], row["input_bytes"]), (2, 2 * item_bytes + 390))
        # a file that alone overflows still gets its own batch
        row = sized(item_bytes + 10)["8.6.3"]["ios"]
        self.assertEqual((row["planned_calls"], row["input_bytes"]), (3, 3 * item_bytes + 390))

        ios_870 = sized(400000)["8.7.0"]["ios"]
        mapped_groups = {e["product"] for e in ios_870["entries"] if e["skills"]}
        self.assertEqual(mapped_groups, {"Barcode", "Id", "Core"})
        self.assertEqual(ios_870["planned_calls"], 3)
        total_items = sum(len(e["text"].encode()) for e in ios_870["entries"] if e["skills"])
        files_total = {"Barcode": 350, "Id": 40, "Core": 390}
        self.assertEqual(ios_870["input_bytes"], total_items + sum(files_total.values()))

    def notes_repo(self, name, old, new, platform="web"):
        repo = self.tmp / name
        path = repo / json.loads(REGISTRY.read_text())["platforms"][platform]["notes"]
        path.parent.mkdir(parents=True)
        for message, text in (("a", old), ("b", new)):
            path.write_text(text)
            if message == "a":
                git(repo, "init", "-q")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", message)
        proc = run("--dry-run", "--docs", str(repo), "--from", "HEAD~1", "--platform", platform)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)["releases"]

    def test_parser_boundaries(self):
        new = ("## 9.0.0\n\n### New Features\n\n#### Core\n\n* A one\n  cont\nplain para\n  orphan\n* A two\n\n"
               "### Bug Fixes\n\n* dropped\n\n### Behavioral Changes\n\n* B one\n\n"
               "## Other heading\n\n### New Features\n\n* leaked\n")
        entries = self.notes_repo("parse", "", new)[0]["platforms"][0]["entries"]
        self.assertEqual([(e["section"], e["product"], e["text"]) for e in entries],
                         [("New Features", "Core", "A one\ncont"), ("New Features", "Core", "A two"),
                          ("Behavioral Changes", None, "B one")])
        self.assertEqual(entries[2]["skills"], [])

    def test_versions_sort_numerically(self):
        new = "".join(f"## {v}\n\n### New Features\n\n* x\n\n" for v in ("8.9.0", "8.10.0", "8.10.1"))
        self.assertEqual([r["version"] for r in self.notes_repo("sort", "", new)],
                         ["8.10.1", "8.10.0", "8.9.0"])

    def test_totals_sum_platform_rows(self):
        release = next(r for r in self.releases()["releases"] if r["version"] == "8.7.0")
        totals = release["totals"]
        self.assertEqual(totals["items"], 284)
        self.assertEqual(totals["items"], totals["mapped"] + totals["no_skill"])
        self.assertEqual(totals["input_bytes"], sum(p["input_bytes"] for p in release["platforms"]))
        self.assertEqual(totals["estimated_tokens"], totals["input_bytes"] // 4)

    @unittest.skipIf(os.geteuid() == 0, "chmod does not restrict root")
    def test_unreadable_skill_dir_exits_2(self):
        skills = self.tmp / "locked-skills"
        shutil.copytree(AUDITOR_ROOT.parents[1] / "skills", skills)
        locked = skills / "sparkscan-ios" / "references"
        locked.chmod(0o000)
        self.addCleanup(locked.chmod, 0o755)
        proc = self.dry("--skills", str(skills), "--platform", "ios",
                        "--from", self.sha["92a9e4d1"], "--to", self.sha["ae41ae70"])
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("cannot read skill files", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)


if __name__ == "__main__":
    unittest.main()
