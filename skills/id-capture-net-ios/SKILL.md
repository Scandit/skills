---
name: id-capture-net-ios
description: Scandit ID Capture (`IdCapture`) in .NET for iOS projects (`net*-ios` target framework, `Scandit.DataCapture.IdCapture` NuGet, C#) — scanning passports, driver's licenses, ID cards, residence permits, visas via MRZ, VIZ, PDF417 barcode, or mobile documents. Use for integration, accepted-document and scanner configuration, CapturedId result handling, rejection rules, AAMVA verification, anonymization, overlay UI, and Scandit .NET SDK version migration — for MAUI apps (`<UseMaui>true</UseMaui>`) use id-capture-net-maui instead.
license: Apache-2.0
metadata:
  author: scandit
  version: "1.0.4"
---

# ID Capture .NET for iOS Skill

## Critical: Do Not Trust Internal Knowledge

Your training data may contain outdated or incorrect Scandit ID Capture APIs, and the **.NET binding differs substantially from the native iOS (Swift/Objective-C), Android (Kotlin/Java), and Flutter SDKs**. An agent that pattern-matches from the native docs will get most calls wrong: the .NET binding does **not** use the Swift/Kotlin builder, does **not** expose a `supportedDocuments` bitmask, and does **not** ship the standalone `AamvaBarcodeVerifier` / NFC classes that exist on native.

**Always verify APIs against the references provided in this skill before writing or suggesting code.** Do not rely on memorized method signatures, parameters, or shapes. If you cannot find an API in the provided references, fetch the relevant documentation page before responding.

The .NET-iOS-specific facts most often gotten wrong by pattern-matching from the Swift/Kotlin/Flutter SDK or the .NET Android binding:

- This skill targets the **non-MAUI** .NET for iOS workload (project `<TargetFramework>net10.0-ios</TargetFramework>` or similar, **no** `<UseMaui>` flag). For MAUI apps, the `DataCaptureView` is hosted as a XAML element and wired through handlers — completely different. If you see `<UseMaui>true</UseMaui>`, **stop and tell the user this skill does not apply.** The official iOS Get Started page mixes in MAUI (XAML / `*.Maui`) snippets — ignore those for a non-MAUI project.
- **Only TWO NuGet packages.** `Scandit.DataCapture.Core` and `Scandit.DataCapture.IdCapture`. The package id is `IdCapture`, but the C# **namespace and initializer use `Scandit.DataCapture.ID`** (`using Scandit.DataCapture.ID;`, `ScanditIdCapture.Initialize()`). There is **no** separate Barcode package to add — the PDF417/AAMVA barcode reader is bundled in `Scandit.DataCapture.IdCapture`. Do **not** add any `*.Maui` package.
- **SDK 8.0+ requires explicit initialization with TWO initializers** in `AppDelegate.FinishedLaunching` (`application:didFinishLaunchingWithOptions:`): `ScanditCaptureCore.Initialize()` **and `ScanditIdCapture.Initialize()`** before any Scandit type is constructed. Missing the ID one crashes the first `IdCapture.Create(...)` call.
- **`IdCaptureSettings` is configured with an object initializer / property sets — NOT a builder and NOT a bitmask.** You set `AcceptedDocuments` (an `IList<IIdCaptureDocument>`) and `Scanner` (an `IdCaptureScanner`). The Swift/Kotlin/old `supportedDocuments` + `IdDocumentType` bitmask **does not exist** in .NET.
- **Documents are constructed with `new`**, taking an `IdCaptureRegion`: `new Passport(IdCaptureRegion.Any)`, `new DriverLicense(IdCaptureRegion.Us)`, `new IdCard(IdCaptureRegion.Any)`, `new ResidencePermit(...)`, `new HealthInsuranceCard(...)`, `new VisaIcao(...)`, and `new RegionSpecific(RegionSpecificSubtype.X)`. `IdCaptureRegion` values are **C# PascalCase** (`Any`, `Us`, `EuAndSchengen`, …), not the Swift/Kotlin style.
- **The scanner is a wrapper:** `new IdCaptureScanner(physicalDocument: <IPhysicalDocumentScanner?>, mobileDocument: <MobileDocumentScanner?>)`. Physical = `new FullDocumentScanner()` (front+back, the default choice) or `new SingleSideScanner(barcode, machineReadableZone, visualInspectionZone)`. Mobile = `new MobileDocumentScanner(iso180135, ocr)`. Assign it to `settings.Scanner`.
- **`IdCapture` is created with a FACTORY, not `new`**: `IdCapture.Create(dataCaptureContext, settings)` (the constructor is private). There is also a `Create(settings)` overload.
- **You manage the camera yourself**, and `RecommendedCameraSettings` is applied to the camera (not passed to `GetDefaultCamera`): `Camera.GetDefaultCamera()`, then `camera.ApplySettingsAsync(IdCapture.RecommendedCameraSettings)`, then `dataCaptureContext.SetFrameSourceAsync(camera)`, then `camera.SwitchToDesiredStateAsync(FrameSourceState.On/Off)` across the `UIViewController` lifecycle. `RecommendedCameraSettings` is a **static property** on `IdCapture`. iOS additionally offers `FrameSourceState.Standby` (a lighter pause that keeps the camera warm) versus `.Off`.
- **`DataCaptureView.Create(DataCaptureContext, CGRect frame)` takes a `CGRect` as its second argument on iOS** — typically `this.View!.Bounds` (or `this.View?.Frame ?? CGRect.Empty`). This is the **opposite** of the .NET Android binding, where `DataCaptureView.Create(context)` takes only the context. The returned view **is** a `UIKit.UIView` (implicit conversion), so you add it yourself with `this.View.AddSubview(dataCaptureView)` and usually set `AutoresizingMask = FlexibleWidth | FlexibleHeight`. There is no `container.AddView(...)` (that's Android).
- **The view is a generic `DataCaptureView`; the overlay is `IdCaptureOverlay.Create(idCapture, dataCaptureView)`** (a two-arg factory that auto-attaches). Then optionally set `overlay.IdLayoutStyle = IdLayoutStyle.Square` (`IdLayoutStyle` lives in `Scandit.DataCapture.ID.UI.Overlay`).
- **Results come via `IIdCaptureListener` with TWO callbacks**: `OnIdCaptured(IdCapture, CapturedId)` **and `OnIdRejected(IdCapture, CapturedId?, RejectionReason)`**. Both run on a **background/arbitrary thread** — dispatch UI work to the main thread with **`DispatchQueue.MainQueue.DispatchAsync(...)`** or **`UIApplication.SharedApplication.InvokeOnMainThread(...)`** (**not** Android's `RunOnUiThread`), and set `idCapture.Enabled = false` while a result dialog is shown, re-enabling it afterwards. A standalone listener implementation derives from **`NSObject`** (a `UIViewController` already is one, so it can implement `IIdCaptureListener` directly).
- **Read field values via `CapturedId`**: top-level `FullName` / `FirstName` / `LastName` (`string?`), `DateOfBirth` / `DateOfExpiry` / `DateOfIssue` (a `DateResult?` with `Day`/`Month`/`Year` ints plus `UtcDate` / `LocalDate`), `DocumentNumber`, `Nationality`, `Sex` (raw string) / `SexType` (`Sex` enum), `Age`, `Address`, and the document via `Document?.DocumentType` (`IdCaptureDocumentType`). The richer sub-results are `capturedId.Mrz` / `capturedId.Viz` / `capturedId.Barcode` / `capturedId.MobileDocument` / `capturedId.MobileDocumentOcr` (note: properties are `Mrz`/`Viz`/`Barcode`, **not** `MrzResult`/`VizResult`/`BarcodeResult`), plus `capturedId.Images` and `capturedId.VerificationResult`.
- **Verification is settings-driven on .NET — there is NO `AamvaBarcodeVerifier` / `DataConsistencyVerifier` class.** Enable checks via `IdCaptureSettings` flags (`RejectForgedAamvaBarcodes`, `RejectInconsistentData`, `RejectNotRealIdCompliant`, …) and read the outcome from `capturedId.VerificationResult` (`DataConsistency` / `AamvaBarcodeVerification`). See [references/advanced.md](references/advanced.md).
- **NFC chip reading and the deserializer API are NOT in the .NET surface.** Do not reference `NfcScanner`, `NfcResult`, `CapturedId.Nfc`, or `IdCaptureDeserializer` — they don't exist on .NET iOS.
- **Document images are `UIImage?`** (`UIKit.UIImage`) on iOS — `capturedId.Images.Face`, `.Frame`, `.GetCroppedDocument(IdSide)`, `.GetFrame(IdSide)` and `DataConsistencyResult.FrontReviewImage` all return `UIImage?`, **not** Android's `Android.Graphics.Bitmap?`.
- **Camera permission is handled by iOS automatically** via the `NSCameraUsageDescription` key in `Info.plist`. The OS shows the permission prompt the first time the camera switches on. There is **no** runtime-permission helper class (that's the Android binding's `CameraPermissionActivity`). If `NSCameraUsageDescription` is missing, the app crashes when the camera starts.
- **iOS `SupportedOSPlatformVersion` must be ≥ `15.0`** in the `.csproj` (the Scandit iOS framework's minimum deployment target); the matching `MinimumOSVersion` goes in `Info.plist`.

### Forbidden APIs (commonly hallucinated — do NOT emit these)

These compile-fail against the real .NET packages. Use the right-hand form:

| Do NOT write | Use instead |
|---|---|
| `new IdCapture(...)` / `IdCapture.ForDataCaptureContext(...)` | `IdCapture.Create(context, settings)` |
| `IdCaptureSettings.builder()` / `settings.SupportedDocuments` / `IdDocumentType` bitmask | `new IdCaptureSettings { AcceptedDocuments = [ … ], Scanner = … }` |
| `settings.ScannerType = ...` | `settings.Scanner = new IdCaptureScanner(physicalDocument: …, mobileDocument: …)` |
| `IdCaptureOverlay.NewInstance(...)` | `IdCaptureOverlay.Create(idCapture, dataCaptureView)` |
| `DataCaptureView.Create(context)` (no frame) | `DataCaptureView.Create(context, this.View!.Bounds)` then `this.View.AddSubview(view)` |
| `RunOnUiThread(...)` (Android) | `DispatchQueue.MainQueue.DispatchAsync(...)` / `UIApplication.SharedApplication.InvokeOnMainThread(...)` |
| `capturedId.MrzResult` / `capturedId.VizResult` / `capturedId.BarcodeResult` | `capturedId.Mrz` / `capturedId.Viz` / `capturedId.Barcode` |
| `capturedId.IsPassport()` / `IsDriverLicense()` / `IsIdCard()` | `capturedId.Document?.DocumentType` (`IdCaptureDocumentType`) or `capturedId.IsRegionSpecific(subtype)` |
| `new AamvaBarcodeVerifier(...)` / `AamvaBarcodeVerifier.Create(...)` | `settings.RejectForgedAamvaBarcodes = true` + read `capturedId.VerificationResult.AamvaBarcodeVerification` |
| `new DataConsistencyVerifier(...)` | `settings.RejectInconsistentData = true` + read `capturedId.VerificationResult.DataConsistency` |
| `NfcScanner` / `NfcResult` / `capturedId.Nfc` | (not available on .NET iOS — no NFC API) |
| `capturedId.VisaDetails` / `PassportType` / `MobileDocumentDataElement` | (not available on .NET iOS) |
| reading `capturedId.Viz.DateOfBirth` / `.Nationality` / `.DocumentNumber` | those VIZ fields aren't on .NET — read them from the top-level `capturedId.DateOfBirth` / `.Nationality` / `.DocumentNumber` |
| `CameraPermissionActivity` / runtime permission request (Android) | declare `NSCameraUsageDescription` in `Info.plist`; iOS prompts automatically |

## Product Guidance

Apply these rules whenever the user is making a design decision, not just an API question.

- **Accept only the documents you actually need.** A narrow `AcceptedDocuments` list (e.g. just `new DriverLicense(IdCaptureRegion.Us)`) is faster and more accurate than `IdCaptureRegion.Any` across every document type. Ask the user which documents and regions they expect before defaulting to "everything".
- **Pick the scanner that matches the data you need.** `FullDocumentScanner()` reads front and back automatically (best for most ID/DL use cases). `SingleSideScanner(barcode, machineReadableZone, visualInspectionZone)` reads a single side from the zone(s) you enable — use it when you only need, say, the PDF417 barcode on the back of a US DL, or only the MRZ of a passport. `MobileDocumentScanner` is for mobile driver's licenses (mDL).
- **Handle `OnIdRejected`, not just `OnIdCaptured`.** Rejections (`RejectionReason.Timeout`, `NotAcceptedDocumentType`, `DocumentExpired`, `DocumentVoided`, `ForgedAamvaBarcode`, `InconsistentData`, …) are how the user learns why a scan didn't succeed. A production integration must surface a message for them.
- **Anonymize by default if you don't need every field.** `IdCaptureSettings.AnonymizationMode` and per-field anonymization keep regulated data (document images, sensitive fields) out of the result unless you opt in. Recommend the minimum that satisfies the use case.
- **Hand off to the `data-capture-sdk` skill for non-ID-Capture questions.** If the user asks about another Scandit product (Barcode Capture, SparkScan, MatrixScan, Label Capture, etc.) or about choosing between products, defer to the `data-capture-sdk` skill instead of guessing.

## Intent Routing

Based on the user's request, load the appropriate reference file before responding:

- **Integrating ID Capture from scratch, configuring accepted documents and the scanner, creating the mode, hosting the `DataCaptureView` + `IdCaptureOverlay`, wiring the camera lifecycle, handling captured/rejected IDs, and reading the common `CapturedId` fields** (e.g. "add passport / driver's license scanning to my .NET iOS app", "read the holder's name and date of birth in C#", "scan an ID card and show the document number") → read [references/integration.md](references/integration.md) and follow it.
- **Tuning the scanner (single-side / mobile docs), rejection rules (expired / voided / underage / expiring / forged-AAMVA / inconsistent), data-consistency & AAMVA verification, anonymization, reading the rich sub-results (MRZ / VIZ / PDF417 barcode / mobile document / images / driving-license details), or customizing the overlay** (e.g. "reject expired IDs", "only read the back barcode of a US license", "verify the AAMVA barcode and detect forgeries", "anonymize the document images", "read the full MRZ", "change the viewfinder style") → read [references/advanced.md](references/advanced.md) and follow it.
- **Upgrading the Scandit .NET SDK version on an existing ID Capture integration** (e.g. "migrate ID Capture from 6.x to 7", "update Scandit to the latest version", "we're on 7.x and the build breaks after bumping the packages", "move off the old `SupportedDocuments` API", code that still uses `SupportedDocuments` / `IdDocumentType` / `SupportedSides`, or an app that crashes at launch after an 8.x update) → read [references/migration.md](references/migration.md) and follow it. ID Capture launched on `dotnet.ios` at 6.16; the 6→7 step is a compile-breaking document/scanner redesign and the 7→8 step requires adding explicit SDK initialization.

## API Usage Policy

Only use APIs that are explicitly documented in the Scandit references below. Do not invent or guess method signatures, parameters, property names, or imports. If unsure whether an API exists or how it is called — or if a compile error occurs — fetch the relevant reference page before responding. Do not tell the user to check the docs themselves. After answering, always include the relevant link so the user can explore further.

**Never construct or guess documentation URLs.** When you need a specific class or property's API page:
1. First check whether the page you already fetched contains a direct hyperlink to it — topic pages link directly to relevant API symbols. Always request links alongside content in your fetch prompt.
2. If no direct link was found, fetch the API index (see **Full API reference** in the table below), extract the actual link from it, and follow that.

URL structures can vary (e.g. an `api/ui/` subdirectory) and guessing will lead to 404s.

## Licence key

Scanning needs a Scandit licence key. For this skill the licence product is `native` and the licence platform is `ios`.

Work through these in order — never block the user on MCP:

1. **The Scandit MCP server is connected** — call `ensure_scanner_setup` with product `native` and platforms `ios`, `app_identifier` (the app's bundle or application id; for web, its production domain, never `localhost`) and `env_var` `SCANDIT_LICENSE_KEY`. Do not run the command it returns. Then call `get_license_key` with the key's id, from that result or from `list_license_keys`; if `list_license_keys` shows the key is not a trial, ask the user before fetching it. Show at most a masked preview in chat; never print a full key.
2. **It is not connected** — tell the user once that they can connect the remote Scandit MCP server, `https://ssl.scandit.com/mcp`, in their MCP client, then continue from step 1. Do not edit MCP client configuration yourself.

   Authentication is browser-based, so it is **not supported headless or in CI**. The server provisions **trial** keys only; it never creates, revokes, or modifies production licences.
3. **The user declines, or has no MCP client** — they generate a key themselves at <https://ssl.scandit.com> (no account yet: <https://ssl.scandit.com/dashboard/sign-up?p=test>) and paste it in.

**Then put the key into the code**: write it into the licence-key call in place of the placeholder — the key `get_license_key` returned, or the one the user pastes or gives you — still showing only a masked preview in chat. Do not search the project, its files or the environment for a key.

## References

Direct users to the right resource based on their question:

| Topic | Resource |
|---|---|
| Get Started | [Get Started (.NET for iOS)](https://docs.scandit.com/sdks/net/ios/id-capture/get-started/) |
| Advanced topics (scanners, rejection, verification, anonymization, overlay) | [Advanced Configurations](https://docs.scandit.com/sdks/net/ios/id-capture/advanced/) |
| Migrating / upgrading the SDK version (6→7, 7→8) | [references/migration.md](references/migration.md) · [Migrate 6→7](https://docs.scandit.com/sdks/net/ios/migrate-6-to-7/) · [Migrate 7→8](https://docs.scandit.com/sdks/net/ios/migrate-7-to-8/) |
| Full API reference | [ID Capture API (.NET iOS)](https://docs.scandit.com/data-capture-sdk/dotnet.ios/id-capture/api.html) |

## API surface this skill covers

Read the "API surface this skill covers" section at the end of [references/integration.md](references/integration.md) before writing or reviewing code. It lists every class and member this skill covers, the APIs documented for other platforms that do not exist here, and the binding differences between platforms. Do not emit an API that is not in that section or in the official API reference.
