"""Antigravity manifest checks that `agy plugin validate` would otherwise catch.

`agy` is not available in CI, so this mirrors the parts of
https://antigravity.google/schemas/v1/plugin.json and the build-plugins guide
that we can break by editing JSON by hand.
"""

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / ".antigravity-plugin/plugin.json"

# Top-level keys the v1 schema allows (`additionalProperties: false`).
ALLOWED_KEYS = {
    "$schema", "name", "displayName", "display_name", "description", "version",
    "disabled", "logo", "suggestedPrompts", "suggested_prompts", "skills",
    "author", "homepage", "repository", "license", "keywords", "extensions",
}
# Fields the Antigravity Marketplace requires.
MARKETPLACE_KEYS = {"name", "displayName", "description", "version", "logo", "suggestedPrompts", "author"}


class AntigravityManifestTest(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(MANIFEST.read_text())

    def test_only_schema_keys(self):
        self.assertEqual(set(self.manifest) - ALLOWED_KEYS, set())

    def test_marketplace_fields_present(self):
        self.assertEqual(MARKETPLACE_KEYS - set(self.manifest), set())

    def test_name_is_lowercase_kebab(self):
        self.assertRegex(self.manifest["name"], r"^[a-z0-9]+(-[a-z0-9]+)*$")

    def test_suggested_prompts(self):
        prompts = self.manifest["suggestedPrompts"]
        self.assertLessEqual(len(prompts), 3)
        self.assertTrue(all(p.strip() for p in prompts))

    def test_logo_is_bundled(self):
        self.assertTrue((REPO / self.manifest["logo"]).is_file())

    def test_author_object_keys(self):
        author = self.manifest["author"]
        self.assertEqual(set(author) - {"name", "email", "url"}, set())
        self.assertTrue(author.get("url", "https://").startswith("https://"))

    def test_mcp_matches_other_hosts(self):
        """mcp_config.json must point at the same server as .mcp.json."""
        agy = json.loads((REPO / "mcp_config.json").read_text())["mcpServers"]
        other = json.loads((REPO / ".mcp.json").read_text())["mcpServers"]
        self.assertEqual(set(agy), set(other))
        for name, server in agy.items():
            self.assertNotIn("type", server, "Antigravity infers transport from serverUrl")
            self.assertEqual(server.get("serverUrl"), other[name]["url"])

    def test_skill_names_match_folders(self):
        for skill in sorted((REPO / "skills").iterdir()):
            text = (skill / "SKILL.md").read_text()
            name = re.search(r"^name:\s*(\S+)\s*$", text, re.M)
            self.assertIsNotNone(name, skill.name)
            self.assertEqual(name.group(1), skill.name)


if __name__ == "__main__":
    unittest.main()
