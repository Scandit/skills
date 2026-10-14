# Migration evals

Runs `claude -p` over each third-party migration eval (`evals/<skill>/third-party-migration-evals.json`),
then scores every output: does it compile, and does it still enable every symbology the original scanned.

```sh
python3 internal/migration-evals/run.py --skill barcode-capture-flutter
python3 internal/migration-evals/run.py --skill barcode-capture-flutter --ids 1,3 --jobs 2 --model sonnet
python3 internal/migration-evals/run.py --skill barcode-capture-flutter --score-only eval-runs/migration/<stamp>
```

Env: `CLAUDE` overrides the claude binary, `FLUTTER` the flutter binary used by the gate.
Each eval runs in its own temp project with this checkout loaded via `--plugin-dir`
and only project settings, so installed plugins do not leak in.

## Output

`eval-runs/migration/<UTC stamp>/` (gitignored):

- `report.md`, `report.json`: per-fixture compiles, errors left, symbologies kept, claude exit/turns/cost; skills sha plus dirty flag.
- `<skill>/<id>/lib/<Main>.dart` and `lib/stubs/*`: the migrated files; `claude.json`, `claude.stderr`: raw claude output; `run.json`: exit code and timeout, reloaded by `--score-only`.
  Each `<id>/` is cleared before its run, so reusing `--out` never scores stale files.

## Scoring

- `compiles`: the suite's gate exits 0. `n/a` when the gate is skipped (flutter absent) or the output file is missing.
- `resolve-fail`: gate failed with no analyzer error lines (for example `pub get`).
- `symbologies kept`: expected ids come from the original fixture (a literal `formats:` list mapped through
  `internal/symbology-map/mapping.json`, else `default_set`); each must reach an enabling call in the migrated
  files: `enableSymbologies(…)` (an identifier argument resolves to its collection literal),
  `enableSymbology(Symbology.<name>, true)` or `settingsForSymbology(Symbology.<name>).isEnabled = true`.
  Comments and string literals are ignored. When the original has no format list
  (scans everything), a migrated subset counts as kept and shows as `narrowed (enabled: …)`; enabling none is not kept.
  Known limit: a static heuristic, so sets built at runtime or passed through functions or fields are not traced.

## Adding a gate

Add a `Suite` entry to `SUITES` in `score.py` with its gate, source, lang, error-line regex, allowed
tools and prompt suffix. The gate is run as `bash <gate> <main file> <stub files...>` and reports through
its exit code (0 pass, 1 fail, 3 skip). The workdir layout (`lib/`, `lib/stubs/`, `pubspec.yaml`) and the
`formats:` parser are Flutter-shaped; the next gate extends `Suite` with its own layout and parser.

Tests: `python3 -m unittest discover -s internal/migration-evals -p 'test_*.py'`
(`MIGRATION_EVALS_FLUTTER=1` also runs the real gate).
