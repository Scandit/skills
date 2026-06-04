---
name: skill-auditor
description: Maintainer tool for this repo. Use when the user wants to audit the skill catalog — check eval coverage ("which edge cases have no eval on <platform>?", "check eval coverage for <product>"), check cross-platform consistency ("are the sparkscan skills consistent?", "audit skill quality"), verify the routing table ("is the handoff table in sync?"), lint skill structure, refresh a product feature taxonomy, or run a full audit. Also use when a batch of new skills lands and the catalog needs re-validation, or before a release of the skill repo.
license: MIT
metadata:
  author: scandit
  version: "0.1.0"
---

# Skill Auditor

Audits the skill catalog in this repo along three layers, per `<product>-<platform>` skill:

1. **Platform truth** — what the platform actually supports. The expected surface is the
   native API minus the documented exclusions in the SDK repo's `docs/api_availability/`
   data, enriched with public-docs sections and sample-app usage. Platforms genuinely
   diverge; a capability absent on a platform is not a defect — an *undocumented or
   untested* capability that the platform supports is.
2. **Eval coverage** — does every supported edge case have an eval? Measured by
   `scripts/coverage_matrix.py` against the product taxonomy.
3. **Skill quality** — is each skill the best version of itself for its customers?
   Missing gotcha warnings, guidance buried in references that belongs frontloaded,
   claims contradicting the platform API, and improvement patterns worth transferring
   from a sibling skill (transfer the *pattern*, not the content).

Sibling-parity differences are **hints feeding layer 3 as questions, never failures**.
Never recommend "make platform X match platform Y" without first checking platform X's
actual API surface.

## Maintenance model

**The taxonomy is regenerated, not hand-edited.** `taxonomies/<product>.yaml` is the list
of capabilities checked across a product's platforms — but treat it like a lockfile, not a
hand-kept document. `audit taxonomy <product>` *derives* it from the sources of truth
(`products.json` / `features.json`, doc sections, samples, `api_availability` exclusions)
and proposes a delta; a human blesses the delta. Steady state when the SDK or docs change:
re-run `audit taxonomy`, review the proposed diff, commit. The human owns *blessing the
delta*, not keeping the list current by hand. (The seed taxonomies in this repo are
hand-written pilots until the mining step is built — see the caveat in `audit taxonomy`.)

**Discrepancies are detected, truth-verified, then confirmed — never auto-applied.** The
flow is always propose-and-confirm:

1. Cheap signal: sibling diff / coverage matrix surfaces "platform X has Y, platform Z
   doesn't."
2. Verify against platform truth (layer 1) BEFORE asking: does Z actually support Y? If
   yes → real gap, worth aligning. If no → legitimate divergence, record it as an
   `excluded_platforms` entry so it stops surfacing. **Parity is never the goal in
   itself** — coverage of each platform's real capability is.
3. Ask the human which verified gaps to fill; draft the fix for review; never commit
   silently.

So "put platforms on par" is the *outcome of a confirmed, truth-checked decision*, not an
automatic rule.

## Sources

All external locations come from `sources.yaml` (committed registry) overlaid with
`sources.local.yaml` (machine-local checkout paths, gitignored — see
`sources.local.yaml.example`). Never invent or guess a URL or path; if a needed source
is not in the registry, report "source missing from manifest" instead.

Resolution per repo: local `path:` if configured (READ-ONLY — record HEAD SHA + branch
into provenance, warn if dirty or not on the default branch, never fetch/checkout/mutate)
→ cached shallow clone for public repos (`~/.cache/scandit-skill-auditor/`) → for private
sources with no path, ask the user once and write `sources.local.yaml`; in CI, skip the
mode and say so visibly.

When entering a source repo, read its own navigation aids first (`CLAUDE.md`,
`AGENTS.md`, `commands.md`, bundled skills) instead of raw-searching it.

Samples: prefer checkouts of the public `datacapture-*-samples` repos — they reflect
released behavior, which is what evals target. The copies inside the SDK monorepo track
`develop`; use them only for what's-coming / API-surface questions.

## Modes

Dispatch on what the user asks for. Run scripts from the repo root with `python3`.

### `audit routing`

Run `scripts/lint_structure.py` and report only the `routing:` findings: skills missing
from the `data-capture-sdk` handoff table, and table rows pointing at skills that don't
exist. These are always real defects — the router silently falls back to "no skill
exists" for unrouted skills. Offer to fix the table directly (follow the existing row
format, grouped by product).

The script only checks the backticked table. Afterwards, read the router's prose for
product+platform claims the script can't see — especially the Step 3 fallback examples
("no skill exists for X on Y"): each cited combo must still be absent from `skills/`.
Prose examples go stale exactly when a new skill lands (happened with
barcode-capture-ios in PR #48).

### `audit structure [product-prefix]`

Run `scripts/lint_structure.py [--prefix <prefix>]`. Frontmatter and routing findings are
defects. Sibling-parity findings are *review candidates*: for each, check layer 1 before
judging — if the platform supports the feature (per `api_availability` exclusions and
`features.json`), the missing file/eval is a real gap; if not, it's expected divergence
and should be recorded as an `excluded_platforms` entry in the product taxonomy so it
stops surfacing. Product prefixes and parity exemptions live in `manifest.json`.

### `audit evals <product>`

1. Run `scripts/coverage_matrix.py taxonomies/<product>.yaml`. If no taxonomy exists yet,
   run `audit taxonomy <product>` first.
2. For each gap, triage: real gap (platform supports it) / platform exclusion (record it
   in the taxonomy) / not worth testing (justify — an eval per API setter is noise).
3. Rank real gaps by evidence: a feature backed by docs ∧ sample ∧ support signals
   outranks one backed by a single source.
4. For top gaps, draft evals. Often the fastest path is porting a sibling platform's eval
   for the same feature — re-target the prompt and APIs, don't copy assertions verbatim.
   Follow the conventions in `references/eval-conventions.md`. Match the per-product eval
   file layout the siblings use; put new evals in the matching `evals/*.json` file.
5. Once evals carry explicit `tags`, tags are the source of truth and the taxonomy
   `match` patterns only catch new untagged evals.

### `audit consistency <product>`

Judgment pass over sibling skills (validated mode — high signal). Fan out subagents in
parallel, one per platform pair or per platform against a shared checklist, comparing
SKILL.md + references. Report only semantic divergence, never legitimate platform
differences (different APIs, naming conventions, lifecycle models are fine). Look for:

- Product-level claims that disagree (capabilities, limits, migration scope, version
  guidance) — e.g. one platform calling a migration "light" while a sibling documents
  breaking changes. Verify against platform truth before recommending a fix.
- Gotchas/warnings present on one platform whose *analogue* exists but is undocumented
  on another (init-order footguns, anti-pattern warnings, permission timing).
- Setup-checklist completeness drift.
- Guidance placement: critical content buried in references on one platform but
  frontloaded on another.

For each finding: severity (high = could mislead a user), the evidence on both sides,
and the concrete fix. Verify claims against layer-1 sources before proposing edits.

### `audit taxonomy <product>`

Seed or refresh `taxonomies/<product>.yaml`. Mine sources in evidence order, fanning out
parallel subagents (one per source class) that return structured feature candidates:

1. `public_docs` feeds (`products.json`, `features.json`) and per-mode doc sections —
   every doc section is a candidate edge case.
2. Samples — each sample demonstrates a blessed workflow.
3. `api_availability` exclusions — populate `excluded_platforms`, and surface *expired*
   exclusions (capability just became coverable → new candidate).
4. `internal_docs` RST corpus — real-world edge cases.

Propose the taxonomy delta to the user for blessing before writing; record provenance
(source + SHA) in the file header. Prioritize: this is a curated edge-case list, not an
API dump. Use `taxonomies/sparkscan.yaml` as the format reference.

### `audit all`

Run routing + structure + evals + consistency for every product with a taxonomy, then
delegate to the `audit-common-skill-rules` skill for the universal trust-rule check.
Summarize per product, leading with required-feature gaps and high-severity consistency
findings. State explicitly which products/modes were skipped and why (no taxonomy,
source not configured) — silent truncation reads as full coverage.

## Reporting

Lead with what's actionable: required gaps and high-severity divergences first, counts
after, raw listings last (or in a file under the workspace if long). Every
recommendation must cite its evidence (file, eval id, doc section, exclusion rule).
The goal of every audit is a concrete next action — an eval to port, a warning to add,
a table row to fix — not a score.
