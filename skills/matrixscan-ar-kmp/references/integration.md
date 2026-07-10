# BarcodeAr (MatrixScan AR) Kotlin Multiplatform Integration Guide

BarcodeAr is the multi-barcode AR scanning mode. It simultaneously tracks all barcodes in the
camera feed and overlays interactive highlights and annotations on each one in real time. On
Scandit's Kotlin Multiplatform (KMP) SDK the shared (`commonMain`) module owns all SDK wiring —
the mode, its settings, the highlight/annotation providers, and the UI tap listener — while each
platform host (Android, iOS) constructs the platform-native `BarcodeArView` and hands it to shared
code to drive.

Examples below are Kotlin, written for `commonMain` unless a file is explicitly marked
`androidMain` or `iosMain`/Swift. Every BarcodeAr type lives in the single package
`com.kmp.datacapture.barcode.ar` — there is no native-Android-style split into `ar.capture` /
`ar.ui` / `ar.ui.highlight` / `ar.ui.annotations` sub-packages.

## Prerequisites

- Scandit KMP SDK — add the shared-module dependencies to the `commonMain` source set of your
  `shared` module's `build.gradle.kts`:
  ```kotlin
  kotlin {
      sourceSets {
          commonMain.dependencies {
              api("com.scandit.datacapture.kmp:core:8.6.0")
              api("com.scandit.datacapture.kmp:barcode:8.6.0")
              // Only if you use the Compose Multiplatform BarcodeArView composable:
              implementation("com.scandit.datacapture.kmp:barcode-compose:8.6.0")
          }
      }
  }
  ```
  Before writing the dependency, confirm the latest published version — fetch
  `https://central.sonatype.com/artifact/com.scandit.datacapture.kmp/barcode` and extract the
  latest version number from the page rather than assuming `8.6.0` is still current.
- iOS side: add the umbrella XCFramework via Swift Package Manager — `File > Add Package
  Dependencies` with the package URL `Scandit/datacapture-kmp-spm`. This is **one** Kotlin
  framework per app (it re-exports the shared module's Kotlin/Native binary plus the native
  `ScanditCaptureCore`/`ScanditBarcodeCapture` xcframeworks it depends on) — do not add separate
  per-module SPM packages.
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- Camera permission:
  - Android: add to `AndroidManifest.xml`
    ```xml
    <uses-feature
        android:name="android.hardware.camera"
        android:required="true" />
    <uses-permission android:name="android.permission.CAMERA" />
    ```
    and request the `CAMERA` permission at runtime using the standard Android permission API
    before scanning starts.
  - iOS: add `NSCameraUsageDescription` to `Info.plist` — the OS shows the permission prompt
    automatically on first camera use.

## Minimal Integration

Ask the user which barcode symbologies they need to scan. When asking, mention that enabling
only what the app actually needs improves tracking performance.

Once the user responds, ask where they'd like BarcodeAr wired up: a shared `commonMain` class
(e.g. a screen model / view model) is the pattern used by Scandit's own KMP sample, with the
Android and iOS hosts only embedding the platform view. Write the integration code directly into
the project's files — do not just show it in chat.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `com.scandit.datacapture.kmp:core` and `com.scandit.datacapture.kmp:barcode` to the shared
   module's `commonMain` dependencies (the version was already fetched and filled in above).
2. Add the `Scandit/datacapture-kmp-spm` Swift Package to the iOS app target.
3. Add `<uses-permission android:name="android.permission.CAMERA" />` and the `<uses-feature>`
   element to `AndroidManifest.xml`; add `NSCameraUsageDescription` to `Info.plist`.
4. Request the `CAMERA` permission at runtime on Android before scanning starts.
5. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com.

### Step 1 — Create the DataCaptureContext

```kotlin
import com.kmp.datacapture.core.capture.DataCaptureContext

val dataCaptureContext: DataCaptureContext =
    DataCaptureContext.initialize("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
```

### Step 2 — Configure BarcodeArSettings

All symbologies are disabled by default. `BarcodeArSettings` has no public constructor — build it
via the companion factory.

```kotlin
import com.kmp.datacapture.barcode.ar.BarcodeArSettings
import com.kmp.datacapture.barcode.data.Symbology

val settings: BarcodeArSettings = BarcodeArSettings.barcodeArSettings().apply {
    enableSymbology(Symbology.EAN13_UPCA, true)
    enableSymbology(Symbology.CODE128, true)
    enableSymbology(Symbology.QR, true)
}
```

You can also enable a set at once: `settings.enableSymbologies(setOf(Symbology.EAN13_UPCA, Symbology.CODE128))`.

#### BarcodeArSettings Members

| Member | Description |
|--------|-------------|
| `BarcodeArSettings.barcodeArSettings()` | Companion factory — creates settings with all symbologies disabled. |
| `enabledSymbologies` | The set of currently enabled symbologies. |
| `enableSymbology(symbology, enabled)` | Enable or disable one symbology. |
| `enableSymbologies(symbologies)` | Enable a `Set<Symbology>` in one call. |
| `getSymbologySettings(symbology)` | Get per-symbology `SymbologySettings` (e.g. `activeSymbolCounts`). |
| `expectsOnlyUniqueBarcodes` | Whether only unique barcodes are reported. |
| `setProperty(name, value)` / `getProperty(name)` | Advanced property tuning by name. |

### Step 3 — Create BarcodeAr

`BarcodeAr` is constructed via the `forContext` companion factory — not a public constructor and
not `forDataCaptureContext`.

```kotlin
import com.kmp.datacapture.barcode.ar.BarcodeAr

val barcodeAr: BarcodeAr = BarcodeAr.forContext(dataCaptureContext, settings)
```

To apply updated settings at runtime: `barcodeAr.applySettings(newSettings)`.

#### BarcodeAr Members

| Member | Description |
|--------|-------------|
| `BarcodeAr.forContext(dataCaptureContext, settings)` | Companion factory — creates the mode and attaches it to the context. |
| `BarcodeAr.recommendedCameraSettings()` | Companion — returns recommended `CameraSettings`. Reference-only on KMP: see the [Pitfalls](#pitfalls) note. |
| `dataCaptureContext` | The `DataCaptureContext?` this instance is attached to. |
| `addListener(listener)` / `removeListener(listener)` | Register or remove a `BarcodeArListener`. |
| `applySettings(settings)` | Update settings at runtime. |
| `feedback` | `BarcodeArFeedback` — sound / vibration on barcode events. |
| `setBarcodeFilter(filter)` | Restrict which barcodes appear in the session (pass `null` to show all). |

### Step 4 — Build BarcodeArViewSettings

`BarcodeArViewSettings` is also built via a companion factory — controls sound, haptics, and the
default camera direction.

```kotlin
import com.kmp.datacapture.barcode.ar.BarcodeArViewSettings
import com.kmp.datacapture.core.source.CameraPosition

val viewSettings: BarcodeArViewSettings = BarcodeArViewSettings.barcodeArViewSettings().apply {
    hapticEnabled = true
    soundEnabled = true
    defaultCameraPosition = CameraPosition.WORLD_FACING
}
```

#### BarcodeArViewSettings Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `soundEnabled` | `Boolean` | `true` | Whether a beep plays on each tracked barcode. |
| `hapticEnabled` | `Boolean` | `true` | Whether haptics fire on each tracked barcode. |
| `defaultCameraPosition` | `CameraPosition` | `WORLD_FACING` | Camera to open on start. |

### Step 5 — Construct BarcodeArView per platform and register it

`BarcodeArView` is an `expect class` — its constructor is **platform-divergent**: Android's takes
a `Context`, iOS's does not. Shared `commonMain` code cannot construct it directly. The pattern
used by Scandit's own KMP sample is a shared function that takes an already-constructed view,
wires the providers/listener, and starts scanning:

```kotlin
// commonMain
import com.kmp.datacapture.barcode.ar.BarcodeArView

fun registerView(view: BarcodeArView): BarcodeArView {
    view.highlightProvider = MyHighlightProvider()
    view.annotationProvider = MyAnnotationProvider()
    view.uiListener = MyUiListener()
    view.start()
    return view
}
```

Android host (`androidApp`, e.g. inside a Compose `AndroidView` factory or an Activity):

```kotlin
// androidMain / androidApp
import com.kmp.datacapture.barcode.ar.BarcodeArView
import com.kmp.datacapture.barcode.ui.toAndroidView

val barcodeArView = registerView(BarcodeArView(context, barcodeAr, viewSettings))
val nativeAndroidView: android.view.View = barcodeArView.toAndroidView()
```

iOS host (Swift, via a `UIViewRepresentable`):

```swift
// iosApp
let barcodeArView = registerView(view: BarcodeArView(barcodeAr: barcodeAr, settings: viewSettings))
let uiView: UIView = barcodeArView.toUIView()
```

Never call `.toNative()` from application code — it exists only because Kotlin's `internal`
visibility cannot span the multi-module KMP SDK. Use `toAndroidView()` / `toUIView()`.

#### BarcodeArView Members

| Member | Description |
|--------|-------------|
| `start()` | Begin or resume scanning. Call once providers/listener are assigned. |
| `pause()` | Temporarily suspend scanning; the view stays alive and can be resumed with `start()`. |
| `stop()` | Terminal teardown — releases resources; the view is not usable afterwards. |
| `reset()` | Clear all cached highlights/annotations; re-invokes providers for all tracked barcodes. |
| `highlightProvider` | `BarcodeArHighlightProvider?` — supplies highlights per barcode. |
| `annotationProvider` | `BarcodeArAnnotationProvider?` — supplies annotations per barcode. |
| `uiListener` | `BarcodeArViewUiListener?` — receives tap events on highlights. |
| `shouldShowTorchControl` / `torchControlPosition` / `torchControlOffset` | Torch (flashlight) toggle control. |
| `shouldShowZoomControl` / `zoomControlPosition` / `zoomControlOffset` / `zoomControlOrientation` | Zoom control. |
| `shouldShowCameraSwitchControl` / `cameraSwitchControlPosition` / `cameraSwitchControlOffset` | Camera-switch control. |
| `logoStyle` / `logoAnchor` / `logoOffset` | Scandit logo placement. |

### Step 6 — BarcodeArListener (or the `sessionUpdates` Flow)

Implement `BarcodeArListener` to receive per-frame session updates, or — a KMP-only convenience —
collect the cold `BarcodeAr.sessionUpdates: Flow<BarcodeArSession>` extension, which registers a
listener for you for the lifetime of the collection.

```kotlin
import com.kmp.datacapture.barcode.ar.BarcodeAr
import com.kmp.datacapture.barcode.ar.BarcodeArListener
import com.kmp.datacapture.barcode.ar.BarcodeArSession
import com.kmp.datacapture.barcode.batch.TrackedBarcode
import com.kmp.datacapture.core.data.FrameData

class MyListener : BarcodeArListener {
    override fun onSessionUpdated(
        barcodeAr: BarcodeAr,
        session: BarcodeArSession,
        frameData: FrameData
    ) {
        val added: List<TrackedBarcode> = session.addedTrackedBarcodes
        for (tracked in added) {
            // tracked.barcode.data, tracked.barcode.symbology
        }
    }
}

barcodeAr.addListener(MyListener())
```

Or with the Flow:

```kotlin
import com.kmp.datacapture.barcode.ar.sessionUpdates
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.flow.onEach

barcodeAr.sessionUpdates
    .onEach { session -> /* session.addedTrackedBarcodes, session.trackedBarcodes */ }
    .launchIn(coroutineScope)
```

#### BarcodeArListener / BarcodeArSession / TrackedBarcode

| Member | Description |
|--------|-------------|
| `onSessionUpdated(barcodeAr, session, frameData)` | Called every processed frame. Has an empty default body — override it. |
| `BarcodeArSession.trackedBarcodes` | `Map<Int, TrackedBarcode>` — all currently tracked barcodes, keyed by tracking ID. |
| `BarcodeArSession.addedTrackedBarcodes` | `List<TrackedBarcode>` — barcodes that entered the view in this frame. |
| `BarcodeArSession.removedTrackedBarcodes` | `List<Int>` — tracking IDs of barcodes that left the view. |
| `BarcodeArSession.reset()` | Clear all tracked state. |
| `TrackedBarcode.barcode` | The decoded `Barcode` — access `.data`, `.symbology`, etc. |
| `TrackedBarcode.identifier` | Unique tracking ID for this barcode. |
| `TrackedBarcode.location` | Position as a `Quadrilateral`. |
| `TrackedBarcode.getAnchorPosition(anchor)` | The point on `location` for a given `Anchor`. |

## Highlights (BarcodeArHighlightProvider)

Highlights are visual overlays drawn over each tracked barcode. Implement
`BarcodeArHighlightProvider` and assign it to `barcodeArView.highlightProvider`. The callback is a
plain Kotlin lambda — invoke it as a function, not `callback.onData(...)`. Neither the provider
method nor the highlight constructors take a `Context`.

```kotlin
import com.kmp.datacapture.barcode.ar.BarcodeArHighlight
import com.kmp.datacapture.barcode.ar.BarcodeArHighlightProvider
import com.kmp.datacapture.barcode.ar.BarcodeArRectangleHighlight
import com.kmp.datacapture.barcode.data.Barcode

class HighlightProvider : BarcodeArHighlightProvider {
    override fun highlightForBarcode(barcode: Barcode, callback: (BarcodeArHighlight?) -> Unit) {
        // Return null to hide a barcode, or supply a highlight.
        callback(BarcodeArRectangleHighlight(barcode))
    }
}

// Assign before calling start():
barcodeArView.highlightProvider = HighlightProvider()
```

### Built-in Highlight Types

**BarcodeArRectangleHighlight** — rectangular overlay matched to the barcode shape:
```kotlin
import com.kmp.datacapture.barcode.ar.BarcodeArRectangleHighlight

val highlight = BarcodeArRectangleHighlight(barcode)
// Customize: highlight.brush, highlight.icon
```

**BarcodeArCircleHighlight** — circular dot or icon overlay:
```kotlin
import com.kmp.datacapture.barcode.ar.BarcodeArCircleHighlight
import com.kmp.datacapture.barcode.ar.BarcodeArCircleHighlightPreset

val highlight = BarcodeArCircleHighlight(barcode, BarcodeArCircleHighlightPreset.DOT)
// Customize: highlight.brush, highlight.icon, highlight.size (Float), highlight.isPulsing
```

Pass `null` to `callback(null)` to hide a barcode entirely.

### Customizing a highlight brush and icon

Both `BarcodeArRectangleHighlight` and `BarcodeArCircleHighlight` expose a `brush`
(`com.kmp.datacapture.core.ui.style.Brush`) and an `icon` (`ScanditIcon?`). Colors use
`Color.fromRgba(r, g, b, a)`; icons are built with `ScanditIcon.builder()`:

```kotlin
import com.kmp.datacapture.barcode.ar.BarcodeArRectangleHighlight
import com.kmp.datacapture.core.common.Color
import com.kmp.datacapture.core.ui.ScanditIcon
import com.kmp.datacapture.core.ui.ScanditIconType
import com.kmp.datacapture.core.ui.style.Brush

val highlight = BarcodeArRectangleHighlight(barcode).apply {
    brush = Brush(
        fillColor = Color.fromRgba(0x00, 0xFF, 0x00, 0x4C),
        strokeColor = Color.fromRgba(0x00, 0xFF, 0x00, 0xFF),
        strokeWidth = 1f
    )
    icon = ScanditIcon.builder()
        .withIcon(ScanditIconType.CHECKMARK)
        .withIconColor(Color.fromRgba(0xFF, 0xFF, 0xFF))
        .build()
}
```

`BarcodeArCircleHighlight(barcode, preset)` additionally exposes `size: Float` and
`isPulsing: Boolean`:

```kotlin
import com.kmp.datacapture.barcode.ar.BarcodeArCircleHighlight
import com.kmp.datacapture.barcode.ar.BarcodeArCircleHighlightPreset

val highlight = BarcodeArCircleHighlight(barcode, BarcodeArCircleHighlightPreset.ICON).apply {
    isPulsing = true
}
```

> There is no custom-drawn-view highlight type on KMP (no `BarcodeArCustomHighlight`, and
> `BarcodeArHighlight` exposes no `createView()`/`update()` hook to subclass). Use brush/icon
> customization on the built-in `BarcodeArRectangleHighlight` / `BarcodeArCircleHighlight` types
> instead.

## Annotations (BarcodeArAnnotationProvider)

Annotations are floating tooltips or panels displayed alongside a tracked barcode. Implement
`BarcodeArAnnotationProvider` and assign it to `barcodeArView.annotationProvider`. Pass `null` to
suppress the annotation for a given barcode.

```kotlin
import com.kmp.datacapture.barcode.ar.BarcodeArAnnotation
import com.kmp.datacapture.barcode.ar.BarcodeArAnnotationProvider
import com.kmp.datacapture.barcode.ar.BarcodeArStatusIconAnnotation
import com.kmp.datacapture.barcode.data.Barcode

class AnnotationProvider : BarcodeArAnnotationProvider {
    override fun annotationForBarcode(barcode: Barcode, callback: (BarcodeArAnnotation?) -> Unit) {
        val annotation = BarcodeArStatusIconAnnotation(barcode).apply {
            text = "Example annotation"
        }
        callback(annotation)
    }
}

// Assign before calling start():
barcodeArView.annotationProvider = AnnotationProvider()
```

Every annotation type implements `BarcodeArAnnotation`, which exposes `annotationTrigger:
BarcodeArAnnotationTrigger` — controls when it appears:

| Value | Behavior |
|-------|----------|
| `HIGHLIGHT_TAP` | Shown only when the user taps the highlight. |
| `HIGHLIGHT_TAP_AND_BARCODE_SCAN` | Shown on scan; can be toggled by tapping the highlight. Default for info/status-icon/responsive annotations. |
| `BARCODE_SCAN` | Shown on scan and stays visible; not toggleable by tap. |

### Info annotation (BarcodeArInfoAnnotation)

A structured tooltip with an optional header, body rows, and an optional footer.

```kotlin
import com.kmp.datacapture.barcode.ar.BarcodeArInfoAnnotation
import com.kmp.datacapture.barcode.ar.BarcodeArInfoAnnotationBodyComponent
import com.kmp.datacapture.barcode.ar.BarcodeArInfoAnnotationFooter
import com.kmp.datacapture.barcode.ar.BarcodeArInfoAnnotationHeader
import com.kmp.datacapture.barcode.ar.BarcodeArInfoAnnotationWidthPreset

val annotation = BarcodeArInfoAnnotation(barcode).apply {
    width = BarcodeArInfoAnnotationWidthPreset.MEDIUM
    header = BarcodeArInfoAnnotationHeader().apply { text = "Product" }
    body = listOf(
        BarcodeArInfoAnnotationBodyComponent().apply { text = barcode.data ?: "" }
    )
    footer = BarcodeArInfoAnnotationFooter().apply { text = "Tap for details" }
}
```

#### BarcodeArInfoAnnotation Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `body` | `List<BarcodeArInfoAnnotationBodyComponent>` | `[]` | Body rows. |
| `header` | `BarcodeArInfoAnnotationHeader?` | `null` | Optional header (`text`, `icon`, `fontFamily`, `textSize`, `textColor`, `backgroundColor`). |
| `footer` | `BarcodeArInfoAnnotationFooter?` | `null` | Optional footer, same properties as header. |
| `width` | `BarcodeArInfoAnnotationWidthPreset` | `SMALL` | `SMALL`, `MEDIUM`, or `LARGE`. Height adjusts to fit content. |
| `anchor` | `BarcodeArInfoAnnotationAnchor` | — | `TOP`, `BOTTOM`, `LEFT`, `RIGHT` — point pinned to the barcode. |
| `hasTip` | `Boolean` | `true` | Show pointer toward the barcode. |
| `isEntireAnnotationTappable` | `Boolean` | `false` | `true` = whole annotation fires one tap callback via `listener`; `false` = per-element header/footer/icon callbacks fire instead. |
| `backgroundColor` | `Color` | — | Background color. |
| `listener` | `BarcodeArInfoAnnotationListener?` | `null` | Receives tap events. |

`BarcodeArInfoAnnotationBodyComponent` (no-arg constructor) exposes `text`, `fontFamily`,
`textSize`, `textAlignment`, `textColor`, `styledText` (a `StyledText?` overriding the plain-text
styling properties when set), `leftIcon`/`isLeftIconTappable`, `rightIcon`/`isRightIconTappable`:

```kotlin
import com.kmp.datacapture.barcode.ar.BarcodeArInfoAnnotationBodyComponent
import com.kmp.datacapture.core.common.TextAlignment

val row = BarcodeArInfoAnnotationBodyComponent().apply {
    text = "In stock: 42"
    textAlignment = TextAlignment.LEFT
    leftIcon = ScanditIcon.builder().withIcon(ScanditIconType.CHECKMARK).build()
}
```

`BarcodeArInfoAnnotationListener` methods all have empty default bodies — override only what you
need:

```kotlin
import com.kmp.datacapture.barcode.ar.BarcodeArInfoAnnotationListener

annotation.listener = object : BarcodeArInfoAnnotationListener {
    override fun onInfoAnnotationTapped(annotation: BarcodeArInfoAnnotation) {
        // Fires only when isEntireAnnotationTappable == true.
    }
    override fun onInfoAnnotationHeaderTapped(annotation: BarcodeArInfoAnnotation) {}
    override fun onInfoAnnotationFooterTapped(annotation: BarcodeArInfoAnnotation) {}
    override fun onInfoAnnotationLeftIconTapped(
        annotation: BarcodeArInfoAnnotation,
        component: BarcodeArInfoAnnotationBodyComponent,
        componentIndex: Int
    ) {}
    override fun onInfoAnnotationRightIconTapped(
        annotation: BarcodeArInfoAnnotation,
        component: BarcodeArInfoAnnotationBodyComponent,
        componentIndex: Int
    ) {}
}
```

### Popover annotation (BarcodeArPopoverAnnotation)

A row of tappable icon+text buttons shown when the user taps the highlight (default trigger:
`HIGHLIGHT_TAP`).

```kotlin
import com.kmp.datacapture.barcode.ar.BarcodeArPopoverAnnotation
import com.kmp.datacapture.barcode.ar.BarcodeArPopoverAnnotationButton
import com.kmp.datacapture.barcode.ar.BarcodeArPopoverAnnotationListener
import com.kmp.datacapture.core.ui.ScanditIcon
import com.kmp.datacapture.core.ui.ScanditIconType

val acceptButton = BarcodeArPopoverAnnotationButton(
    icon = ScanditIcon.builder().withIcon(ScanditIconType.CHECKMARK).build(),
    text = "Accept"
)
val annotation = BarcodeArPopoverAnnotation(barcode, listOf(acceptButton)).apply {
    isEntirePopoverTappable = false
    listener = object : BarcodeArPopoverAnnotationListener {
        override fun onPopoverButtonTapped(
            popover: BarcodeArPopoverAnnotation,
            button: BarcodeArPopoverAnnotationButton,
            buttonIndex: Int
        ) {
            // React to the tapped button.
        }
        override fun onPopoverTapped(popover: BarcodeArPopoverAnnotation) {}
    }
}
```

`BarcodeArPopoverAnnotationButton(icon, text)` also exposes `fontFamily`, `textSize`,
`textColor`, and `enabled` (defaults `true`). `BarcodeArPopoverAnnotation` also exposes `anchor:
BarcodeArPopoverAnnotationAnchor` (`TOP`/`BOTTOM`/`LEFT`/`RIGHT`).

### Status icon annotation (BarcodeArStatusIconAnnotation)

A compact icon (with optional short text, max 20 characters) shown over the barcode.

```kotlin
import com.kmp.datacapture.barcode.ar.BarcodeArStatusIconAnnotation
import com.kmp.datacapture.barcode.ar.BarcodeArStatusIconAnnotationAnchor
import com.kmp.datacapture.core.ui.ScanditIcon
import com.kmp.datacapture.core.ui.ScanditIconShape
import com.kmp.datacapture.core.ui.ScanditIconType

val annotation = BarcodeArStatusIconAnnotation(barcode).apply {
    text = "Close to expiry"
    icon = ScanditIcon.builder()
        .withBackgroundShape(ScanditIconShape.CIRCLE)
        .withIcon(ScanditIconType.EXCLAMATION_MARK)
        .build()
    anchor = BarcodeArStatusIconAnnotationAnchor.TOP
}
```

`BarcodeArStatusIconAnnotation` also exposes `hasTip`, `textColor`, `backgroundColor`. Unlike the
other annotation types, `icon` is non-null (there is always a default icon).

### Responsive annotation (BarcodeArResponsiveAnnotation)

Switches between two `BarcodeArInfoAnnotation` variations based on how large the barcode appears
relative to the screen. Either variation may be `null`.

```kotlin
import com.kmp.datacapture.barcode.ar.BarcodeArInfoAnnotation
import com.kmp.datacapture.barcode.ar.BarcodeArResponsiveAnnotation

BarcodeArResponsiveAnnotation.threshold = 0.1f // barcode-area / screen-area ratio; default 0.05

val closeUp = BarcodeArInfoAnnotation(barcode)
val farAway = BarcodeArInfoAnnotation(barcode)
val annotation = BarcodeArResponsiveAnnotation(
    barcode,
    closeUpAnnotation = closeUp,
    farAwayAnnotation = farAway
)
```

`threshold` is a `companion object` property shared across all responsive annotations, not a
per-instance setting.

> There is no custom-drawn-view annotation type documented as available on KMP. Use the built-in
> info/popover/status-icon/responsive annotation types and their styling properties instead of
> looking for a custom-annotation seam.

## Tap handling (BarcodeArViewUiListener)

Assign a `BarcodeArViewUiListener` to `barcodeArView.uiListener` to react to highlight taps. Note
the KMP callback has **no `View` parameter** (unlike native Android's 4-arg version):

```kotlin
import com.kmp.datacapture.barcode.ar.BarcodeAr
import com.kmp.datacapture.barcode.ar.BarcodeArHighlight
import com.kmp.datacapture.barcode.ar.BarcodeArViewUiListener
import com.kmp.datacapture.barcode.data.Barcode

barcodeArView.uiListener = object : BarcodeArViewUiListener {
    override fun onHighlightForBarcodeTapped(
        barcodeAr: BarcodeAr,
        barcode: Barcode,
        highlight: BarcodeArHighlight
    ) {
        // React to the user tapping a highlight.
    }
}
```

## Barcode filtering (BarcodeArFilter)

Implement `BarcodeArFilter` and register it with `barcodeAr.setBarcodeFilter(filter)` (pass
`null` to clear) to restrict which barcodes are augmented. `filterBarcodes` runs on an internal
recognition thread and must return quickly — avoid blocking I/O or expensive computation. It is
re-evaluated when barcodes are added/removed or when the filter itself changes, but not on every
position update.

```kotlin
import com.kmp.datacapture.barcode.ar.BarcodeArFilter
import com.kmp.datacapture.barcode.data.Barcode

class PrefixFilter : BarcodeArFilter {
    override fun filterBarcodes(barcodes: List<Barcode>): List<Barcode> =
        barcodes.filter { it.data?.startsWith("PROD-") == true }
}

barcodeAr.setBarcodeFilter(PrefixFilter())
```

## Optional configuration — BarcodeArFeedback

BarcodeAr plays a sound and vibrates on scan by default. Customize per-event feedback via
`scanned` / `tapped`:

```kotlin
import com.kmp.datacapture.barcode.ar.BarcodeArFeedback

// Suppress all feedback (silent scanning):
barcodeAr.feedback = BarcodeArFeedback()

// Restore defaults (scan click + short vibration on scan; silent on tap):
barcodeAr.feedback = BarcodeArFeedback.defaultFeedback()
```

`BarcodeArFeedback()` (public no-arg constructor) creates silent feedback; assign to `scanned`
and/or `tapped` (both `com.kmp.datacapture.core.feedback.Feedback`) to customize further.

## Compose Multiplatform

The `barcode-compose` module ships a top-level `@Composable fun BarcodeArView(...)` — a distinct
declarative wrapper around the base-module `BarcodeArView` class, in package
`com.kmp.datacapture.barcode.compose`. It constructs the platform view internally (no manual
`toAndroidView()`/`toUIView()` needed) and starts scanning as the final mount step, stopping on
dispose.

```kotlin
import com.kmp.datacapture.barcode.ar.BarcodeArSettings
import com.kmp.datacapture.barcode.compose.BarcodeArView
import com.kmp.datacapture.barcode.compose.rememberBarcodeArViewState
import com.kmp.datacapture.barcode.data.Symbology

@Composable
fun ScannerScreen() {
    val settings = remember {
        BarcodeArSettings.barcodeArSettings().apply {
            enableSymbology(Symbology.EAN13_UPCA, true)
        }
    }
    val viewState = rememberBarcodeArViewState()
    val highlightProvider = remember { MyHighlightProvider() }

    BarcodeArView(
        settings = settings,
        highlightProvider = highlightProvider,
        state = viewState,
        modifier = Modifier.fillMaxSize(),
    )
}
```

- `settings` / `viewSettings` default to fresh `BarcodeArSettings.barcodeArSettings()` /
  `BarcodeArViewSettings.barcodeArViewSettings()`.
- `annotationProvider` / `highlightProvider` default to `null` (no overlay). **Stabilize with
  `remember`** — a fresh instance built inline on every recomposition is reassigned to the view
  every frame.
- `context` defaults to `DataCaptureContext.sharedInstance`; pass an explicit `DataCaptureContext`
  to reuse one already created elsewhere.
- `barcodeAr` is an advanced override — by default one is built from `settings` via
  `rememberBarcodeAr(context, settings)`.
- `state: BarcodeArViewState` (from `rememberBarcodeArViewState()`) exposes imperative
  `reset()` / `start()` / `pause()` / `stop()` on the mounted view — calling any of them before
  the view is mounted throws `IllegalStateException`.
- `overlay: @Composable BoxScope.() -> Unit` draws Compose content on top of the camera view,
  inside the same `Box`.

## Lifecycle & Teardown

Drive `start()` / `pause()` / `stop()` from your screen's lifecycle — there is no separate
`onResume()`/`onPause()`/`onDestroy()` split like native Android; those are folded into the KMP
surface:

```kotlin
fun onScreenResumed() { barcodeArView.start() }   // begin/resume scanning
fun onScreenPaused() { barcodeArView.pause() }    // suspend; resumable with start()

fun onScreenDisposed() {
    barcodeArView.stop()   // terminal teardown — view is not usable afterwards
    barcodeAr.removeListener(myListener)
}
```

Call `barcodeArView.reset()` (not a full teardown) when you need to clear cached
highlights/annotations and re-query the providers for all currently tracked barcodes — e.g. after
switching between demo modes in a multi-mode screen.

## Pitfalls

1. **Factories, not constructors.** `BarcodeAr.forContext(...)`,
   `BarcodeArSettings.barcodeArSettings()`, `BarcodeArViewSettings.barcodeArViewSettings()` are
   all companion factory functions. None of `BarcodeArSettings()` / `BarcodeArViewSettings()` /
   `BarcodeAr(...)` compiles.
2. **One flat package.** Everything AR-related is `com.kmp.datacapture.barcode.ar.*` — do not
   invent native Android's `ar.capture`/`ar.ui`/`ar.ui.highlight`/`ar.ui.annotations` split.
3. **`BarcodeArView` can't be constructed in shared code.** Its constructor is platform-divergent
   (`Context` on Android, none on iOS) — build it in each platform host and pass it into shared
   code (e.g. a `registerView(view)` function).
4. **KMP's `BarcodeArView` always owns its own camera**, including on Android — there is no hook
   to feed it custom `CameraSettings` from shared code. `BarcodeAr.recommendedCameraSettings()` is
   informational only.
5. **Lifecycle is `start()`/`pause()`/`stop()`/`reset()`** — no `onResume`/`onPause`/`onDestroy`.
   `stop()` is terminal; the view cannot be restarted afterwards.
6. **Provider callbacks are lambdas.** `callback(value)`, not `callback.onData(value)`; neither
   `highlightForBarcode` nor `annotationForBarcode` takes a `Context`.
7. **`onHighlightForBarcodeTapped` has 3 args** (`barcodeAr`, `barcode`, `highlight`) — no `View`
   parameter, unlike native Android.
8. **No custom highlight/annotation view seam on KMP.** Don't suggest `BarcodeArCustomHighlight`
   or `BarcodeArCustomAnnotation` — use brush/icon customization on the built-in types instead.
9. **Symbologies** — all disabled by default; enable only what is needed; names use underscores
   (`EAN13_UPCA`, not `ean13Upca`).
10. **License placeholder** is exactly `-- ENTER YOUR SCANDIT LICENSE KEY HERE --`.
11. **Runtime permission** — add `CAMERA` to the Android manifest and request it at runtime
    before the first scan; add `NSCameraUsageDescription` to iOS's `Info.plist`.
