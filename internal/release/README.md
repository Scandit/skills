# Release tooling

Internal. This directory is stripped from every published plugin bundle.

## OpenAI plugin directory

`build_openai_bundle.py` packages the skills-only ZIP that the OpenAI plugin
submission portal takes on its Skills tab, and validates it first against the
rules in
[submission-errors](https://developers.openai.com/plugins/deploy/submission-errors).
There is no `codex plugin pack` command, so this script is the packer.

```bash
internal/release/build_openai_bundle.py --check-only     # validate HEAD, no ZIP
internal/release/build_openai_bundle.py --ref v1.1.0     # package a release tag
```

It exports the tree with `git archive`, so it packages committed content only
and a dirty checkout cannot leak into an upload. Output is deterministic: the
same ref always yields the same bytes and the same SHA-256, which is what makes
"the tree we tested is the tree we submitted" checkable rather than assumed.

Stripped from the bundle: `internal/`, the Claude, Cursor and Copilot manifests,
`.agents/`, `skills.sh.json`, `README.md`, `.gitignore`, and every
`skills/*/evals/` directory. `internal/` is the one exclusion that is a real
risk rather than hygiene: `skill-auditor/sources.yaml` names private Scandit
repos, and uploaded skills are scanned for sensitive information.

### Cutting a directory update

The OpenAI directory does **not** track this repo. An approved listing is a
frozen, reviewed snapshot, so nothing shipped to `master` reaches directory
users until a new version is reviewed and published. Each update is:

1. Bump `version` in `.codex-plugin/plugin.json`. A new release must not reuse
   the published version (`plugin_version_unchanged`), and `name` must stay
   `scandit-sdk` (`plugin_name_mismatch` blocks the upload otherwise).
2. Merge, then tag the release (`git tag v1.2.0 && git push origin v1.2.0`).
3. `internal/release/build_openai_bundle.py --ref v1.2.0`.
4. Install the ZIP locally and run the submission test cases against that exact
   tree, not against a working checkout.
5. In the portal, create a new draft version of the existing plugin, upload the
   ZIP, write release notes describing what changed, and submit for review.
6. Publish the approved version. It replaces the previous one.

Only one version can be published and one in review at a time. To change
anything after submitting, cancel the review in the portal and resubmit. Skill
safety and security scans can take up to two hours, so do not treat a
resubmission as same-day.

The repo-marketplace channel (`codex plugin marketplace add scandit/skills`) is
unaffected by any of this and keeps updating from the repo. The two channels
move at different speeds on purpose.

### Local install check

```bash
python3 internal/release/build_openai_bundle.py --out /tmp/b
mkdir -p /tmp/smoke/mkt/plugins /tmp/smoke/mkt/.agents/plugins
unzip -q /tmp/b/scandit-sdk-*.zip -d /tmp/smoke/mkt/plugins/scandit-sdk
# marketplace.json: one local entry with "path": "./plugins/scandit-sdk"
CODEX_HOME=/tmp/smoke/home codex plugin marketplace add /tmp/smoke/mkt
CODEX_HOME=/tmp/smoke/home codex plugin add scandit-sdk@bundle-smoke
CODEX_HOME=/tmp/smoke/home codex plugin list
```

### Listing limits worth knowing before editing copy

The portal enforces two tiers, and the strict tier only applies at final
directory submission, which is where a listing that passed upload validation can
still be rejected. The script checks the strict tier.

| Field | Upload validation | Final submission |
| --- | --- | --- |
| `interface.displayName` | 80 | **30** |
| `interface.shortDescription` | 240 | **30** |
| `interface.defaultPrompt` | 512 per prompt | **128 per prompt, at most 3 prompts** |
| Listing URLs | 2,048 | 1,024 |
| `interface.longDescription` | 4,000 | 4,000 |

Skills-only bundles must not carry `interface.screenshots`, `mcpServers`,
`apps`, `.mcp.json`, or `.app.json`. Screenshots require an MCP-backed
submission with custom UI.
