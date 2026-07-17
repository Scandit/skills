# Migration report

Every migration ends with a written report so the customer knows exactly what changed automatically, what still needs their hands, and how to validate. Produce it in Phase 5 and update it if the migration is resumed.

## Template

```markdown
# Xamarin → .NET Migration Report

## Summary
- **Project:** <name / path>
- **Path:** Xamarin.<Android|iOS|Forms> → <.NET for Android | .NET for iOS | .NET MAUI>
- **Scandit product:** <e.g. Barcode Capture>  ·  **SDK version:** <from> → <to>
- **Started from commit / backup:** <sha or backup location>
- **Status:** <Complete | Partial — N manual items remain>

## Changed automatically
List each mechanical change applied, grouped by area:
- **Project file:** legacy .csproj → SDK-style; TFM set to `net8.0-<...>`; SupportedOSPlatformVersion `<v>`.
- **Packages:** `Scandit.DataCapture.*.Xamarin` → `Scandit.DataCapture.*` (+ `*.Maui`), pinned to `<version>`.
- **Bootstrap:** <MainApplication/AppDelegate/MauiProgram changes; SDK 8 init added>.
- **Manifest / Info.plist / resources:** <what moved>.
- **Namespaces (Forms→MAUI):** `Xamarin.Forms` → `Microsoft.Maui`, XAML xmlns updated.

## Needs manual follow-up
One row per item that was flagged, not auto-migrated:
- [ ] <Custom renderer `BadgeView`> → migrate to a MAUI handler.
- [ ] <`DependencyService` `IAudioService`> → register in `MauiProgram` DI.
- [ ] <Third-party package `X` has no .NET equivalent> → find a replacement or remove.
- [ ] <Legacy `Scandit.BarcodePicker.Xamarin`> → reintegrate on Barcode Capture/SparkScan via `<skill>`.
- [ ] <Any Scandit 6→7 / 7→8 call-site deltas> → apply via `<impl-skill>`'s migration guide.

## How to validate
1. `dotnet restore` then `dotnet build -f <tfm>` for each target platform — expect a clean build.
2. Deploy to an emulator/simulator/device and confirm the app launches without the "SDK not initialized" crash.
3. Smoke-test scanning: point at a barcode/document and confirm a result is reported.
4. Diff against the starting commit; confirm no source outside the migration scope changed.

## Rollback
Revert to `<starting sha>` (or restore `<backup location>`) if anything regresses.
```

## Guidance

- **Be honest about partial migrations.** If manual items remain, set status to *Partial* and keep the checklist actionable — the migration is resumable and the next run reads this report.
- **Never claim a build/scan passed if it was not run.** State what was verified and what was not (e.g. "iOS build verified on simulator; on-device scan not tested — no device available").
- **Link the implementation skill** used for the Scandit call sites so the customer can go deeper.
