---
name: xamarin-to-net-migration
description: Migrate a Xamarin app and its Scandit Data Capture SDK integration onto the supported .NET stack — Xamarin.Android to .NET for Android, Xamarin.iOS to .NET for iOS, Xamarin.Forms to .NET MAUI. Use when a project references `Scandit.DataCapture.*.Xamarin` (or legacy `Scandit.BarcodePicker.Xamarin`) packages, targets MonoAndroid/Xamarin.iOS/Xamarin.Forms, or the user wants off Xamarin (end-of-support May 2024) onto net-android/net-ios/MAUI. Converts the project/platform layer, swaps NuGet packages, and hands off to the matching `*-net-*` / MAUI skill for the Scandit call sites.
license: MIT
metadata:
  author: scandit
  version: "1.0.0"
---

# Xamarin → .NET Migration Skill

Guides a Scandit customer from a Xamarin project (Android, iOS, or Forms) onto the supported .NET stack while keeping the Scandit Data Capture SDK working. Microsoft ended Xamarin support on **May 1, 2024**, and Scandit stopped shipping Xamarin SDK updates from v8.0 — staying on Xamarin means no more SDK updates, so migration is the only path to newer Scandit releases.

## The one thing to internalize first

**The Scandit call-site API barely changes; the project/platform layer is the whole migration.** The Scandit .NET binding for `net*-android` / `net*-ios` / MAUI uses the *same* PascalCase C# API as the Xamarin binding (`DataCaptureContext.ForLicenseKey(...)`, `BarcodeCapture.Create(context, settings)`, `IBarcodeCaptureListener`, symbology names, etc.). What actually moves is:

1. **NuGet packages** — drop the `.Xamarin` suffix (`Scandit.DataCapture.Core.Xamarin` → `Scandit.DataCapture.Core`), and for MAUI add the `*.Maui` companion packages.
2. **Project file** — legacy `.csproj` → SDK-style, correct Target Framework Moniker (`net8.0-android` / `net8.0-ios` / MAUI multi-target).
3. **Platform bootstrap** — `MainActivity`/`Application` (Android), `AppDelegate` (iOS), or `App.xaml`+`MauiProgram` (Forms→MAUI); manifest/`Info.plist`; assets/resources.
4. **SDK 8.0+ explicit init** — call `ScanditCaptureCore.Initialize()` (+ the per-product `Scandit*.Initialize()`) at startup, which Xamarin 6.x/7.x did not require.

So the bulk of the mechanical rewrite is .NET tooling, not Scandit code. Delegate the Scandit call-site verification to the matching implementation skill (see Handoff).

## Critical: Do Not Trust Internal Knowledge

Your training data may contain outdated or incorrect Scandit SDK APIs, wrong Xamarin/.NET package names, and stale project-file templates. It is especially likely to hallucinate a Scandit "Xamarin → .NET rename" that does not exist — the C# API is largely stable across the two bindings.

**Always verify APIs, package names, and versions against the references in this skill (and the per-product implementation skill you hand off to) before writing or suggesting code.** Do not rely on memorized method signatures, parameters, property names, package IDs, or version numbers. Never invent a NuGet version — fetch the latest stable from nuget.org. If you cannot find something in the provided references, fetch the relevant documentation page before responding.

Migration-specific gotchas worth flagging:

- **Never work destructively on the customer's source.** Confirm a git branch (or a backup copy) exists before editing. Record the starting commit so the migration is revertible.
- **The migration is resumable and idempotent.** Re-running on a partially migrated project must *continue*, not redo — always re-run detection first (see `references/detection.md`) and skip steps whose target state is already present.
- **Xamarin package IDs carry a `.Xamarin` suffix; .NET ones do not.** `Scandit.DataCapture.Core.Xamarin` → `Scandit.DataCapture.Core`. The legacy v5 `Scandit.BarcodePicker.Xamarin` (Barcode Picker API) has **no** modern equivalent — it maps to a Barcode Capture / SparkScan reintegration, not a package swap. Flag it as manual.
- **Do not guess the target TFM version.** `net8.0-*` is the current LTS baseline for Scandit's .NET SDK; confirm against the Scandit .NET docs and the customer's toolchain rather than assuming `net9.0`/`net10.0`.
- **Third-party packages, custom renderers, and platform effects are not auto-migratable.** Flag them for manual follow-up (custom renderers → MAUI handlers, `DependencyService` → DI) instead of silently breaking the build.
- **SDK 8.0+ requires explicit initialization** that Xamarin 6.x/7.x did not. Omitting `ScanditCaptureCore.Initialize()` compiles fine but crashes at the first Scandit call. The exact placement is per-platform — the implementation skill you hand off to has the template.

## Intent Routing

Based on the detected setup and the user's request, load the appropriate reference file before responding:

- **First contact / unknown setup** ("migrate my Xamarin app to .NET", "get me off Xamarin", "upgrade to MAUI") → always start with `references/detection.md` to classify the project, then follow the matching migration reference.
- **Xamarin.Android → .NET for Android** → read `references/migrate-android.md`.
- **Xamarin.iOS → .NET for iOS** → read `references/migrate-ios.md`.
- **Xamarin.Forms → .NET MAUI** → read `references/migrate-forms-maui.md`.
- **Which Scandit packages/APIs change, and which implementation skill to hand off to** → read `references/scandit-packages.md`.
- **Producing the final migration report** → read `references/report-template.md`.

## Migration workflow

Copy this checklist into the working session and track progress. It is the same five phases regardless of Xamarin flavour.

```
Migration progress:
- [ ] 1. Detect   — classify flavour, TFM, project style, Scandit packages + version
- [ ] 2. Plan     — produce a per-file migration plan; flag manual-only items
- [ ] 3. Migrate  — apply the mechanical project/platform changes
- [ ] 4. Map      — swap Scandit packages; verify call sites via the impl skill
- [ ] 5. Verify   — build per platform, smoke-check the SDK, write the report
```

**Phase 1 — Detect.** Follow `references/detection.md`. Output: Xamarin flavour (Android / iOS / Forms), current TFM, project style (legacy vs SDK-style `.csproj`), the Scandit packages + version referenced, and any third-party packages / custom renderers / platform effects. This phase is also the resume check — if detection shows a step already done, skip it.

**Phase 2 — Plan.** Synthesize detection into a per-file plan: which files convert mechanically, which need the customer's decision, and which are manual-only. Confirm a branch/backup exists (see the destructive-edit gotcha). Present the plan before large edits.

**Phase 3 — Migrate the project/platform layer.** Apply the matching `references/migrate-*.md`. This is the `.csproj` conversion, TFM, bootstrap files, manifest/`Info.plist`, and asset/resource handling.

**Phase 4 — Map the Scandit integration.** Follow `references/scandit-packages.md` to swap the Xamarin package IDs for the .NET (and, for MAUI, `*.Maui`) equivalents, aligned to a single version fetched from nuget.org. Then **hand off to the matching implementation skill** (see below) to verify/rewrite the Scandit call sites and add the SDK-8 initialization — do not re-derive the Scandit API here.

**Phase 5 — Verify and report.** Build the migrated project per target platform. Where a device/emulator is available, run a smoke check that the Scandit SDK initializes and scans. Then produce the migration report using `references/report-template.md`: what changed automatically, what needs manual follow-up, and how to validate.

## Handoff to the implementation skills

After the project/platform migration, the Scandit call sites are verified by the per-product .NET skill for the customer's product + target platform. Pick the skill that matches both:

| Target platform | Skill name pattern | Examples |
|---|---|---|
| .NET for Android (`net*-android`, non-MAUI) | `<product>-net-android` | `barcode-capture-net-android`, `id-capture-net-android` |
| .NET for iOS (`net*-ios`, non-MAUI) | `<product>-net-ios` | `barcode-capture-net-ios`, `id-capture-net-ios` |
| .NET MAUI | product's MAUI skill | `barcode-capture-maui`, `sparkscan-maui`, `id-capture-net-maui`, `label-capture-net-maui`, `matrixscan-count-maui` |

If you are unsure which Scandit **product** the customer uses (Barcode Capture, SparkScan, MatrixScan AR/Batch/Count, Smart Label Capture, ID Capture), hand off to the **`data-capture-sdk`** router skill — it identifies the product and names the correct implementation skill. Naming the specific skill is always better than telling the user "an implementation skill exists."

## API Usage Policy

Only use APIs, package IDs, and namespaces that are explicitly documented in this skill's references or in the implementation skill you hand off to. Do not invent or guess method signatures, parameters, property names, package names, or version numbers. If unsure whether an API exists or how it is called — or if a compile error occurs — fetch the relevant reference page before responding. Do not tell the user to check the docs themselves. After answering, always include the relevant link so the user can explore further.

**Never construct or guess documentation or NuGet URLs.** When you need a specific page:
1. First check whether a page you already fetched links to it — topic pages link directly to relevant API symbols and sibling docs. Always request links alongside content in your fetch prompt.
2. If no direct link was found, fetch the API/docs index (see **References** below), extract the actual link from it, and follow that.

URL structures vary between the Xamarin (versioned, e.g. `docs.scandit.com/7.6.x/sdks/xamarin/...`) and .NET (`docs.scandit.com/sdks/net/...`) doc trees, and guessing will lead to 404s.

## References

Direct users to the right resource based on their question:

| Topic | Resource |
|---|---|
| Microsoft's Xamarin → .NET upgrade guidance | [Upgrade from Xamarin to .NET](https://learn.microsoft.com/en-us/dotnet/maui/migration/) |
| .NET Upgrade Assistant | [Upgrade Assistant overview](https://learn.microsoft.com/en-us/dotnet/core/porting/upgrade-assistant-overview) |
| Xamarin.Forms → .NET MAUI upgrade | [Forms → MAUI migration](https://learn.microsoft.com/en-us/dotnet/maui/migration/forms-projects) |
| Scandit .NET SDK docs | [Scandit for .NET](https://docs.scandit.com/sdks/net/android/add-sdk/) |
| Scandit MAUI SDK docs | [Scandit for .NET MAUI](https://docs.scandit.com/sdks/net/maui/add-sdk/) |
| Legacy Scandit Xamarin docs (source side) | [Scandit for Xamarin (7.6.x)](https://docs.scandit.com/7.6.14/sdks/xamarin/ios/add-sdk/) |
| Scandit .NET NuGet packages | [nuget.org/profiles/Scandit](https://www.nuget.org/profiles/Scandit) |
