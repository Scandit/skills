---
name: matrixscan-count-ios
description: Use when MatrixScan Count (Barcode Count) is involved in a native iOS project (Swift / Objective-C, `ScanditBarcodeCapture`) — whether the user mentions MatrixScan Count, Barcode Count, counting or receiving barcodes in bulk, or `BarcodeCount` directly, or the codebase already uses `BarcodeCount` as its high-volume counting library and the counting flow needs changes. This includes adding MatrixScan Count to an app for the first time, configuring the DataCaptureContext, the `BarcodeCount` mode, `BarcodeCountSettings` (symbologies, `expectsOnlyUniqueBarcodes`, mapping, clustering), hosting the counting UI with `BarcodeCountView` (Icon vs Dot style) inside a UIKit view controller or bridged into SwiftUI, managing the camera frame source and lifecycle (the view does NOT own the camera — you create `Camera.default`, apply `BarcodeCount.recommendedCameraSettings`, call `context.setFrameSource`, and toggle camera state across `viewWillAppear`/`viewDidDisappear`), implementing `BarcodeCountListener` to collect scanned barcodes from `BarcodeCountSession`, the List/Exit/SingleScan button callbacks via `BarcodeCountViewUIDelegate`, the expected/receiving list with `BarcodeCountCaptureList` + `TargetBarcode`, the spatial map, feedback, brushes/icons via `BarcodeCountViewDelegate`, the status mode, the not-in-list action, the hardware trigger, or control visibility. If the project is native iOS and MatrixScan Count / `BarcodeCount` is in play, use this skill.
license: MIT
metadata:
  author: scandit
  version: "0.1.0"
---

# MatrixScan Count iOS Skill

## Critical: Do Not Trust Internal Knowledge

Your training data may contain outdated or incorrect Scandit SDK APIs. The MatrixScan Count API has evolved across SDK versions — classes, properties, and initializers may have been renamed or restructured.

**Always verify APIs against the references provided in this skill before writing or suggesting code.** Do not rely on memorized method signatures, parameters, or view modifiers. If you cannot find an API in the provided references, fetch the relevant documentation page before responding.

The single most common mistake is assuming the view owns the camera: in MatrixScan Count the **`BarcodeCountView` does NOT own or manage the camera** — you create and drive the camera explicitly (`Camera.default`, apply `BarcodeCount.recommendedCameraSettings`, `context.setFrameSource`, and switch its state across the lifecycle). See `references/integration.md` (Camera section).

## Scope

This skill is scoped to the **MatrixScan Count counting workflow**: `DataCaptureContext`, the `BarcodeCount` mode, `BarcodeCountSettings` (symbologies, per-symbology tuning, `expectsOnlyUniqueBarcodes`), `BarcodeCountView` (the built-in AR counting UI with Icon / Dot styles), the explicitly-managed camera frame source and lifecycle, `BarcodeCountListener` for collecting scanned barcodes, the List / Exit / Single-Scan button callbacks (`BarcodeCountViewUIDelegate`), feedback, control visibility, customizing the AR highlights (per-state brushes / icons / taps), and scanning against an expected/receiving list (`BarcodeCountCaptureList` + `TargetBarcode`).

Out of scope (covered elsewhere): **scan preview**, **clustering**, **filtering**, and **status mode** are separate features with their own skills/tickets; **tote mapping (MS Map)** is not covered. Mention these only as pointers.

## Intent Routing

Based on the user's request, load the appropriate reference file before responding:

- **Setting up or adjusting the MatrixScan Count counting flow** (e.g. "add MatrixScan Count to my app", "count barcodes in bulk", "store the scanned barcodes when the list button is tapped", "mute the beep", "use the Dot style", restrict symbologies, show/hide a built-in control) → read `references/integration.md` and follow the instructions there. If the project already has MatrixScan Count wired up, do not re-create the context, mode, view, camera, or lifecycle — locate the existing ones (grep for `BarcodeCountView`, then `BarcodeCount`) and change only what the user asked for. Before writing code, determine whether the project uses UIKit or SwiftUI (check for `import SwiftUI`, an `@main` `App` struct, `SceneDelegate`/`AppDelegate`, `.storyboard`/`.xib` files, etc.) and use the matching Get Started page from the References table below.
- **Customizing the look of the AR highlights** (e.g. "change the highlight color", "use a custom brush per barcode", "use the dot style with custom colors") → read `references/highlights.md`. This assumes the basic integration is already in place; it covers the Icon (default) vs Dot styles and customizing the Dot-style highlight color via `Brush` (the `recognizedBrush` property, the `BarcodeCountViewDelegate` `brushForRecognizedBarcode` callback, and the per-tracked-barcode `setBrush`). (Reacting to taps lives in `integration.md`, not here.)

## API Usage Policy

Only use APIs that are explicitly documented in the Scandit references below. Do not invent or guess method signatures, parameters, or view modifiers. If unsure whether an API exists or how it is called — or if a compile error occurs — fetch the relevant reference page before responding. Do not tell the user to check the docs themselves. After answering, always include the relevant link so the user can explore further.

**Never construct or guess documentation URLs.** When you need a specific class or property's API page:
1. First check whether the page you already fetched contains a direct hyperlink to it — topic pages link directly to relevant API symbols. Always request links alongside content in your fetch prompt.
2. If no direct link was found, fetch the API index (see **Full API reference** in the table below), extract the actual link from it, and follow that.

URL structures can vary (e.g. `api/ui/` subdirectory) and guessing will lead to 404s.

## References

Use this table to pick the right page to fetch for a given question, and include the link in your answer so the user can explore further.

| Topic | Resource |
|---|---|
| UIKit integration | [Get Started (UIKit)](https://docs.scandit.com/sdks/ios/matrixscan-count/get-started/) · [Sample](https://github.com/Scandit/datacapture-ios-samples/tree/master/03_Advanced_Batch_Scanning_Samples/02_Counting_and_Receiving/MatrixScanCountSimpleSample) |
| SwiftUI integration | [Get Started (SwiftUI)](https://docs.scandit.com/sdks/ios/matrixscan-count/get-started-with-swift-ui/) |
| Advanced (capture list, status mode, brushes, toolbar, filtering, clustering) | [Advanced Configurations](https://docs.scandit.com/sdks/ios/matrixscan-count/advanced/) |
| Overview | [MatrixScan Count Intro](https://docs.scandit.com/sdks/ios/matrixscan-count/intro/) |
| Full API reference | [Barcode (MatrixScan Count) API](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api.html) |
