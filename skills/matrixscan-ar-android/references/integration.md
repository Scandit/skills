# BarcodeAr (MatrixScan AR) Android Integration Guide

BarcodeAr is the multi-barcode AR scanning mode. It simultaneously tracks all barcodes in the camera feed and overlays interactive highlights and annotations on each one in real time. Unlike BarcodeCapture, BarcodeAr does not require a separate `Camera` object — the `BarcodeArView` handles camera management internally. AR overlays are driven by **provider interfaces**: `BarcodeArHighlightProvider` supplies a highlight per barcode, and `BarcodeArAnnotationProvider` supplies an optional annotation.

Examples below use Kotlin and an Activity. The same APIs work in Fragments — adapt ownership of `DataCaptureContext`, `BarcodeAr`, and the view to the project's existing structure.

## Prerequisites

- Scandit Data Capture SDK for Android — add via Gradle. Before writing the dependency, fetch the latest published version from `https://central.sonatype.com/artifact/com.scandit.datacapture/barcode` and extract the latest version number from the page. Then add both dependencies to `app/build.gradle`:
  ```gradle
  dependencies {
      implementation "com.scandit.datacapture:barcode:<latest-version>"
      implementation "com.scandit.datacapture:core:<latest-version>"
  }
  ```
  Or in `app/build.gradle.kts`:
  ```kotlin
  dependencies {
      implementation("com.scandit.datacapture:barcode:<latest-version>")
      implementation("com.scandit.datacapture:core:<latest-version>")
  }
  ```
  The SDK is distributed via Maven Central.
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- Camera permission in `AndroidManifest.xml`:
  ```xml
  <uses-feature
      android:name="android.hardware.camera"
      android:required="true" />
  <uses-permission android:name="android.permission.CAMERA" />
  ```
  Request the permission at runtime using the standard Android permission API before scanning starts.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that enabling only what the app actually needs improves tracking performance.

Once the user responds, ask them which Activity or Fragment they'd like to integrate BarcodeAr into. Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `implementation "com.scandit.datacapture:barcode:<version>"` and `implementation "com.scandit.datacapture:core:<version>"` to `app/build.gradle` (the version was already fetched and filled in above).
2. Add `<uses-permission android:name="android.permission.CAMERA" />` and the `<uses-feature>` element to `AndroidManifest.xml`.
3. Request the `CAMERA` permission at runtime before scanning starts.
4. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com.

## Package paths

| Class | Package |
|-------|---------|
| `BarcodeAr`, `BarcodeArSettings`, `BarcodeArListener`, `BarcodeArSession` | `com.scandit.datacapture.barcode.ar.capture` |
| `BarcodeArFeedback` | `com.scandit.datacapture.barcode.ar.feedback` |
| `BarcodeArView`, `BarcodeArViewSettings`, `BarcodeArViewUiListener` | `com.scandit.datacapture.barcode.ar.ui` |
| `BarcodeArRectangleHighlight`, `BarcodeArCircleHighlight` | `com.scandit.datacapture.barcode.ar.ui.highlight` |
| `BarcodeArHighlightProvider`, `BarcodeArHighlight` | `com.scandit.datacapture.barcode.ar.ui.highlight` |
| `BarcodeArAnnotationProvider`, `BarcodeArAnnotation`, `BarcodeArInfoAnnotation`, `BarcodeArStatusIconAnnotation`, `BarcodeArPopoverAnnotation` | `com.scandit.datacapture.barcode.ar.ui.annotations` |
| `BarcodeArInfoAnnotationBodyComponent`, `BarcodeArInfoAnnotationHeader`, `BarcodeArInfoAnnotationFooter`, `BarcodeArInfoAnnotationWidthPreset`, `BarcodeArInfoAnnotationAnchor` | `com.scandit.datacapture.barcode.ar.ui.annotations.info` |
| `TrackedBarcode` | `com.scandit.datacapture.barcode.batch.data` |

## Step 1 — Create the DataCaptureContext

```kotlin
import com.scandit.datacapture.core.capture.DataCaptureContext

private val dataCaptureContext = DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
```

## Step 2 — Configure BarcodeArSettings

All symbologies are disabled by default. Enable each one explicitly; enabling only what is needed reduces tracking overhead.

```kotlin
import com.scandit.datacapture.barcode.ar.capture.BarcodeArSettings
import com.scandit.datacapture.barcode.data.Symbology

val settings = BarcodeArSettings().apply {
    enableSymbology(Symbology.EAN13_UPCA, true)
    enableSymbology(Symbology.CODE128, true)
    enableSymbology(Symbology.QR, true)
}
```

You can also enable a set at once:
```kotlin
settings.enableSymbologies(setOf(Symbology.EAN13_UPCA, Symbology.CODE128))
```

### BarcodeArSettings Members

| Member | Description |
|--------|-------------|
| `enableSymbology(symbology, enabled)` | Enable or disable one symbology. |
| `enableSymbologies(symbologies)` | Enable a `Set<Symbology>` in one call. |
| `getSymbologySettings(symbology)` | Get per-symbology `SymbologySettings` (e.g. `activeSymbolCounts`). |

## Step 3 — Create BarcodeAr

BarcodeAr uses a direct constructor — not a factory. Pass the context and settings together.

```kotlin
import com.scandit.datacapture.barcode.ar.capture.BarcodeAr

private val barcodeAr = BarcodeAr(dataCaptureContext, settings)
```

To apply updated settings at runtime: `barcodeAr.applySettings(newSettings)`.

### BarcodeAr Members

| Member | Description |
|--------|-------------|
| `BarcodeAr(dataCaptureContext, settings)` | Constructor — creates the mode and attaches it to the context. |
| `addListener(listener)` / `removeListener(listener)` | Register or remove a `BarcodeArListener`. |
| `applySettings(settings)` | Update settings at runtime. |
| `applySettings(settings, whenDone)` | Update settings at runtime with a completion callback. |
| `feedback` | `BarcodeArFeedback` — sound / vibration on barcode events. |
| `setBarcodeFilter(filter)` | Restrict which barcodes appear in the session (pass `null` to show all). Added in 8.1.0. |
| `BarcodeAr.createRecommendedCameraSettings()` | Static — returns recommended `CameraSettings`. |

## Step 4 — BarcodeArViewSettings

`BarcodeArViewSettings` controls sound, haptics, and the default camera direction.

```kotlin
import com.scandit.datacapture.barcode.ar.ui.BarcodeArViewSettings
import com.scandit.datacapture.core.source.CameraPosition

val viewSettings = BarcodeArViewSettings().apply {
    hapticEnabled = true
    soundEnabled = true
    defaultCameraPosition = CameraPosition.WORLD_FACING
}
```

### BarcodeArViewSettings Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `soundEnabled` | `Boolean` | `true` | Whether a beep plays on each tracked barcode. |
| `hapticEnabled` | `Boolean` | `true` | Whether haptics fire on each tracked barcode. |
| `defaultCameraPosition` | `CameraPosition` | `WORLD_FACING` | Camera to open on start. |

## Step 5 — Create and embed BarcodeArView

`BarcodeArView` extends `FrameLayout` and manages the camera and AR rendering internally. It adds itself automatically to the provided `parentView`.

```kotlin
import com.scandit.datacapture.barcode.ar.ui.BarcodeArView

// In onCreate() — pass the root ViewGroup of your layout as parentView:
val barcodeArView = BarcodeArView(parentView, barcodeAr, dataCaptureContext, viewSettings)
```

There is also a 5-argument overload accepting custom camera settings:
```kotlin
val barcodeArView = BarcodeArView(parentView, barcodeAr, dataCaptureContext, viewSettings, cameraSettings)
```

To use BarcodeArView as the full-screen content of an Activity with no existing layout:
```kotlin
val container = FrameLayout(this)
setContentView(container)
val barcodeArView = BarcodeArView(container, barcodeAr, dataCaptureContext, viewSettings)
```

### BarcodeArView UI Controls

```kotlin
barcodeArView.apply {
    shouldShowTorchControl = true
    torchControlPosition = Anchor.BOTTOM_RIGHT
    shouldShowZoomControl = true
    zoomControlPosition = Anchor.TOP_LEFT
    shouldShowCameraSwitchControl = true
    cameraSwitchControlPosition = Anchor.TOP_RIGHT
}
```

### BarcodeArView Members

| Member | Description |
|--------|-------------|
| `onResume()` | Enable the camera and resume scanning. Call from `Activity.onResume()`. |
| `onPause()` | Pause scanning and release the camera. Call from `Activity.onPause()`. |
| `onDestroy()` | Release all resources. Call from `Activity.onDestroy()`. |
| `start()` | Begin scanning (call after setup is complete and providers are assigned). |
| `stop()` | Stop scanning. |
| `reset()` | Clear all highlights and annotations; re-invokes providers for all tracked barcodes. |
| `highlightProvider` | `BarcodeArHighlightProvider?` — supplies highlights per barcode. |
| `annotationProvider` | `BarcodeArAnnotationProvider?` — supplies annotations per barcode. |
| `uiListener` | `BarcodeArViewUiListener?` — receives tap events on highlights. |

## Step 6 — BarcodeArListener

Implement `BarcodeArListener` to receive per-frame session updates. `onSessionUpdated` is called on a **recognition thread** — dispatch any UI work to the main thread.

```kotlin
import com.scandit.datacapture.barcode.ar.capture.BarcodeArListener
import com.scandit.datacapture.barcode.ar.capture.BarcodeArSession
import com.scandit.datacapture.barcode.batch.data.TrackedBarcode
import com.scandit.datacapture.core.data.FrameData

class ScannerActivity : AppCompatActivity(), BarcodeArListener {

    override fun onSessionUpdated(
        barcodeAr: BarcodeAr,
        session: BarcodeArSession,
        frameData: FrameData
    ) {
        // Called from a recognition thread — dispatch UI work.
        val added: List<TrackedBarcode> = session.addedTrackedBarcodes
        runOnUiThread {
            for (tracked in added) {
                // tracked.barcode.data, tracked.barcode.symbology
            }
        }
    }

    override fun onObservationStarted(barcodeAr: BarcodeAr) {}
    override fun onObservationStopped(barcodeAr: BarcodeAr) {}
}
```

Register the listener after constructing `BarcodeAr`:
```kotlin
barcodeAr.addListener(this)
```

### BarcodeArListener Interface

| Callback | Description |
|----------|-------------|
| `onSessionUpdated(barcodeAr, session, frameData)` | Called every processed frame. Recognition thread — marshal UI work to main thread. |
| `onObservationStarted(barcodeAr)` | Listener was registered. |
| `onObservationStopped(barcodeAr)` | Listener was removed. |

### BarcodeArSession Properties

| Property | Type | Description |
|----------|------|-------------|
| `trackedBarcodes` | `Map<Int, TrackedBarcode>` | All currently tracked barcodes, keyed by tracking ID. |
| `addedTrackedBarcodes` | `List<TrackedBarcode>` | Barcodes that entered the view in this frame. |
| `removedTrackedBarcodes` | `List<Int>` | Tracking IDs of barcodes that left the view. |
| `reset()` | — | Clear all tracked state. |

### TrackedBarcode Properties

`TrackedBarcode` is in `com.scandit.datacapture.barcode.batch.data`.

| Property | Type | Description |
|----------|------|-------------|
| `barcode` | `Barcode` | The decoded barcode — access `.data`, `.symbology`, etc. |
| `identifier` | `Int` | Unique tracking ID for this barcode. |
| `location` | `Quadrilateral` | Position in image-space coordinates. |

## Step 7 — Highlights (BarcodeArHighlightProvider)

Highlights are visual overlays drawn over each tracked barcode. Implement `BarcodeArHighlightProvider` and assign it to `barcodeArView.highlightProvider`. Callbacks run on the **main thread**; invoke `callback.onData(...)` synchronously or from the main thread.

```kotlin
import com.scandit.datacapture.barcode.ar.ui.highlight.BarcodeArHighlightProvider
import com.scandit.datacapture.barcode.ar.ui.highlight.BarcodeArRectangleHighlight

private inner class HighlightProvider : BarcodeArHighlightProvider {
    override fun highlightForBarcode(
        context: Context,
        barcode: Barcode,
        callback: BarcodeArHighlightProvider.Callback
    ) {
        // Return null to hide a barcode, or supply a highlight.
        callback.onData(BarcodeArRectangleHighlight(context, barcode))
    }
}

// Assign before calling start():
barcodeArView.highlightProvider = HighlightProvider()
```

### Built-in Highlight Types

**BarcodeArRectangleHighlight** — rectangular overlay matched to the barcode shape:
```kotlin
import com.scandit.datacapture.barcode.ar.ui.highlight.BarcodeArRectangleHighlight

val highlight = BarcodeArRectangleHighlight(context, barcode)
// Customize: highlight.brush, highlight.icon
```

**BarcodeArCircleHighlight** — circular dot or icon overlay:
```kotlin
import com.scandit.datacapture.barcode.ar.ui.highlight.BarcodeArCircleHighlight

val highlight = BarcodeArCircleHighlight(context, barcode, BarcodeArCircleHighlightPreset.DOT)
// Customize: highlight.brush, highlight.icon, highlight.size (Float, min 18dp), highlight.isPulsing
```

Pass `null` to `callback.onData(null)` to hide a barcode entirely.

## Step 8 — Annotations (BarcodeArAnnotationProvider)

Annotations are floating tooltips or panels displayed alongside a tracked barcode. Implement `BarcodeArAnnotationProvider` and assign it to `barcodeArView.annotationProvider`. Pass `null` to suppress the annotation for a given barcode.

```kotlin
import com.scandit.datacapture.barcode.ar.ui.annotations.BarcodeArAnnotationProvider
import com.scandit.datacapture.barcode.ar.ui.annotations.BarcodeArStatusIconAnnotation

private inner class AnnotationProvider : BarcodeArAnnotationProvider {
    override fun annotationForBarcode(
        context: Context,
        barcode: Barcode,
        callback: BarcodeArAnnotationProvider.Callback
    ) {
        val annotation = BarcodeArStatusIconAnnotation(context, barcode).apply {
            text = "Example annotation"
        }
        callback.onData(annotation)
    }
}

// Assign before calling start():
barcodeArView.annotationProvider = AnnotationProvider()
```

### Built-in Annotation Types

| Type | Constructor | Description |
|------|-------------|-------------|
| `BarcodeArStatusIconAnnotation` | `(context, barcode)` | Compact icon that expands to text on tap. Default trigger: `HIGHLIGHT_TAP_AND_BARCODE_SCAN`. |
| `BarcodeArInfoAnnotation` | `(context, barcode)` | Structured tooltip with optional header, body rows, and footer. |
| `BarcodeArPopoverAnnotation` | see Advanced Configurations | A set of icon+text action buttons. |

**BarcodeArStatusIconAnnotation Properties:**

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `icon` | `ScanditIcon` | exclamation mark | Icon shown in collapsed state. |
| `text` | `String?` | `null` | Text shown in expanded state (max 20 chars). `null` = no expand. |
| `backgroundColor` | `Int` | `#FFFFFF` | Annotation background color. |
| `textColor` | `Int` | `#121619` | Expanded text color. |
| `hasTip` | `Boolean` | `true` | Show pointer toward the barcode. |
| `annotationTrigger` | `BarcodeArAnnotationTrigger` | `HIGHLIGHT_TAP_AND_BARCODE_SCAN` | When the annotation becomes visible. |

**BarcodeArInfoAnnotation — body row example:**

`BarcodeArInfoAnnotationBodyComponent` is in the `info` sub-package — **not** `ar.ui.annotations`:

```kotlin
// IMPORTANT: BarcodeArInfoAnnotationBodyComponent is in the .info sub-package:
import com.scandit.datacapture.barcode.ar.ui.annotations.BarcodeArAnnotationProvider
import com.scandit.datacapture.barcode.ar.ui.annotations.BarcodeArInfoAnnotation
import com.scandit.datacapture.barcode.ar.ui.annotations.info.BarcodeArInfoAnnotationBodyComponent

private inner class AnnotationProvider : BarcodeArAnnotationProvider {
    override fun annotationForBarcode(
        context: Context,
        barcode: Barcode,
        callback: BarcodeArAnnotationProvider.Callback
    ) {
        val annotation = BarcodeArInfoAnnotation(context, barcode).apply {
            body = listOf(
                BarcodeArInfoAnnotationBodyComponent().apply {
                    text = barcode.data ?: ""
                }
            )
        }
        callback.onData(annotation)
    }
}
```

**BarcodeArInfoAnnotation Properties:**

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `body` | `List<BarcodeArInfoAnnotationBodyComponent>` | `[]` | Body rows. Import from `ar.ui.annotations.info`. |
| `header` | `BarcodeArInfoAnnotationHeader?` | `null` | Optional header. Import from `ar.ui.annotations.info`. |
| `footer` | `BarcodeArInfoAnnotationFooter?` | `null` | Optional footer. Import from `ar.ui.annotations.info`. |
| `width` | `BarcodeArInfoAnnotationWidthPreset` | `SMALL` | `SMALL`, `MEDIUM`, or `LARGE`. Import from `ar.ui.annotations.info`. |
| `anchor` | `BarcodeArInfoAnnotationAnchor` | `BOTTOM` | `TOP`, `BOTTOM`, `LEFT`, `RIGHT`. Import from `ar.ui.annotations.info`. |
| `hasTip` | `Boolean` | `true` | Show pointer toward the barcode. |
| `isEntireAnnotationTappable` | `Boolean` | `false` | `true` = whole annotation fires one tap callback. |
| `backgroundColor` | `Color` | `#CCFFFFFF` | Background color. |

> For exact property types, annotation trigger values, and listener interfaces, fetch the [Advanced Configurations](https://docs.scandit.com/sdks/android/matrixscan-ar/advanced/) page.

## Step 9 — Start scanning and Lifecycle management

After assigning providers and listeners, call `start()` to begin scanning:

```kotlin
barcodeArView.start()
```

Drive the view from `onResume`, `onPause`, and `onDestroy`. Call `super.*` before `barcodeArView.*`.

```kotlin
override fun onResume() {
    super.onResume()
    barcodeArView.onResume()
}

override fun onPause() {
    super.onPause()
    barcodeArView.onPause()
}

override fun onDestroy() {
    super.onDestroy()
    barcodeAr.removeListener(this)
    barcodeArView.onDestroy()
}
```

## Complete minimal example

```kotlin
import android.content.Context
import android.os.Bundle
import android.widget.FrameLayout
import androidx.appcompat.app.AppCompatActivity
import com.scandit.datacapture.barcode.ar.capture.BarcodeAr
import com.scandit.datacapture.barcode.ar.capture.BarcodeArListener
import com.scandit.datacapture.barcode.ar.capture.BarcodeArSession
import com.scandit.datacapture.barcode.ar.capture.BarcodeArSettings
import com.scandit.datacapture.barcode.ar.ui.BarcodeArView
import com.scandit.datacapture.barcode.ar.ui.highlight.BarcodeArRectangleHighlight
import com.scandit.datacapture.barcode.ar.ui.BarcodeArViewSettings
import com.scandit.datacapture.barcode.ar.ui.highlight.BarcodeArHighlightProvider
import com.scandit.datacapture.barcode.batch.data.TrackedBarcode
import com.scandit.datacapture.barcode.data.Barcode
import com.scandit.datacapture.barcode.data.Symbology
import com.scandit.datacapture.core.capture.DataCaptureContext
import com.scandit.datacapture.core.data.FrameData

class BarcodeArActivity : AppCompatActivity(), BarcodeArListener {

    private val dataCaptureContext =
        DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

    private val barcodeAr: BarcodeAr
    private lateinit var barcodeArView: BarcodeArView

    init {
        val settings = BarcodeArSettings().apply {
            enableSymbology(Symbology.EAN13_UPCA, true)
            enableSymbology(Symbology.CODE128, true)
        }
        barcodeAr = BarcodeAr(dataCaptureContext, settings)
        barcodeAr.addListener(this)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Request CAMERA permission here before scanning starts.
        val container = FrameLayout(this)
        setContentView(container)
        val viewSettings = BarcodeArViewSettings()
        barcodeArView = BarcodeArView(container, barcodeAr, dataCaptureContext, viewSettings)
        barcodeArView.highlightProvider = HighlightProvider()
        barcodeArView.start()
    }

    override fun onResume() {
        super.onResume()
        barcodeArView.onResume()
    }

    override fun onPause() {
        super.onPause()
        barcodeArView.onPause()
    }

    override fun onDestroy() {
        super.onDestroy()
        barcodeAr.removeListener(this)
        barcodeArView.onDestroy()
    }

    override fun onSessionUpdated(
        barcodeAr: BarcodeAr,
        session: BarcodeArSession,
        frameData: FrameData
    ) {
        val added: List<TrackedBarcode> = session.addedTrackedBarcodes
        runOnUiThread {
            for (tracked in added) {
                // handle tracked.barcode.data and tracked.barcode.symbology
            }
        }
    }

    override fun onObservationStarted(barcodeAr: BarcodeAr) {}
    override fun onObservationStopped(barcodeAr: BarcodeAr) {}

    private inner class HighlightProvider : BarcodeArHighlightProvider {
        override fun highlightForBarcode(
            context: Context,
            barcode: Barcode,
            callback: BarcodeArHighlightProvider.Callback
        ) {
            callback.onData(BarcodeArRectangleHighlight(context, barcode))
        }
    }
}
```

## Optional configuration

### BarcodeArFeedback

BarcodeAr plays a sound and vibrates by default. To customize:

```kotlin
import com.scandit.datacapture.barcode.ar.feedback.BarcodeArFeedback

// Suppress all feedback:
barcodeAr.feedback = BarcodeArFeedback()

// Restore defaults:
barcodeAr.feedback = BarcodeArFeedback.defaultFeedback()
```

### Tap interactions (BarcodeArViewUiListener)

```kotlin
import com.scandit.datacapture.barcode.ar.ui.BarcodeArViewUiListener

barcodeArView.uiListener = object : BarcodeArViewUiListener {
    override fun onHighlightForBarcodeTapped(
        barcodeAr: BarcodeAr,
        barcode: Barcode,
        highlight: BarcodeArHighlight,
        highlightView: View
    ) {
        // React to the user tapping a highlight.
    }
}
```

## Advanced overlays and configuration

### Customizing a highlight brush and icon

Both `BarcodeArRectangleHighlight` and `BarcodeArCircleHighlight` expose a `brush` (`com.scandit.datacapture.core.ui.style.Brush`) and an `icon` (`ScanditIcon?`). Build a `ScanditIcon` with `ScanditIconBuilder`:

```kotlin
import com.scandit.datacapture.barcode.ar.ui.highlight.BarcodeArRectangleHighlight
import com.scandit.datacapture.core.ui.style.Brush
import com.scandit.datacapture.core.ui.icon.ScanditIcon
import com.scandit.datacapture.core.ui.icon.ScanditIconBuilder
import com.scandit.datacapture.core.ui.icon.ScanditIconType

val highlight = BarcodeArRectangleHighlight(context, barcode).apply {
    brush = Brush(Color.argb(75, 0, 200, 0), Color.GREEN, 2f)
    icon = ScanditIconBuilder()
        .withIcon(ScanditIconType.CHECKMARK)
        .withIconColor(Color.WHITE)
        .build()
}
```

`ScanditIconType` values are SCREAMING_SNAKE_CASE on Android (e.g. `CHECKMARK`, `STAR_FILLED`, `EXCLAMATION_MARK`).

### BarcodeArCircleHighlight

`BarcodeArCircleHighlight(context, barcode, preset)` takes a `BarcodeArCircleHighlightPreset` (`DOT` or `ICON`) and exposes `brush`, `icon`, `size` (`Float`, min 18), and `isPulsing` (`Boolean`):

```kotlin
import com.scandit.datacapture.barcode.ar.ui.highlight.BarcodeArCircleHighlight
import com.scandit.datacapture.barcode.ar.ui.highlight.BarcodeArCircleHighlightPreset

val highlight = BarcodeArCircleHighlight(context, barcode, BarcodeArCircleHighlightPreset.DOT).apply {
    size = 24f
    isPulsing = true
}
```

### BarcodeArStatusIconAnnotation

A compact icon that expands to text on tap. Set `icon`, `text` (max 20 chars; `null` = no expand), `annotationTrigger`, and `anchor` (`BarcodeArStatusIconAnnotationAnchor`):

```kotlin
import com.scandit.datacapture.barcode.ar.ui.annotations.BarcodeArStatusIconAnnotation
import com.scandit.datacapture.barcode.ar.ui.annotations.BarcodeArStatusIconAnnotationAnchor
import com.scandit.datacapture.barcode.ar.ui.annotations.BarcodeArAnnotationTrigger

val annotation = BarcodeArStatusIconAnnotation(context, barcode).apply {
    text = "In stock"
    anchor = BarcodeArStatusIconAnnotationAnchor.TOP
    annotationTrigger = BarcodeArAnnotationTrigger.BARCODE_SCAN
}
```

### BarcodeArInfoAnnotation header and footer

In addition to `body`, an info annotation accepts an optional `header` (`BarcodeArInfoAnnotationHeader`) and `footer` (`BarcodeArInfoAnnotationFooter`), both with `text` and `icon`:

```kotlin
import com.scandit.datacapture.barcode.ar.ui.annotations.BarcodeArInfoAnnotation
import com.scandit.datacapture.barcode.ar.ui.annotations.info.BarcodeArInfoAnnotationBodyComponent
import com.scandit.datacapture.barcode.ar.ui.annotations.info.BarcodeArInfoAnnotationHeader
import com.scandit.datacapture.barcode.ar.ui.annotations.info.BarcodeArInfoAnnotationFooter
import com.scandit.datacapture.barcode.ar.ui.annotations.info.BarcodeArInfoAnnotationWidthPreset

val annotation = BarcodeArInfoAnnotation(context, barcode).apply {
    width = BarcodeArInfoAnnotationWidthPreset.MEDIUM
    header = BarcodeArInfoAnnotationHeader().apply { text = "Product" }
    body = listOf(
        BarcodeArInfoAnnotationBodyComponent().apply { text = barcode.data ?: "" }
    )
    footer = BarcodeArInfoAnnotationFooter().apply { text = "Tap for details" }
}
```

### BarcodeArPopoverAnnotation

A set of icon+text action buttons shown when the user taps the highlight. Construct with a list of `BarcodeArPopoverAnnotationButton(icon, text)` and receive taps via a `BarcodeArPopoverAnnotationListener`:

```kotlin
import com.scandit.datacapture.barcode.ar.ui.annotations.BarcodeArPopoverAnnotation
import com.scandit.datacapture.barcode.ar.ui.annotations.BarcodeArPopoverAnnotationButton
import com.scandit.datacapture.barcode.ar.ui.annotations.BarcodeArPopoverAnnotationListener
import com.scandit.datacapture.core.ui.icon.ScanditIconBuilder
import com.scandit.datacapture.core.ui.icon.ScanditIconType

val pickButton = BarcodeArPopoverAnnotationButton(
    ScanditIconBuilder().withIcon(ScanditIconType.TO_PICK).build(),
    "Pick"
)
val annotation = BarcodeArPopoverAnnotation(context, barcode, listOf(pickButton)).apply {
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

`BarcodeArPopoverAnnotation`'s default `annotationTrigger` is `BarcodeArAnnotationTrigger.HIGHLIGHT_TAP`.

### BarcodeArResponsiveAnnotation

Switches between two `BarcodeArInfoAnnotation` variations based on how large the barcode appears. The constructor takes a close-up annotation and a far-away annotation (either may be `null`). The switch point is the class-level `BarcodeArResponsiveAnnotation.threshold` (barcode-area / screen-area ratio, default `0.05`):

```kotlin
import com.scandit.datacapture.barcode.ar.ui.annotations.BarcodeArResponsiveAnnotation
import com.scandit.datacapture.barcode.ar.ui.annotations.BarcodeArInfoAnnotation

BarcodeArResponsiveAnnotation.threshold = 0.1f

val closeUp = BarcodeArInfoAnnotation(context, barcode)
val farAway = BarcodeArInfoAnnotation(context, barcode)
val annotation = BarcodeArResponsiveAnnotation(context, barcode, closeUp, farAway)
```

### BarcodeArAnnotationTrigger

Every annotation exposes `annotationTrigger: BarcodeArAnnotationTrigger`, controlling when it appears:

| Value | Behavior |
|-------|----------|
| `HIGHLIGHT_TAP` | Shown only when the user taps the highlight. |
| `HIGHLIGHT_TAP_AND_BARCODE_SCAN` | Shown on scan; can be toggled by tapping the highlight. Default for info, status-icon, responsive. |
| `BARCODE_SCAN` | Shown on scan and stays visible; not toggleable by tap. |

### Highlight tap interactions (BarcodeArViewUiListener)

Assign a `BarcodeArViewUiListener` to `barcodeArView.uiListener` to react to highlight taps. The callback `onHighlightForBarcodeTapped` delivers the `BarcodeAr`, the `Barcode`, the `BarcodeArHighlight`, and the highlight `View`:

```kotlin
import com.scandit.datacapture.barcode.ar.ui.BarcodeArViewUiListener
import com.scandit.datacapture.barcode.ar.ui.highlight.BarcodeArHighlight
import android.view.View

barcodeArView.uiListener = object : BarcodeArViewUiListener {
    override fun onHighlightForBarcodeTapped(
        barcodeAr: BarcodeAr,
        barcode: Barcode,
        highlight: BarcodeArHighlight,
        highlightView: View
    ) {
        // React to the user tapping a highlight.
    }
}
```

### BarcodeArView UI controls

`BarcodeArView` can show built-in torch, zoom, and camera-switch controls. Each has a `shouldShow*Control` flag and a `*ControlPosition` (`Anchor`):

```kotlin
import com.scandit.datacapture.core.common.geometry.Anchor

barcodeArView.apply {
    shouldShowTorchControl = true
    torchControlPosition = Anchor.TOP_LEFT
    shouldShowZoomControl = true
    zoomControlPosition = Anchor.BOTTOM_LEFT
    shouldShowCameraSwitchControl = true
    cameraSwitchControlPosition = Anchor.TOP_RIGHT
}
```

### Custom highlight (subclass BarcodeArHighlight)

On Android there is no `BarcodeArCustomHighlight` type — create a custom highlight by implementing `BarcodeArHighlight` and overriding `createView()` (returns the `View`) and `update(view, barcodeLocation)` (positions it). Return the instance from `highlightForBarcode` via `callback.onData(...)`:

```kotlin
import com.scandit.datacapture.barcode.ar.ui.highlight.BarcodeArHighlight
import com.scandit.datacapture.core.common.geometry.Quadrilateral
import android.view.View
import android.widget.ImageView

private class CustomHighlight(private val context: Context) : BarcodeArHighlight {
    override fun createView(): View =
        ImageView(context).apply { setImageResource(R.drawable.custom_highlight) }

    override fun update(view: View, barcodeLocation: Quadrilateral) {
        view.x = barcodeLocation.center.x - view.width / 2f
        view.y = barcodeLocation.center.y - view.height / 2f
    }
}
```

### Custom annotation (subclass BarcodeArAnnotation)

On Android there is no `BarcodeArCustomAnnotation` type — implement `BarcodeArAnnotation`, set `annotationTrigger`, and override `createView()` and `update(barcodeLocation, highlightViewLocation, view)`:

```kotlin
import com.scandit.datacapture.barcode.ar.ui.annotations.BarcodeArAnnotation
import com.scandit.datacapture.barcode.ar.ui.annotations.BarcodeArAnnotationTrigger
import com.scandit.datacapture.core.common.geometry.Quadrilateral
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView

private class CustomAnnotation(private val context: Context) : BarcodeArAnnotation {
    override var annotationTrigger: BarcodeArAnnotationTrigger =
        BarcodeArAnnotationTrigger.HIGHLIGHT_TAP_AND_BARCODE_SCAN

    override fun createView(): View =
        ImageView(context).apply {
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            )
            setImageResource(R.drawable.custom_annotation)
        }

    override fun update(
        barcodeLocation: Quadrilateral,
        highlightViewLocation: Quadrilateral?,
        view: View
    ) {
        val location = highlightViewLocation ?: barcodeLocation
        view.x = location.center.x - view.width / 2f
        view.y = location.topCenter.y - view.height
    }
}
```

### Filtering tracked barcodes (BarcodeArFilter)

Implement `BarcodeArFilter` and register it with `barcodeAr.setBarcodeFilter(filter)` (pass `null` to clear) to restrict which barcodes appear in the session. `filterBarcodes` runs on a recognition thread and must return quickly:

```kotlin
import com.scandit.datacapture.barcode.ar.capture.BarcodeArFilter

private class PrefixFilter : BarcodeArFilter {
    override fun filterBarcodes(barcodes: List<Barcode>): List<Barcode> =
        barcodes.filter { it.data?.startsWith("PROD-") == true }
}

barcodeAr.setBarcodeFilter(PrefixFilter())
```

`setBarcodeFilter` was added in SDK 8.1.

### Migrating from BarcodeBatch / BarcodeTracking (MatrixScan)

When moving from the older MatrixScan mode (`BarcodeBatch`, formerly `BarcodeTracking`) to MatrixScan AR (`BarcodeAr`), the main structural changes are:

- Replace the `BarcodeBatch` / `BarcodeTracking` mode with `BarcodeAr(dataCaptureContext, settings)` — a direct constructor, not a `forDataCaptureContext()` factory.
- Replace `BarcodeBatchSettings` / `BarcodeTrackingSettings` with `BarcodeArSettings`; symbology enabling via `enableSymbology(...)` carries over.
- BarcodeAr does not use a separate `Camera` / `DataCaptureView` / `BarcodeBatchBasicOverlay`. Replace all of that with a single `BarcodeArView`, which manages the camera internally — remove any `Camera`, `setFrameSource`, `DataCaptureView`, and overlay setup.
- Replace `BarcodeBatchListener` / `BarcodeTrackingListener` with `BarcodeArListener` (`onSessionUpdated(barcodeAr, session, frameData)`).
- AR overlays are no longer driven by a basic overlay + brush. Supply visuals through `barcodeArView.highlightProvider` (`BarcodeArHighlightProvider`) and `barcodeArView.annotationProvider` (`BarcodeArAnnotationProvider`).
- Drive the lifecycle from `barcodeArView.onResume()`, `barcodeArView.onPause()`, and `barcodeArView.onDestroy()` instead of the camera's `switchToDesiredState(...)`.

## Key Rules

1. **Constructor, not factory** — `BarcodeAr(dataCaptureContext, settings)` is a direct constructor, not `forDataCaptureContext()`.
2. **No manual camera setup** — `BarcodeArView` manages the camera. Do not create a `Camera` object or call `setFrameSource`.
3. **Auto-added to parent** — `BarcodeArView` adds itself to the provided `ViewGroup` automatically on construction.
4. **Call `start()`** — after providers are assigned, call `barcodeArView.start()` to begin scanning.
5. **View-driven lifecycle** — call `super.on*()` first, then `barcodeArView.on*()` in `onResume`, `onPause`, and `onDestroy`.
6. **Recognition thread** — `onSessionUpdated` runs on a background thread; always dispatch UI work via `runOnUiThread {}`.
7. **Provider callbacks are main-thread** — `highlightForBarcode` and `annotationForBarcode` run on the main thread; invoke `callback.onData(...)` on the main thread.
8. **`TrackedBarcode` not `Barcode`** — session properties hold `TrackedBarcode`; access barcode data via `tracked.barcode.data`.
9. **Highlights take Context** — `BarcodeArRectangleHighlight(context, barcode)` and `BarcodeArCircleHighlight(context, barcode, preset)` both require a `Context` as the first argument.
10. **Return null to hide** — pass `null` to `callback.onData(null)` to suppress a highlight or annotation for a given barcode.
11. **Symbologies** — all disabled by default; enable only what is needed.
12. **Runtime permission** — add `CAMERA` to the manifest and request it at runtime before the first scan.
