---
name: sparkscan-kmp
description: Use when SparkScan is involved in a Kotlin Multiplatform (KMP) project — whether the user mentions SparkScan, Kotlin Multiplatform, KMP, or Compose Multiplatform directly, or the codebase already uses Scandit's KMP SDK (`com.kmp.datacapture.*`) as its barcode scanning library and something needs to be added, changed, fixed, or configured. This includes adding SparkScan to a new KMP app (shared ScreenModel + Android/iOS hosts), modifying scan settings, handling scan results, customizing feedback or the SparkScan UI, embedding `SparkScanView` via `toAndroidView()`/`toUIView()`, using the Compose Multiplatform `SparkScanView` composable, or troubleshooting SparkScan behavior in a shared Kotlin codebase. If the project is Kotlin Multiplatform (or Compose Multiplatform) and SparkScan is in play, use this skill.
license: MIT
metadata:
  author: scandit
  version: "1.0.0"
---

# SparkScan KMP Skill

## Critical: Do Not Trust Internal Knowledge

Scandit's Kotlin Multiplatform (KMP) SDK is new, shipping in 8.6. Your training data almost
certainly predates it and contains **zero** reliable knowledge of its API — do not pattern-match
it against the Android-native or iOS-native SparkScan SDKs you may know. The KMP API packages are
`com.kmp.datacapture.*` (the `com.scandit.datacapture.kmp` name is only the **Maven group id**,
never a Kotlin import), and shapes diverge from both native SDKs in specific ways (see below).

**Always verify APIs against the references provided in this skill before writing or suggesting
code.** Do not rely on memorized method signatures, parameters, or property names from any other
Scandit platform. If you cannot find an API in the provided references, fetch the relevant
documentation page before responding.

KMP-specific gotchas worth flagging:

- Import root is `com.kmp.datacapture.*` — e.g. `com.kmp.datacapture.barcode.spark.SparkScan`,
  `com.kmp.datacapture.core.capture.DataCaptureContext`. Never write `com.scandit.datacapture.*`
  in KMP code.
- **`SparkScan(settings)` is a plain constructor** — unlike other KMP modes (e.g.
  `BarcodeCapture.forContext(...)`, `BarcodeAr.forContext(...)`), SparkScan has no
  `forContext`/factory function. `SparkScan` binds to the shared `DataCaptureContext` implicitly
  the same way native SDKs do.
- `SparkScanSettings` and `SparkScanViewSettings` have **no public constructor** — use the
  factories `SparkScanSettings.sparkScanSettings()` (or the `capturePresets` overload) and
  `SparkScanViewSettings.sparkScanViewSettings()`. Writing `SparkScanSettings()` is a compile
  error.
- `SparkScanView` is **platform-divergent by construction signature**: Android's constructor is
  `SparkScanView(context: android.content.Context, dataCaptureContext: DataCaptureContext, sparkScan: SparkScan, settings: SparkScanViewSettings)`;
  iOS's is `SparkScanView(dataCaptureContext: DataCaptureContext, sparkScan: SparkScan, settings: SparkScanViewSettings)` —
  **no `Context` parameter on iOS**. Shared `commonMain` code cannot construct a `SparkScanView`
  directly; each platform host constructs it and hands it to shared code (e.g. the screen model)
  to wire the feedback delegate and lifecycle.
- To embed the native view: Android uses `view.toAndroidView(): View` (import
  `com.kmp.datacapture.barcode.ui.toAndroidView`) inside a Compose `AndroidView` factory or a
  plain `ViewGroup`; iOS uses `view.toUIView(): UIView` inside a `UIViewRepresentable`. These are
  the *only* supported bridges — never call `toNative()` from application code (it's public only
  because Kotlin's `internal` cannot span the multi-module KMP SDK).
- `SparkScanListener` has exactly two methods to implement:
  `onBarcodeScanned(sparkScan, session, frameData)` and
  `onSessionUpdated(sparkScan, session, frameData)` — both required (no default bodies), and
  `frameData: FrameData` is **non-null** on KMP (Android-native's `data: FrameData?` is nullable).
  Read the scanned barcode from `session.newlyRecognizedBarcode`.
- `SparkScanFeedbackDelegate.getFeedbackForBarcode(barcode)` returns `SparkScanBarcodeFeedback?`.
  Build success/error feedback with `SparkScanBarcodeSuccessFeedback(...)` /
  `SparkScanBarcodeErrorFeedback(errorMessage, resumeCapturingDelay, ...)` — the error
  constructor's message parameter is named **`errorMessage`** (not `message`), and
  `resumeCapturingDelay` is a plain **`Long` in milliseconds** (not `TimeInterval` like
  Android-native, not a `.NET TimeSpan`). `feedbackDelegate` is a property on the platform
  `SparkScanView` instance, not on `SparkScanSettings`.
- **There is no `SparkScanScanningMode.Target` on KMP.** Native Android's combined
  "Target scanning mode" class is not bound. Instead, `SparkScanViewSettings` exposes two
  independent properties: `scanningBehavior: SparkScanScanningBehavior` (`SINGLE` / `CONTINUOUS`)
  and `previewBehavior: SparkScanPreviewBehavior` (`DEFAULT` / `PERSISTENT`). Correspondingly,
  `SparkScanViewUiListener` has no `onScanningModeChange` callback — don't invent one.
- UI-chrome toggles (`triggerButtonVisible`, `torchControlVisible`, `toolbarBackgroundColor`,
  `triggerButtonCollapsedColor`, etc.) are `var` properties on the constructed **`SparkScanView`
  instance itself**, not on `SparkScanViewSettings` — `SparkScanViewSettings` only configures
  construction-time behavior (zoom, timeouts, sound/haptic, hardware trigger, toast, mini-preview
  size, camera position, periscope mode, scanning/preview behavior). The Compose Multiplatform
  `SparkScanView` composable exposes the view-level toggles directly as parameters since it owns
  view construction.
- Reactive alternative to implementing `SparkScanListener`: `sparkScan.recognizedBarcodes: Flow<Barcode>`
  and `sparkScan.sessionUpdates: Flow<SparkScanSession>` (from the same `com.kmp.datacapture.barcode.spark`
  package). Collecting either Flow registers a listener; cancelling the collection removes it.
  Each collector gets an independent listener — share a single upstream listener with
  `.shareIn(scope, SharingStarted.WhileSubscribed())` if multiple coroutines need the same stream.
- Compose Multiplatform: `@Composable fun SparkScanView(...)` (from the `barcode-compose` module)
  starts scanning as the final step on entering composition and stops it on dispose — **do not
  add manual `onResume()`/`onPause()`/`startScanning()`/`stopScanning()` calls** when using this
  composable; it manages the whole lifecycle. Use `rememberSparkScan(context, settings)` to build
  the mode (defaults `context` to `DataCaptureContext.sharedInstance`).
- Teardown when NOT using the Compose composable (i.e. the manual `SparkScanView` pattern):
  `sparkScan.removeListener(this)` then `dataCaptureContext.removeMode(sparkScan)` — in that
  order, on screen/model disposal. This matches the canonical sample's `dispose()` exactly; there
  is no separate `onDestroy()`.
- The license key placeholder is exactly `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` (matches the
  canonical sample). Use this exact string, not a different placeholder.
- On iOS, distribution is via Swift Package Manager (`Scandit/datacapture-kmp-spm`, an umbrella
  XCFramework) — an app links exactly **one** Kotlin framework product from that package; pick the
  variant that bundles the barcode module (needed for SparkScan). The native Scandit XCFrameworks
  (core, barcode) resolve transitively — do not add them as separate SPM dependencies.
- Request the `CAMERA` permission at runtime on Android before starting scanning (the manifest
  declaration alone is not sufficient). On iOS, `NSCameraUsageDescription` in `Info.plist`
  triggers the OS permission prompt automatically on first camera use.

## Intent Routing

Based on the user's request, load the appropriate reference file before responding:

- **Integrating SparkScan from scratch, configuring symbologies, customizing feedback, handling
  scan results, wiring the Compose Multiplatform view, customizing the SparkScan UI, or tearing
  down the integration** (e.g. "add SparkScan to my KMP app", "set up barcode scanning in my
  shared module", "how do I use SparkScan with Compose Multiplatform", "reject a barcode and show
  an error", "enable continuous scanning", "hide the trigger button") → read
  `references/integration.md` and follow the instructions there.

## API Usage Policy

Only use APIs that are explicitly documented in the Scandit references below. Do not invent or
guess method signatures, parameters, or property names — and never carry over a signature from
the Android-native or iOS-native SDKs without verifying it also holds for KMP. If unsure whether
an API exists or how it is called — or if a compile error occurs — fetch the relevant reference
page before responding. Do not tell the user to check the docs themselves. After answering,
always include the relevant link so the user can explore further.

**Never construct or guess documentation URLs.** When you need a specific class or property's API
page:
1. First check whether the page you already fetched (e.g. the Advanced Configurations page)
   contains a direct hyperlink to it — topic pages link directly to relevant API symbols. Always
   request links alongside content in your fetch prompt.
2. If no direct link was found, fetch the API index (see **Full API reference** in the table
   below), extract the actual link from it, and follow that.

URL structures can vary (e.g. `api/ui/` subdirectory) and guessing will lead to 404s.

## References

Direct users to the right resource based on their question:

| Topic | Resource |
|---|---|
| Get Started | [Intro](https://docs.scandit.com/sdks/kmp/sparkscan/intro/) · [Get Started](https://docs.scandit.com/sdks/kmp/sparkscan/get-started/) |
| Advanced topics (custom feedback, scanning behavior, UI customization) | `references/integration.md` |
| Compose Multiplatform | [Core Concepts](https://docs.scandit.com/sdks/kmp/core-concepts/) |
| Core concepts (context, camera, views) | [Core Concepts](https://docs.scandit.com/sdks/kmp/core-concepts/) |
