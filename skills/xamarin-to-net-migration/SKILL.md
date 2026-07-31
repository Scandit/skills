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

**The Scandit *method* API barely changes; the project/platform layer and the Scandit *namespaces* are the migration.** The Scandit .NET binding uses the *same* PascalCase C# method surface as the Xamarin binding (`DataCaptureContext.ForLicenseKey(...)`, `BarcodeCapture.Create(context, settings)`, `IBarcodeCaptureListener`, symbology names, etc.). What actually moves is:

1. **NuGet packages** — drop the `.Xamarin` / `.Xamarin.Forms` suffix (`Scandit.DataCapture.Core.Xamarin` → `Scandit.DataCapture.Core`), and for MAUI add the `*.Maui` companion packages.
2. **Scandit namespaces (Forms→MAUI only)** — the Forms binding's `.Unified` namespaces and `Scandit*Unified` assembly names **do** change. See "Scandit namespace rename" in `references/migrate-forms-maui.md`. This is the single highest-volume mechanical edit in a Forms migration; do not skip it on the strength of "the API barely changes".
3. **Project file** — legacy `.csproj` → SDK-style, correct Target Framework Moniker (`net*-android` / `net*-ios` / MAUI multi-target).
4. **Platform bootstrap** — `MainActivity`/`Application` (Android), `AppDelegate` (iOS), or `App.xaml`+`MauiProgram` (Forms→MAUI); manifest/`Info.plist`; assets/resources.
5. **SDK 8.0+ explicit init** — call `ScanditCaptureCore.Initialize()` (+ the per-product `Scandit*.Initialize()`) at startup, which Xamarin 6.x/7.x did not require. MAUI instead initializes via the `.UseScandit*()` builder chain.

So the bulk of the mechanical rewrite is .NET tooling and namespaces, not Scandit logic. Delegate the Scandit call-site verification to the matching implementation skill (see Handoff).

## Critical: Do Not Trust Internal Knowledge

Your training data may contain outdated or incorrect Scandit SDK APIs, wrong Xamarin/.NET package names, and stale project-file templates. It is especially likely to hallucinate a Scandit "Xamarin → .NET rename" that does not exist — the C# API is largely stable across the two bindings.

**Always verify APIs, package names, and versions against the references in this skill (and the per-product implementation skill you hand off to) before writing or suggesting code.** Do not rely on memorized method signatures, parameters, property names, package IDs, or version numbers. Never invent a NuGet version — fetch the latest stable from nuget.org. If you cannot find something in the provided references, fetch the relevant documentation page before responding.

Migration-specific gotchas worth flagging:

- **Never work destructively on the customer's source.** Confirm a git branch (or a backup copy) exists before editing. Record the starting commit so the migration is revertible.
- **NEVER delete, comment out, or stub a Scandit call site to make the build pass.** This is the single worst failure mode of this migration and it is easy to rationalize. Removing `<scandit:DataCaptureView>` from a page, commenting out the `.UseScandit*()` builder chain, replacing a scanning page with a placeholder `Label`/`Button`, or dropping an `IBarcodeCaptureListener` implementation produces an app that **compiles cleanly and no longer scans** — a silent, shipped regression far worse than a red build.
  - **Invariant:** every Scandit view, overlay, listener, settings object, and builder call present before the migration must still be present after it — **though not necessarily in the same file or language.** Verify this explicitly in Phase 5 by diffing Scandit symbols against the starting commit (see the Phase 5 integration-parity check).
  - **Relocation is allowed; deletion is not.** Some Forms XAML constructs legitimately move into code-behind because the MAUI binding has no XAML element for them — most notably `BarcodeCaptureOverlay`, which becomes a `HandlerChanged` + `AddOverlay` call (see `references/migrate-forms-maui.md`). Moving a construct from markup to C# satisfies the invariant. Removing it without recreating it does not.
  - If a Scandit construct will not compile, the cause is almost always a **wrong namespace/assembly name in your code, or a type that is not a XAML element at all** — not a missing API. Read the implementation skill's documented namespace, and check whether the type is a control or a runtime object, before concluding the API does not exist.
  - A build that only goes green because integration code was removed is a **FAILED migration**. Report it as blocked, with the compile error, and leave the original code in place — do not report success.
- **Do not conclude a Scandit API "does not exist" from a compile error.** Before making that claim, verify against the implementation skill's references, and if still unsure inspect the shipped assembly directly, e.g.
  `strings ~/.nuget/packages/scandit.datacapture.core.maui/<version>/lib/<tfm>/ScanditCaptureCoreMaui.dll | grep UseScandit`.
  `UseScanditCore`, `AddDataCaptureView` (in `ScanditCaptureCoreMaui`) and `UseScanditBarcode` (in `ScanditBarcodeCaptureMaui`) are all real and shipped — if they appear to be missing, your `using`/`xmlns` is wrong. They are **extension methods**, so `CS1061: 'MauiAppBuilder' has no method 'UseScanditCore'` means a missing `using`, not a missing API. The three required directives are:
  ```csharp
  using Scandit.DataCapture.Core;          // UseScanditCore
  using Scandit.DataCapture.Core.UI.Maui;  // AddDataCaptureView
  using Scandit.DataCapture.Barcode;       // UseScanditBarcode
  ```
  Commenting out the `.UseScandit*()` chain to get a green build is the **canonical instance** of the forbidden gutting above: the app then builds, launches, and fails at the first Scandit call because the SDK was never initialized.
- **The migration is resumable and idempotent.** Re-running on a partially migrated project must *continue*, not redo — always re-run detection first (see `references/detection.md`) and skip steps whose target state is already present.
- **Xamarin package IDs carry a `.Xamarin` *or* `.Xamarin.Forms` suffix; .NET ones do not.** `Scandit.DataCapture.Core.Xamarin` → `Scandit.DataCapture.Core`, and `Scandit.DataCapture.Core.Xamarin.Forms` → `Scandit.DataCapture.Core` **+** `Scandit.DataCapture.Core.Maui`. Strip the whole suffix — naively "dropping `.Xamarin`" from `Core.Xamarin.Forms` yields `Scandit.DataCapture.Core.Forms`, which **does not exist** and fails restore with `NU1101`. The legacy v5 `Scandit.BarcodePicker.Xamarin` (Barcode Picker API) has **no** modern equivalent — it maps to a Barcode Capture / SparkScan reintegration, not a package swap. Flag it as manual.
- **Do not guess the target TFM version — resolve it from the installed toolchain.** Run `dotnet workload list` and `dotnet --version` and target the newest TFM the customer actually has manifests for; a `net8.0-*` target on a machine with only the .NET 10 SDK fails to restore. `net8.0-*` is the conservative LTS floor, not a default to hardcode. Whatever you pick, use the *same* TFM in the build-verification commands you run and report.
- **`net10.0-android` needs an explicit kotlinx-serialization-json override.** Scandit's Android AAR chain pulls a transitive `Org.Jetbrains.Kotlinx.KotlinxSerializationJson` that only targets `net8.0-android`/`net9.0-android`. On `net10.0-android` the project builds **clean** and then crashes at the first scan with `Java.Lang.NoClassDefFoundError: Lkotlinx/serialization/json/JsonKt;`. If you target `net10.0-android`, add the override from `references/migrate-forms-maui.md` ("Android kotlinx-serialization override") — and note that a green build does **not** rule this out.
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

**Phase 5 — Verify and report.** In this order:

1. **Integration-parity check (do this *before* the build).** Confirm no Scandit integration was lost. Diff the Scandit symbol surface against the starting commit, e.g.

   ```bash
   git grep -IohE 'scandit[A-Za-z]*:[A-Za-z]+|UseScandit[A-Za-z]*|BarcodeCaptureOverlay|DataCaptureView|IBarcodeCaptureListener' <start-sha> -- . ':(exclude)**/obj/**' ':(exclude)**/bin/**' | sort -u > /tmp/before.txt
   git grep -IohE 'scandit[A-Za-z]*:[A-Za-z]+|UseScandit[A-Za-z]*|BarcodeCaptureOverlay|DataCaptureView|IBarcodeCaptureListener'              -- . ':(exclude)**/obj/**' ':(exclude)**/bin/**' | sort -u > /tmp/after.txt
   diff /tmp/before.txt /tmp/after.txt
   ```

   Anything present before and absent after must be either (a) a documented rename you applied deliberately, or (b) a **defect you fix now**. Also grep the diff for commented-out `UseScandit`/`scandit:` lines — a commented builder call is a lost integration, not a migration.
2. **Build** per target platform, using the TFM you resolved in Phase 1.
3. **Smoke check** on a device/emulator where available: the SDK initializes, the camera preview renders (a black/blank preview usually means `DataCaptureContext` is not bound on the view), and a scan reports a result. On `net10.0-android` a clean build does not imply a working scan — see the kotlinx gotcha.
4. **Report** using `references/report-template.md`: what changed automatically, what needs manual follow-up, and how to validate. If step 1 or 2 failed, the status is *Blocked* or *Partial* — never *Complete*.

## Handoff to the implementation skills

After the project/platform migration, the Scandit call sites are verified by the per-product .NET skill for the customer's product + target platform. Pick the skill that matches both:

| Target platform | Skill name pattern | Examples |
|---|---|---|
| .NET for Android (`net*-android`, non-MAUI) | `<product>-net-android` | `barcode-capture-net-android`, `id-capture-net-android` |
| .NET for iOS (`net*-ios`, non-MAUI) | `<product>-net-ios` | `barcode-capture-net-ios`, `id-capture-net-ios` |
| .NET MAUI | `<product>-net-maui` | `barcode-capture-net-maui`, `sparkscan-net-maui`, `id-capture-net-maui`, `label-capture-net-maui`, `matrixscan-count-net-maui` |

Every MAUI skill slug ends in **`-net-maui`** — there is no `barcode-capture-net-maui` / `sparkscan-net-maui` / `matrixscan-*-maui`. **Load the handoff skill before you write any MAUI Scandit code**, not after: it holds the exact XAML `xmlns`, assembly names, and builder-chain signature you need, and guessing them is the main cause of the "the API doesn't exist" false conclusion. If the skill you named fails to load, re-derive its slug from this table rather than proceeding without it.

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
