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

## Fix-verification gate (HARD RULE — anti-hallucination)

**The auditor must never commit a fixture or reference code snippet that has not been
compiled against the resolved real Scandit SDK.** String/semantic evals validate API
*shape* in prose; they pass non-compiling code and wrong-language code (e.g. Java-style
Kotlin). They do not catch hallucinated APIs. This rule exists because that exact failure
shipped (Java-in-Kotlin fixtures in label-capture).

What the gate is FOR — and what it is NOT:

- **Goal: the API is not hallucinated.** Every Scandit symbol the code uses (class,
  method, property, enum case, import path, signature) must actually exist in the
  released SDK, and the file must compile. That is the whole bar.
- **NOT in scope: runtime behavior.** Whether it actually scans / detects / reads a
  document is QA's job (needs a device + license + camera) — do not claim the gate
  covers it.

The gate is only meaningful with the **real Scandit packages resolved on the
classpath**. A bare `kotlinc File.kt` / `swiftc File.swift` is a FALSE gate: it cannot
resolve `com.scandit.datacapture.*` at all, so it errors on every Scandit symbol
indiscriminately (can't tell a real API from a hallucinated one) or, with imports
stubbed, checks nothing. The fixture must be built inside a **deps-resolved project**
(the skill-creator "local sample app" approach).

Per-platform — who runs the gate:

| Platform(s) | Gate (deps-resolved) | Cheap enough for the auditor to run? |
|---|---|---|
| Flutter | scratch pub project + `flutter analyze` / `dart analyze` | yes |
| Web / RN / Capacitor (TS) | temp dir, `npm install` the published `@scandit/*` / `scandit-*` pkg, `tsc --strict --noEmit` | yes |
| Cordova (plain JS) | `node --check` for syntax + verify every `Scandit.*` name against the plugin's exports (it re-exports the shared frameworks pkg; the tsc check above usually covers signatures) | yes |
| .NET (net-android/net-ios/maui, C#) | scratch project + `dotnet restore` the Scandit NuGet + `dotnet build` | yes |
| Android (Kotlin) | gradle project w/ `com.scandit.datacapture:*` + Android SDK → `./gradlew compileDebugKotlin` | NO — heavy toolchain |
| iOS (Swift) | SPM/xcodebuild w/ the Scandit frameworks → `swift build` / `xcodebuild` | NO — heavy toolchain |
| KMP (Kotlin Multiplatform) | inject the file into the KMP SDK's `DebugApp` umbrella (already resolves every `scandit-kmp-datacapture-*` module + Compose MP) → `./gradlew :shared:compileDebugKotlinAndroid` | YES — incremental compile is seconds with a warm cache (needs the SDK checkout + `GITLAB_PRIVATE_TOKEN`) |

**Decision rule (Option C):**

1. If a cheap deps-resolved gate exists for the platform → the auditor MUST run it and the
   fixture/snippet must pass BEFORE the change is committed. Compile before commit, not after.
   (KMP is an exception among Kotlin targets: it has a cheap deps-resolved gate via the SDK's
   DebugApp umbrella — `scripts/fix_gate_kmp.sh` — so the auditor MUST run it, per rule 1.)
2. If the gate is heavy (plain-Android Kotlin, Swift) → the auditor does NOT bare-compile (toothless) and
   does NOT commit unverified code. It stays **audit-only** for that platform: it emits the
   proposed fixture/snippet to the report as UNVERIFIED and hands it to `skill-creator`,
   which builds the local sample app and compiles it. The auditor never self-commits
   Kotlin/Swift fixtures.
3. A cheaper anti-hallucination fallback (NOT a substitute for a build): cross-check every
   Scandit symbol used against the SDK's declared surface (`docs/source/**/*.rst`,
   `docs/api_availability/`). This catches hallucinated symbols/signatures but not all
   syntax — so it is "propose-only / mark not-build-verified," never an auto-commit path.

**Mechanical gate scripts** (`scripts/fix_gate_*.sh`) — run the right one on the file you
drafted; each resolves the real Scandit packages, compiles, and prints `GATE-PASS` /
`GATE-FAIL` / `GATE-SKIP` (skip = toolchain absent, exit 3 — don't pretend it passed):

    scripts/fix_gate_flutter.sh <dart-file> [version] [pub-pkg]
    scripts/fix_gate_ts.sh      <web|rn|capacitor> <ts-file> [version]
    scripts/fix_gate_swift.sh   <swift-file> [frameworks-csv]
    scripts/fix_gate_dotnet.sh  <cs-file> [version] [extra-pkg ...]   # covers net-android/net-ios/maui
    scripts/fix_gate_kmp.sh     <kotlin-file>   # KMP; needs SDK checkout + $GITLAB_PRIVATE_TOKEN

Notes: default version 8.4.0. `dotnet` builds a plain net8.0 project against the package's
net8.0 managed slice — no android/ios workloads needed (keep platform-UI-only types like
`Android.Views.*`/`UIKit.*` out of the gated snippet). Swift needs the xcframeworks resolved
once (an SPM sample build) or `$SCANDIT_XCFRAMEWORKS`. Toolchain overrides: `$FLUTTER`,
`$DOTNET`. These are the mechanical form of the rule above — proven to catch real bugs
(e.g. the `BarcodeFilterHighlightSettingsBrush` namespace error in matrixscan-count .NET).

## Honesty rules

- Never dismiss a low pass rate as "judge bugs" without proof — rebuild/re-run the
  harness first, then inspect transcripts.
- When porting an eval from a sibling platform, re-target prompt and API literals to
  the destination platform; do not copy assertions verbatim (API names and lifecycle
  hooks differ per platform).
- An eval file's layout must match its product family's existing `evals/*.json` split
  (integration / migration / third-party-migration / etc.). Add `tags:
  ["<taxonomy-feature-id>", ...]` to new evals.
