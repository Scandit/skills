# Scandit migration report

Every migration ends with a written report so the customer knows exactly what changed on the Scandit side, what still needs their hands, and how to validate. This report covers the **Scandit slice only** — the general app migration (owned by the .NET Upgrade Assistant) is explicitly out of scope. Produce it in Phase 5 and update it if the migration is resumed.

## Template

```markdown
# Scandit Xamarin → .NET Migration Report

## Summary
- **Project:** <name / path>
- **Target platform:** <.NET for Android | .NET for iOS | .NET MAUI> (TFM `<net*-...>`)
- **Scandit product:** <e.g. Barcode Capture>  ·  **SDK version:** <from> → <to>
- **Started from commit / backup:** <sha or backup location>
- **Status:** <Complete | Partial — N Scandit items remain | Blocked — see below>
- **Scandit integration parity:** <PASS — all pre-migration Scandit views/listeners/builder calls still present | FAIL — list what was lost>
- **Verified by:** <build only | build + on-device scan | not verified>

## Scandit changes applied
List each change, grouped by area:
- **Packages:** `Scandit.DataCapture.*.Xamarin(.Forms)` → `Scandit.DataCapture.*` (+ `*.Maui` for MAUI), pinned to `<version>`.
- **Initialization:** <SDK-8 `ScanditCaptureCore.Initialize()` + per-product `Initialize()` (Android/iOS) | `.UseScanditCore(...).UseScandit<Product>()` chain in `MauiProgram` (MAUI)>.
- **Namespaces (MAUI):** Scandit `.Unified` → plain in `.cs`; `<scandit:…>` `xmlns` → `...UI.Maui;assembly=ScanditCaptureCoreMaui`.
- **Views (MAUI):** <e.g. `BarcodeCaptureOverlay` relocated from XAML to code-behind (`HandlerChanged` + `AddOverlay`)>.
- **Runtime prerequisites:** <camera permission confirmed; SupportedOSPlatformVersion raised to Scandit's minimum (Android 24 / iOS 15)>.

## Scandit follow-up (still on the Scandit side, if any)
- [ ] <Legacy `Scandit.BarcodePicker.Xamarin`> → reintegrate on Barcode Capture/SparkScan via `<skill>`.
- [ ] <Any Scandit 6→7 / 7→8 call-site deltas> → apply via `<impl-skill>`'s migration guide.
- [ ] <Mode-specific call sites not yet verified> → hand off to `<product>-net-<platform>`.

## Out of scope — general app migration (NOT covered here)
Owned by the .NET Upgrade Assistant and the customer's team; listed only if it blocked the Scandit build:
- <Custom renderers, `DependencyService`/DI, platform effects, `MessagingCenter`, third-party packages with no .NET equivalent, general `Xamarin.Forms` → `Microsoft.Maui` cleanup.>
Run the .NET Upgrade Assistant for these — this skill did not touch them.

## How to validate
1. `dotnet restore` then `dotnet build -f <tfm>` for the target platform — expect a clean build.
2. Deploy to an emulator/simulator/device and confirm the app launches without the "SDK not initialized" crash.
3. Smoke-test scanning: point at a barcode/document and confirm a result is reported.
4. Diff against the starting commit; confirm no source outside the Scandit slice changed.

## Rollback
Revert to `<starting sha>` (or restore `<backup location>`) if anything regresses.
```

## Guidance

- **Be honest about partial migrations.** If Scandit items remain, set status to *Partial* and keep the checklist actionable — the migration is resumable and the next run reads this report.
- **Never claim a build/scan passed if it was not run.** State what was verified and what was not (e.g. "iOS build verified on simulator; on-device scan not tested — no device available").
- **A green build with a gutted integration is `Blocked`, never `Complete`.** If any Scandit view, overlay, listener, or `.UseScandit*()` call was deleted, commented out, or replaced with a placeholder to get the project compiling, the integration-parity line is **FAIL** and the status is **Blocked**. Say plainly which construct would not compile and what the compile error was, so the customer (or the next run) can fix the namespace rather than inheriting a silently non-scanning app. Do not describe a placeholder page as a migrated page.
- **Distinguish "compiles" from "scans".** Especially on `net10.0-android`, where the kotlinx-serialization gap produces a clean build and a first-scan crash. If no scan was performed, the *Verified by* line must say so.
- **Keep general-migration items in the out-of-scope section, not the Scandit sections.** This skill neither applied nor takes responsibility for them; only mention one if it actively blocked the Scandit build.
- **Link the implementation skill** used for the Scandit call sites so the customer can go deeper.
