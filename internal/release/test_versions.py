import json
import shutil
import tempfile
import unittest
from pathlib import Path

import versions

REPO = Path(__file__).resolve().parents[2]


class VersionsTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        for rel in versions.PLUGIN_MANIFESTS + versions.MARKETPLACES:
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(REPO / rel, self.root / rel)

    def edit(self, rel, change):
        path = self.root / rel
        data = json.loads(path.read_text())
        change(data)
        path.write_text(json.dumps(data, indent=2))

    def test_repo_is_aligned(self):
        self.assertEqual(versions.check(REPO, None), [])

    def test_drifted_manifest_fails(self):
        self.edit(".cursor-plugin/plugin.json", lambda d: d.update(version="0.0.1"))
        self.assertTrue(any("versions differ" in p for p in versions.check(self.root, None)))

    def test_missing_plugin_version_fails(self):
        self.edit(".claude-plugin/plugin.json", lambda d: d.pop("version"))
        self.assertIn(".claude-plugin/plugin.json: no version", versions.check(self.root, None))

    def test_missing_marketplace_metadata_version_fails(self):
        for rel in versions.VERSIONED_MARKETPLACES:
            with self.subTest(rel=rel):
                self.setUp()
                self.edit(rel, lambda d: d["metadata"].pop("version"))
                self.assertIn(f"{rel}: no metadata.version", versions.check(self.root, None))
                self.assertTrue(versions.set_version(self.root, "7.8.9"))

    def test_marketplace_entry_version_fails(self):
        self.edit(".github/plugin/marketplace.json", lambda d: d["plugins"][0].update(version="9.9.9"))
        self.assertTrue(any("plugin entry" in p for p in versions.check(self.root, None)))

    def test_tag_mismatch_fails(self):
        self.assertTrue(any("does not match" in p for p in versions.check(self.root, "v0.0.0")))

    def test_set_bumps_every_manifest(self):
        self.assertEqual(versions.set_version(self.root, "7.8.9"), [])
        found, _ = versions.collect(self.root)
        self.assertEqual(set(found.values()), {"7.8.9"})
        self.assertEqual(versions.check(self.root, "v7.8.9"), [])

    def test_set_leaves_nested_version_keys_alone(self):
        self.edit(".claude-plugin/plugin.json", lambda d: d.update(extra={"version": "2.0.0"}))
        self.assertEqual(versions.set_version(self.root, "7.8.9"), [])
        data = json.loads((self.root / ".claude-plugin/plugin.json").read_text())
        self.assertEqual((data["version"], data["extra"]["version"]), ("7.8.9", "2.0.0"))

    def test_set_refuses_ambiguous_version_line(self):
        rel = ".claude-plugin/plugin.json"
        self.edit(rel, lambda d: d.update(extra={"version": d["version"]}))
        before = (self.root / ".codex-plugin/plugin.json").read_text()
        self.assertTrue(any("more than once" in p for p in versions.set_version(self.root, "7.8.9")))
        self.assertEqual((self.root / ".codex-plugin/plugin.json").read_text(), before)

    def test_set_rejects_non_semver(self):
        self.assertTrue(versions.set_version(self.root, "1.2"))


if __name__ == "__main__":
    unittest.main()
