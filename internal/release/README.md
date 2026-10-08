# Release tooling

Internal. This directory is stripped from every published plugin bundle.

## Cutting a release

Every plugin manifest, and the Cursor and Copilot marketplace `metadata`,
carries one version, and every release bumps it. Installed copies on all channels only update when that string
changes, so a merge without a bump reaches nobody who already installed.

1. `internal/release/versions.py set 1.2.0`, commit, merge.
2. Tag the merge commit: `git tag v1.2.0 && git push origin v1.2.0`.
   `versions.py check --tag v1.2.0` confirms the tag matches the manifests.
3. Publish to the directories that pin a reviewed snapshot:
   [Claude Code](#claude-code-official-directory) and
   [OpenAI](#openai-plugin-directory).

`versions.py check` runs in the pre-push hook and in `publish-dist`, so
manifests that drift apart never reach `dist`.

## Claude Code official directory

`scandit-sdk@claude-plugins-official` is pinned to one commit of this repo in
[anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official/blob/main/.claude-plugin/marketplace.json).
New commits go live only after Anthropic reviews them and moves the pin. No
resubmission is needed, but until their automatic pickup ships, send our
Anthropic partner contact the release tag and the `dist` commit built from it.
`publish-dist` creates that commit on GitHub, so wait for its run on the tagged
commit to finish, then fetch before looking it up (empty output = not built yet):

```bash
git fetch origin dist
git log origin/dist --format=%H -1 --grep "built from main $(git rev-parse v1.2.0^{commit})"
```

Ask for the `dist` commit, not the tag: `main` also carries `evals/` and
`internal/`, which the plugin cache would then clone.

## OpenAI plugin directory

`build_openai_bundle.py` packages the ZIP that the OpenAI plugin submission
portal takes, Scandit MCP server included, and validates it first against the
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
frozen, reviewed snapshot, so nothing shipped to `main` reaches directory
users until a new version is reviewed and published. Each update is:

1. [Cut a release](#cutting-a-release). The portal refuses a version it has
   already published (`plugin_version_unchanged`), and `name` must stay
   `scandit-sdk` (`plugin_name_mismatch` blocks the upload otherwise).
2. `internal/release/build_openai_bundle.py --ref v1.2.0`.
3. Install the ZIP locally and run the submission test cases against that exact
   tree, not against a working checkout.
4. In the portal, create a new draft version of the existing plugin, upload the
   ZIP, write release notes describing what changed, and submit for review.
5. Publish the approved version. It replaces the previous one.

Only one version can be published and one in review at a time. To change
anything after submitting, cancel the review in the portal and resubmit. Skill
safety and security scans can take up to two hours, so do not treat a
resubmission as same-day.

The repo-marketplace channel (`codex plugin marketplace add scandit/skills`) picks
up each release straight from the repo, with no portal review. The two channels
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

The bundle keeps `.mcp.json` and the manifest's `mcpServers`: the skills call
the Scandit MCP server for licence keys, and without it the portal reports no
MCP. The builder requires exactly one remote HTTPS server, the portal's limit.
After upload, connect it on the draft's MCPs tab (domain verification on
`ssl.scandit.com`). OpenAI does not support adding an MCP server to an existing
skills-only plugin, so the first MCP upload may need a new plugin draft. Bundles
must not carry `interface.screenshots`, `apps`, or `.app.json`.
