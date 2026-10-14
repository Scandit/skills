# Migration evals

Runs `claude -p` over each third-party migration eval (`evals/<skill>/third-party-migration-evals.json`),
then scores every output: does it compile, and does it still enable every symbology the original scanned.

```sh
python3 internal/migration-evals/run.py --skill barcode-capture-flutter
python3 internal/migration-evals/run.py --skill barcode-capture-flutter --ids 1,3 --jobs 2 --model sonnet
python3 internal/migration-evals/run.py --skill barcode-capture-rn --ids 1,2,3 --sdk-version 8.6.1
python3 internal/migration-evals/run.py --skill barcode-capture-capacitor
python3 internal/migration-evals/run.py --skill barcode-capture-flutter --score-only eval-runs/migration/<stamp>
```

Env: `CLAUDE` overrides the claude binary, `FLUTTER` the flutter binary used by the gate. RN and Capacitor suites type-check with
`internal/skill-auditor/scripts/fix_gate_ts.sh` (node + npm) against the SDK from `--sdk-version` (default 8.6.1).
Each eval runs in its own temp project with this checkout loaded via `--plugin-dir`
and only project settings, so installed plugins do not leak in.

## Output

`eval-runs/migration/<UTC stamp>/` (gitignored):

- `report.md`, `report.json`: per-fixture compiles, errors left, symbologies kept, claude exit/turns/cost; skills sha plus dirty flag.
- `<skill>/<id>/lib/<Main>.dart` and `lib/stubs/*` (RN and Capacitor: the files flat in `<id>/`): the migrated files; `claude.json`, `claude.stderr`: raw claude output; `run.json`: exit code and timeout, reloaded by `--score-only`.
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
  RN and Capacitor also trace the `symbologies={…}` prop of `BarcodeCaptureAioView`; format lists are `codeTypes` /
  `barcodeFormats` / `barcodeTypes` (RN) and `formats` (Capacitor), unioned across every list in the file.
  An identifier argument that is a function parameter counts every named list literal of symbologies in the files.
  Known limit: a static heuristic, so sets built at runtime or held in fields are not traced.
- RN and Capacitor gate with `FIX_GATE_TS_ANY_MODULE=1`: app modules the gate cannot install (rxjs, Angular, Vue,
  `react-native-fs`, app-local paths) are typed `any`, while Scandit, React and React Native resolve for real. So a
  migrated file that still imports the old scanner fails with one error per import, even when the gate passes:
  `react-native-vision-camera`, `react-native-vision-camera-barcode-scanner`, `expo-camera` (RN) and
  `@capacitor-mlkit/barcode-scanning` (Capacitor). Known limit: strict-mode errors in the app's own code stay counted
  (Capacitor id 4 keeps the ones its unmigrated original has too).

## Adding a gate

Add a `Suite` entry to `SUITES` in `score.py` with its gate, format lists (list key to mapping source), lang,
error-line regex, allowed tools and prompt suffix. A suite with a `platform` runs
`bash <gate> <platform> <main> <sdk version> <extra files...>`, otherwise `bash <gate> <main> <stub files...>`;
the gate reports through its exit code (0 pass, 1 fail, 3 skip). A `platform` suite copies every eval file by name
into the workdir root; the Flutter suite uses `lib/`, `lib/stubs/` and `pubspec.yaml`.

Tests: `python3 -m unittest discover -s internal/migration-evals -p 'test_*.py'`
(`MIGRATION_EVALS_FLUTTER=1` also runs the real gate).
