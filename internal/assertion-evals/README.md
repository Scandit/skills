# Assertion evals

Runs the assertion evals (`evals/<skill>/*evals.json`: integration, migration, feature suites) and scores each
assertion. A customer-usage simulation: the skill (`SKILL.md` plus every `references/*.md`) is the system prompt,
the eval prompt plus its fixture files is the user turn, and the model answers once with no tools.
Compile-gated third-party migrations are `internal/migration-evals`.

```sh
python3 internal/assertion-evals/run.py --skill barcode-capture-android --smoke
python3 internal/assertion-evals/run.py --skill 'id-capture-*' --files integration-evals --jobs 6
python3 internal/assertion-evals/run.py --skill sparkscan-flutter --ids 1,3 --reps 3
python3 internal/assertion-evals/run.py --skill 'label-capture-*' --ref main --out eval-runs/assertion/main   # A/B
python3 internal/assertion-evals/run.py --skill 'label-capture-*' --out eval-runs/assertion/pr
```

Runs through `claude -p` (`CLAUDE` overrides the binary), so a Claude Code login or `ANTHROPIC_API_KEY` is enough; no
Python dependencies. Sessions get no tools, no settings, MCP servers or skills, so installed plugins do not leak in.
`--ref` takes `skills/` from a git ref; evals and fixtures always come from the working tree.

Defaults: generator `claude-sonnet-5-5` at `--effort medium`, judge `claude-opus-4-7`. Changing either moves the
scores, so compare runs made with the same pair (both are recorded in `results.json`).

## Scoring

- **Deterministic first.** `X is [NOT] present|called|enabled`, where X looks like code, is a substring check on the
  output; `X or Y` passes on either; `Import from X` and `X import` look for an import statement.
- **Judge for the rest**: prose assertions and anything marked `(semantic`, all of one eval's assertions in one call
  (`<n>. PASS|FAIL: <reason>`; a missing line counts as `JUDGE_PARSE_ERROR`, a fail).
- **Migration suites** (file stem contains `migration`): absence assertions are checked against fenced code only, as
  answers name the old API in prose (`references/eval-conventions.md` in the skill auditor).
- Known limit: the generator has no tools, so a skill step like "fetch the latest SDK version" cannot run and the
  answer carries a placeholder.

## Output

`eval-runs/assertion/<UTC stamp>/` (gitignored): `results.json` (models, skills sha plus dirty flag, total cost, per eval
its output, assertions and `cost_usd`) and `summary.txt` (pass rate per skill, each failing assertion with its reason).

## Cost

Each eval is one generator session plus one judge call (two for a migration eval with both scopes), at about $0.15 to
$0.20 per eval on the defaults. A skill's suite costs a few dollars, the full catalog (about 1,300 evals) roughly $250.
Start with `--smoke` (first eval of each matched skill).

Tests: `python3 -m unittest discover -s internal/assertion-evals -p 'test_*.py'`
