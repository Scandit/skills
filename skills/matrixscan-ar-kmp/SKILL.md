---
name: matrixscan-ar-kmp
description: Use when MatrixScan AR (Barcode AR / BarcodeAr) is involved in a Kotlin Multiplatform (KMP) project — whether the user mentions MatrixScan AR, Barcode AR, BarcodeAr, or Scandit KMP directly, or the codebase already uses the `com.scandit.datacapture.kmp` packages (`com.kmp.datacapture.*`) as its multi-barcode scanning library and something needs to be added, changed, fixed, or configured. This includes adding BarcodeAr to a new KMP app (commonMain + Android/iOS hosts), modifying scan settings, handling tracked barcodes, customizing highlights or annotations, wiring up providers, using the Compose Multiplatform `BarcodeArView` composable, troubleshooting BarcodeAr behavior, or replacing a third-party barcode scanning library with BarcodeAr in a shared Kotlin module targeting Android and iOS. If the project is Kotlin Multiplatform and MatrixScan AR (BarcodeAr) is in play, use this skill.
license: MIT
metadata:
  author: scandit
  version: "1.0.0"
---

# MatrixScan AR KMP Skill

## Critical: Do Not Trust Internal Knowledge

Scandit's Kotlin Multiplatform (KMP) SDK is new, shipping in 8.6. Your training data almost
certainly predates it and contains **zero** reliable knowledge of its API — do not pattern-match
it against the Android or iOS native SDKs you may know. The KMP API packages are
`com.kmp.datacapture.*` (NOT `com.scandit.datacapture.*`), and shapes diverge from both native
SDKs in specific ways (see below).

**Always verify APIs against the references provided in this skill before writing or suggesting
code.** Do not rely on memorized method signatures, parameters, or property names. If you cannot
find an API in the provided references, fetch the relevant documentation page before responding.

KMP-specific gotchas worth flagging:

- **One flat package, not native's split.** Every BarcodeAr type — mode, settings, view, view
  settings, listener, session, all highlights, all annotations, all providers, the UI listener,
  feedback, the filter — lives in the single package `com.kmp.datacapture.barcode.ar`. Do not
  invent native Android's `ar.capture` / `ar.ui` / `ar.ui.highlight` / `ar.ui.annotations` /
  `ar.ui.annotations.info` sub-package split — KMP has no such split.
- **Factory, not constructor.** `BarcodeAr.forContext(dataCaptureContext, settings)` is a
  `companion object` factory function — not a public constructor, and not native Android's
  `BarcodeAr(context, settings)` direct-constructor pattern.
- **Settings are built via factories, not `X()`.** `BarcodeArSettings.barcodeArSettings()` and
  `BarcodeArViewSettings.barcodeArViewSettings()` are companion factory functions. Neither
  `BarcodeArSettings` nor `BarcodeArViewSettings` has a public no-arg constructor in KMP.
- **`BarcodeArView` is constructed platform-side, not in shared code.** `BarcodeArView` is an
  `expect class` whose constructor differs per platform: Android's takes `(context, barcodeAr,
  viewSettings)`, iOS's takes `(barcodeAr, viewSettings)` — no `Context` on iOS. Shared
  (`commonMain`) code cannot construct it directly; the Android host builds it with the Android
  context, the iOS host builds it without one, and both hand the resulting instance to shared
  code (e.g. a `registerView(view: BarcodeArView)` function) to wire providers and start
  scanning. Embed the underlying platform view with `view.toAndroidView()` (Android, returns
  `android.view.View`) or `view.toUIView()` (iOS, returns `UIView`).
- **KMP's `BarcodeArView` owns its own camera — always.** Unlike native Android (which threads
  a `Camera`/`CameraSettings` through the view constructor), the KMP view constructs and manages
  its camera internally on every platform, including Android. `BarcodeAr.recommendedCameraSettings()`
  exists for reference/documentation purposes only — there is no hook to actually apply custom
  `CameraSettings` to the view from shared code.
- **Lifecycle is `start()` / `pause()` / `stop()` / `reset()` — nothing else.** There is no
  separate `onResume()`/`onPause()`/`onDestroy()` split like native Android; the KMP view folds
  that into `start()` (begin/resume), `pause()` (temporarily suspend, resumable), and `stop()`
  (terminal teardown — the view is not usable afterwards). Call `reset()` to clear cached
  highlights/annotations and re-query the providers (e.g. after switching scanning modes).
- **Provider callbacks are plain Kotlin lambdas, not a `Callback` interface.**
  `BarcodeArHighlightProvider.highlightForBarcode(barcode, callback)` and
  `BarcodeArAnnotationProvider.annotationForBarcode(barcode, callback)` take
  `callback: (BarcodeArHighlight?) -> Unit` / `(BarcodeArAnnotation?) -> Unit` — invoke it as a
  function (`callback(highlight)`), not `callback.onData(highlight)` like native Android. Neither
  callback takes a `Context` parameter — KMP highlight/annotation constructors don't need one
  either (e.g. `BarcodeArRectangleHighlight(barcode)`, not `BarcodeArRectangleHighlight(context,
  barcode)`).
- **`BarcodeArViewUiListener.onHighlightForBarcodeTapped` has no `View` parameter** — it is
  `onHighlightForBarcodeTapped(barcodeAr, barcode, highlight)`, unlike native Android's 4-arg
  version that also passes the highlight's `View`.
- Symbology names use underscores, same as native Android: `Symbology.EAN13_UPCA`,
  `Symbology.CODE128` — not camelCase.
- All symbologies are disabled by default in `BarcodeArSettings`. Enabling only what the app
  needs improves tracking performance.
- Colors are built with `Color.fromRgba(r, g, b, a)` (from `com.kmp.datacapture.core.common`) —
  not a raw platform color int. Icons are built with `ScanditIcon.builder()...build()` (from
  `com.kmp.datacapture.core.ui`) — not a direct constructor.
- The license key placeholder is exactly `-- ENTER YOUR SCANDIT LICENSE KEY HERE --`.
- **`BarcodeArCustomAnnotation` and a `BarcodeArCustomHighlight` type are not documented as
  available on KMP.** Do not offer a custom-drawn-view highlight or annotation path on KMP;
  point the user at the built-in highlight/annotation types (rectangle/circle highlights,
  info/status-icon/popover/responsive annotations) and brush/icon customization instead.

## Intent Routing

Based on the user's request, load the appropriate reference file before responding:

- **Integrating BarcodeAr from scratch, or extending an existing integration** (e.g. "add
  MatrixScan AR to my KMP app", "set up barcode AR scanning in Kotlin Multiplatform", "how do I
  use BarcodeAr with Compose Multiplatform", "how do I show highlights on tracked barcodes", "how
  do I show info annotations", "how do I filter tracked barcodes") → read
  `references/integration.md` and follow the instructions there.

## API Usage Policy

Only use APIs that are explicitly documented in the Scandit references below. Do not invent or
guess method signatures, parameters, or property names. If unsure whether an API exists or how
it is called — or if a compile error occurs — fetch the relevant reference page before
responding. Do not tell the user to check the docs themselves. After answering, always include
the relevant link so the user can explore further.

**Never construct or guess documentation URLs.** When you need a specific class or property's
API page:
1. First check whether the page you already fetched contains a direct hyperlink to it — topic
   pages link directly to relevant API symbols. Always request links alongside content in your
   fetch prompt.
2. If no direct link was found, fetch the API index (see **Full API reference** in the table
   below), extract the actual link from it, and follow that.

URL structures can vary (e.g. `api/ui/` subdirectory) and guessing will lead to 404s.

## References

Direct users to the right resource based on their question:

| Topic | Resource |
|---|---|
| Get Started | [Intro](https://docs.scandit.com/sdks/kmp/matrixscan-ar/intro/) · [Get Started](https://docs.scandit.com/sdks/kmp/matrixscan-ar/get-started/) |
| Advanced topics (custom highlights, annotations, tap interactions, notifications, filter) | `references/integration.md` |
| Compose Multiplatform | [Core Concepts](https://docs.scandit.com/sdks/kmp/core-concepts/) |
| Core concepts (context, camera, views) | [Core Concepts](https://docs.scandit.com/sdks/kmp/core-concepts/) |
