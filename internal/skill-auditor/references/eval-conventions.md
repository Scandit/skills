# Eval conventions for this repo

House rules for writing or porting evals, learned across the existing suites. Follow
these whenever `audit evals` drafts new evals so they behave like the other 65 suites.

## Assertion wording

- Write assertions the hybrid judge can verify against the produced output: name the
  exact API literal expected in code (`DataCaptureContext.initialize(` ), not a
  paraphrase ("initializes the context properly").
- Positive presence checks beat vague quality checks. "prepareScanning() is called in
  viewWillAppear" survives the judge; "lifecycle is handled correctly" does not.
- Forbidden-API assertions ("X is NOT present") are string checks — except when X is a
  forbidden API the skill explicitly warns about; then phrase it semantically ("the
  deprecated DataCaptureContext(licenseKey:) constructor is NOT used") so a comment
  mentioning X doesn't fail the eval.

## Migration evals

Judge migration evals **against code blocks only**. Migration answers legitimately
mention old APIs in prose ("replace forLicenseKey with..."), so assertions about
old-API absence must scope to code, or they false-fail correct answers.

## Compile gates

String assertions alone pass non-compiling code. Where the platform has a cheap static
check, add it:

- Flutter: `flutter analyze` gate on the produced file.
- Web/TS: hand-write one `App.ts` from the skill's docs and run `tsc` — cheaper than a
  model-graded gate and doubles as a doc-fidelity check (if the docs can't produce
  compiling code, the docs are the bug).

## Snippet compile gate (skill reference content)

Never commit a code snippet into a skill's SKILL.md or references/ that has not been
compile-checked. String-verified-against-source is not enough — compile against the
**published** package (released behavior):

- Dart: temp project with the pub.dev package + `dart analyze` on the snippet.
- TS (rn/capacitor/web): temp dir, `npm install` the published package, `tsc --strict
  --noEmit` on the snippet.
- Plain JS (cordova): `node --check` for syntax, then verify every `Scandit.*` name is
  exported by the plugin (the cordova plugin re-exports the shared frameworks-barcode
  package, so tsc-checking the rn/capacitor snippet usually covers the signatures).

Order matters: compile the snippet BEFORE committing the skill change, not after.

## Honesty rules

- Never dismiss a low pass rate as "judge bugs" without proof — rebuild/re-run the
  harness first, then inspect transcripts.
- When porting an eval from a sibling platform, re-target prompt and API literals to
  the destination platform; do not copy assertions verbatim (API names and lifecycle
  hooks differ per platform).
- An eval file's layout must match its product family's existing `evals/*.json` split
  (integration / migration / third-party-migration / etc.). Add `tags:
  ["<taxonomy-feature-id>", ...]` to new evals.
