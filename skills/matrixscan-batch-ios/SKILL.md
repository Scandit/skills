---
name: matrixscan-batch-ios
description: Use when MatrixScan Batch (BarcodeBatch / BarcodeTracking) is involved in an iOS project — whether the user mentions MatrixScan, MatrixScan Batch, BarcodeBatch, or BarcodeTracking directly, or the codebase already uses BarcodeBatch* classes and something needs to be added, changed, fixed, or extended. This includes adding MatrixScan Batch to a new iOS app, configuring BarcodeBatchSettings and symbologies, handling tracked barcodes via BarcodeBatchListener, customizing highlights via BarcodeBatchBasicOverlay, adding AR views via BarcodeBatchAdvancedOverlay, or managing the lifecycle. If the project is iOS and MatrixScan Batch (BarcodeBatch) is in play, use this skill.
license: MIT
metadata:
  author: scandit
  version: "1.0.0"
---

# MatrixScan Batch iOS Skill

## Critical: Do Not Trust Internal Knowledge

Your training data may contain outdated or incorrect Scandit SDK APIs. The BarcodeBatch API changes between major SDK versions — initializer signatures, overlay constructors, and delegate method names have all evolved (e.g. `BarcodeTracking` → `BarcodeBatch`).

**Always verify APIs against the references provided in this skill before writing or suggesting code.** Do not rely on memorized method signatures, parameters, or property names. If you cannot find an API in the provided references, fetch the relevant documentation page before responding.

iOS-specific gotchas worth flagging:

- `BarcodeBatch(context: context, settings: settings)` is a **direct convenience initializer** — not a factory method like Android's `BarcodeBatch.forDataCaptureContext(...)`. Passing a non-nil context auto-attaches the mode to the context.
- Camera setup is **manual**: get `Camera.default`, call `context.setFrameSource(camera, completionHandler: nil)`, then `camera?.apply(BarcodeBatch.recommendedCameraSettings, completionHandler: nil)`. Drive the camera from `viewWillAppear` / `viewWillDisappear`.
- `BarcodeBatchListener.barcodeBatch(_:didUpdate:frameData:)` is called on a **background queue** — not the main thread. Dispatch UI work via `DispatchQueue.main.async {}`.
- **Do not hold references** to `BarcodeBatchSession.trackedBarcodes`, `addedTrackedBarcodes`, `updatedTrackedBarcodes`, or `removedTrackedBarcodes` outside the callback — copy the data before the callback returns.
- `BarcodeBatchBasicOverlay(barcodeBatch:view:)` and `BarcodeBatchAdvancedOverlay(barcodeBatch:view:)` **auto-add the overlay** to the `DataCaptureView` — no separate `addOverlay` call needed.
- **`DataCaptureView` must be `addSubview`'d manually** — unlike `BarcodeArView`, `DataCaptureView` does not auto-attach to a parent view.
- **Per-barcode brush customization** (`barcodeBatchBasicOverlay(_:brushFor:)`, `setBrush(_:for:)`) requires the **MatrixScan AR add-on** license. A uniform default brush (no delegate) does not.
- **BarcodeBatchAdvancedOverlay** requires the **MatrixScan AR add-on** license.
- iOS symbology cases are **camelCase**: `.ean13UPCA`, `.code128`, `.qr` — not `EAN13_UPCA` / `CODE128` / `QR` like Android.
- iOS delegate methods use Swift naming: `barcodeBatchBasicOverlay(_:didTap:)` (not Android's `onTrackedBarcodeTapped`), `barcodeBatchAdvancedOverlay(_:viewFor:)` (not `viewForTrackedBarcode`).
- `BarcodeBatchAdvancedOverlayDelegate` uses `UIView` — not Android `View` or SwiftUI views.
- SwiftUI: `DataCaptureView` is a `UIView` and cannot be dropped into SwiftUI directly. Wrap a UIKit view controller in a `UIViewControllerRepresentable` and keep all BarcodeBatch APIs inside that view controller.
- Cleanup: `BarcodeBatchListener` is held as a **weak** reference, so a missed `removeListener` won't leak — but call `barcodeBatch.removeListener(self)` in `deinit` to make the lifecycle explicit. When using the shared singleton (`DataCaptureContext.shared`), modes stay attached for the app's lifetime — you don't need to call `removeCurrentMode()` or `dispose()`. Those methods do exist on `DataCaptureContext` if you want to tear down explicitly.
- `DataCaptureContext` exposes two valid initializers: `DataCaptureContext.initialize(licenseKey:)` + `.shared` (added 7.1.0/7.6.0 — the modern singleton pattern, and what this skill uses) and the older `DataCaptureContext(licenseKey:)` convenience init (still non-deprecated, and what the UIKit Get Started page on docs.scandit.com still shows). Prefer the singleton form.

## Intent Routing

Based on the user's request, load the appropriate reference file before responding:

- **Integrating MatrixScan Batch from scratch, configuring settings, handling tracked barcodes, customizing overlays, or managing lifecycle** → read `references/integration.md` and follow the instructions there. Before writing code, determine whether the project uses UIKit or SwiftUI (check for `import SwiftUI`, an `@main` `App` struct, `SceneDelegate`/`AppDelegate`, `.storyboard`/`.xib` files, etc.) and use the matching Get Started page from the References table below. If the project already has BarcodeBatch wired up, do not re-create the context, mode, view, or lifecycle — locate the existing ones (grep for `BarcodeBatch`, then `DataCaptureView`) and change only what the user asked for.

## API Usage Policy

Only use APIs that are explicitly documented in the Scandit references below. Do not invent or guess method signatures, parameters, or property names. If unsure whether an API exists or how it is called — or if a compile error occurs — fetch the relevant reference page before responding. Do not tell the user to check the docs themselves. After answering, always include the relevant link so the user can explore further.

**Never construct or guess documentation URLs.** When you need a specific class or property's API page:
1. First check whether the page you already fetched contains a direct hyperlink to it — topic pages link directly to relevant API symbols. Always request links alongside content in your fetch prompt.
2. If no direct link was found, fetch the API index (see **Full API reference** in the table below), extract the actual link from it, and follow that.

URL structures can vary (e.g. `api/ui/` subdirectory) and guessing will lead to 404s.

## References

| Topic | Resource |
|---|---|
| UIKit integration | [Get Started (UIKit)](https://docs.scandit.com/sdks/ios/matrixscan/get-started/) · [Sample](https://github.com/Scandit/datacapture-ios-samples/tree/master/03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanBubblesSample) |
| SwiftUI integration | [Get Started (SwiftUI)](https://docs.scandit.com/sdks/ios/matrixscan/get-started-with-swift-ui/) |
| AR overlays (BasicOverlay brushes, AdvancedOverlay views) | [Adding AR Overlays](https://docs.scandit.com/sdks/ios/matrixscan/advanced/) |
| Full API reference | [BarcodeBatch API](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api.html) |
