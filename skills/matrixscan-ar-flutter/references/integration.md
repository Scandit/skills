# MatrixScan AR Flutter Integration Guide

MatrixScan AR (API class name: `BarcodeAr`) is a multi-barcode scanning mode that simultaneously tracks all barcodes in the camera feed and overlays interactive highlights and annotations on each one in real time. In Flutter it is backed by a `StatefulWidget` (`BarcodeArView`) that renders a native AR view. Unlike SparkScan, the highlights and annotations are driven by **provider interfaces** — the app supplies the view for each barcode, and the SDK positions it automatically.

> **State management note**: Examples below use the BLoC pattern (as in the official `MatrixScanARSimpleSample`). The same APIs work with Provider, Riverpod, GetX, or plain `StatefulWidget` — adapt ownership of `DataCaptureContext`, `BarcodeAr`, and the camera to the project's existing convention.

## Prerequisites

- Scandit Flutter packages in `pubspec.yaml`:
  - `scandit_flutter_datacapture_barcode` (pulls in `scandit_flutter_datacapture_core` transitively)
  - `permission_handler` (for the runtime camera permission on Android)
- Flutter `>=3.22.0`, Dart SDK `>=3.0.0 <4.0.0`.
- After editing `pubspec.yaml`, run `flutter pub get` to fetch the packages.
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- Camera permissions configured by the app:
  - iOS: add `NSCameraUsageDescription` to `ios/Runner/Info.plist`.
  - Android: the manifest permission is declared by the plugin; request at runtime with `permission_handler`.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that enabling only the symbologies actually needed improves tracking performance and accuracy.

Once the user responds, ask them which file they would like to integrate BarcodeAr into (typically a BLoC / controller class, or a page `StatefulWidget`). Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `scandit_flutter_datacapture_barcode` and `permission_handler` to `pubspec.yaml`, then run `flutter pub get`.
2. Add `NSCameraUsageDescription` to `ios/Runner/Info.plist` with a short usage explanation.
3. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with the key from https://ssl.scandit.com.
4. Ensure `main()` calls `WidgetsFlutterBinding.ensureInitialized()` and then `await ScanditFlutterDataCaptureBarcode.initialize()` before `runApp(...)`.
5. Call `Permission.camera.request()` from `permission_handler` before the first scan (usually in `initState()` of the scanning page).

## Step 1 — Initialize the SDK in `main()`

Plugin initialization **must** happen before any other Scandit API call. It discovers all installed Scandit Flutter plugins, fetches native defaults, and wires up the method-channel bridge.

```dart
import 'package:flutter/material.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Must be called first — sets up all Scandit plugins.
  await ScanditFlutterDataCaptureBarcode.initialize();
  runApp(const MyApp());
}
```

> **Important**: Always call `WidgetsFlutterBinding.ensureInitialized()` before the `await`. Flutter requires the binding before any platform-channel call.

## Step 2 — Create the DataCaptureContext

```dart
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

const String licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

final DataCaptureContext dataCaptureContext =
    DataCaptureContext.forLicenseKey(licenseKey);
```

- `DataCaptureContext.forLicenseKey(licenseKey)` returns a singleton — call it once and reuse the reference.
- For a given process only **one** `DataCaptureContext` exists; repeated calls return the same instance.

## Step 3 — Configure BarcodeArSettings and Symbologies

All symbologies are disabled by default. Only enable the ones the app actually needs — each extra symbology adds processing time.

```dart
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_ar.dart';

var settings = BarcodeArSettings()
  ..enableSymbologies({
    Symbology.ean13Upca,
    Symbology.ean8,
    Symbology.upce,
    Symbology.code39,
    Symbology.code128,
    Symbology.qr,
    Symbology.dataMatrix,
  });

// Optional: adjust active symbol counts for variable-length symbologies.
settings.settingsForSymbology(Symbology.code39).activeSymbolCounts = {
  7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
};
```

### BarcodeArSettings Methods

| Method | Description |
|--------|-------------|
| `enableSymbologies(symbologies)` | Enable multiple symbologies (takes a `Set<Symbology>`). |
| `enableSymbology(symbology, enabled)` | Enable or disable a single symbology. |
| `settingsForSymbology(symbology)` | Get per-symbology settings (e.g. `activeSymbolCounts`). |
| `setProperty<T>(name, value)` / `getProperty<T>(name)` | Advanced property access by name. |

## Step 4 — Construct BarcodeAr

Use the `BarcodeAr(settings)` constructor available on Flutter from SDK 7.6. This constructor does not require passing the `DataCaptureContext` directly — the context is supplied when creating the view.

```dart
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_ar.dart';

final BarcodeAr barcodeAr = BarcodeAr(settings);
```

To retrieve recommended camera settings for the mode:

```dart
final CameraSettings cameraSettings = BarcodeAr.createRecommendedCameraSettings();
```

### BarcodeAr Methods

| Method | Description |
|--------|-------------|
| `BarcodeAr(settings)` | Constructs a new instance with the given settings (Flutter 7.6+). |
| `addListener(listener)` / `removeListener(listener)` | Register/remove a `BarcodeArListener`. |
| `applySettings(settings)` | Asynchronously apply updated settings at runtime. |
| `BarcodeAr.createRecommendedCameraSettings()` | Returns `CameraSettings` tuned for BarcodeAr. |

### BarcodeAr Properties

| Property | Type | Description |
|----------|------|-------------|
| `feedback` | `BarcodeArFeedback` | The feedback (sound/vibration) emitted on barcode events. |

## Step 5 — BarcodeArViewSettings

`BarcodeArViewSettings` controls sound, haptics, and the default camera position.

```dart
final viewSettings = BarcodeArViewSettings()
  ..soundEnabled = true
  ..hapticEnabled = true
  ..defaultCameraPosition = CameraPosition.worldFacing;
```

### BarcodeArViewSettings Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `soundEnabled` | `bool` | `true` | Whether a beep plays on each tracked barcode. |
| `hapticEnabled` | `bool` | `true` | Whether haptics fire on each tracked barcode. |
| `defaultCameraPosition` | `CameraPosition` | `worldFacing` | Camera to open on start. |

## Step 6 — Create BarcodeArView

`BarcodeArView` is a `StatefulWidget`. Create it **once in `initState()`** and store it as a field; never create it inside `build()`.

```dart
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_ar.dart';

// Inside State.initState():
_barcodeArView = BarcodeArView.forModeWithViewSettingsAndCameraSettings(
  bloc.dataCaptureContext,
  bloc.barcodeAr,
  bloc.barcodeArViewSettings,
  bloc.cameraSettings,
);
```

The two available factory constructors on Flutter:

| Constructor | Description |
|-------------|-------------|
| `BarcodeArView.forMode(dataCaptureContext, barcodeAr)` | Default view and camera settings. |
| `BarcodeArView.forModeWithViewSettings(dataCaptureContext, barcodeAr, viewSettings)` | Custom view settings, default camera settings. |
| `BarcodeArView.forModeWithViewSettingsAndCameraSettings(dataCaptureContext, barcodeAr, viewSettings, cameraSettings)` | Full control over view and camera settings. |

Embed the view in the widget tree using the stored field:

```dart
@override
Widget build(BuildContext context) {
  return Scaffold(
    appBar: AppBar(title: const Text('MatrixScan AR')),
    body: _barcodeArView!,
  );
}
```

### BarcodeArView UI controls

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `shouldShowTorchControl` | `bool` | `false` | Show the torch toggle. |
| `torchControlPosition` | `Anchor` | `topLeft` | Position of the torch control. |
| `shouldShowZoomControl` | `bool` | `false` | Show the zoom slider. |
| `zoomControlPosition` | `Anchor` | `bottomRight` | Position of the zoom control. |
| `shouldShowCameraSwitchControl` | `bool` | `false` | Show the front/back camera switch. |
| `cameraSwitchControlPosition` | `Anchor` | `topRight` | Position of the camera switch. |
| `shouldShowMacroModeControl` | `bool` | `false` | Show macro-mode toggle (iOS only). |

### BarcodeArView Methods

| Method | Description |
|--------|-------------|
| `start()` | Start the scanning process (returns `Future<void>`). |
| `stop()` | Stop scanning and release the camera (returns `Future<void>`). |
| `pause()` | Pause scanning without releasing the camera (returns `Future<void>`). |
| `reset()` | Clear all highlights and annotations, then re-query the providers. |

### BarcodeArView Provider/Listener slots

| Property | Type | Description |
|----------|------|-------------|
| `highlightProvider` | `BarcodeArHighlightProvider?` | Supplies highlight instances per barcode. If `null`, a default highlight is shown. |
| `annotationProvider` | `BarcodeArAnnotationProvider?` | Supplies annotation instances per barcode. If `null`, no annotations are shown. |
| `uiListener` | `BarcodeArViewUiListener?` | Receives tap callbacks on barcode highlights. |

## Step 7 — BarcodeArListener

Implement `BarcodeArListener` on the BLoC to receive session updates. Add the listener to the `BarcodeAr` instance. Only one callback exists on Flutter:

```dart
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_ar.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

class ScannerBloc implements BarcodeArListener {
  late final BarcodeAr barcodeAr;

  ScannerBloc() {
    final settings = BarcodeArSettings()
      ..enableSymbologies({Symbology.ean13Upca, Symbology.code128});
    barcodeAr = BarcodeAr(settings);
    barcodeAr.addListener(this);
  }

  @override
  Future<void> didUpdateSession(
    BarcodeAr barcodeAr,
    BarcodeArSession session,
    Future<FrameData> Function() getFrameData,
  ) async {
    // session.addedTrackedBarcodes — barcodes that appeared in this frame.
    // session.trackedBarcodes — all currently tracked barcodes (map of id -> TrackedBarcode).
    // session.removedTrackedBarcodes — ids of barcodes that left the frame.
    for (final tracked in session.addedTrackedBarcodes) {
      debugPrint('New barcode: ${tracked.barcode.data}');
    }
  }

  void dispose() {
    barcodeAr.removeListener(this);
  }
}
```

### BarcodeArListener Callback

| Callback | Signature | Description |
|----------|-----------|-------------|
| `didUpdateSession` | `(BarcodeAr, BarcodeArSession, Future<FrameData> Function()) => Future<void>` | Invoked on every processed frame. |

### BarcodeArSession Properties

| Property | Type | Description |
|----------|------|-------------|
| `addedTrackedBarcodes` | `List<TrackedBarcode>` | Barcodes that entered the view in this frame. |
| `removedTrackedBarcodes` | `List<int>` | Identifiers of barcodes that left the view. |
| `trackedBarcodes` | `Map<int, TrackedBarcode>` | All currently tracked barcodes. |
| `reset()` | `Future<void>` | Clear all tracked barcodes and their state. |

## Step 8 — Highlights

Highlights are visual overlays drawn over each tracked barcode. Supply them via `BarcodeArHighlightProvider`. The State class (not the BLoC) is the natural place to implement this interface, because the view's `highlightProvider` slot requires a provider object.

```dart
class _ScannerPageState extends State<ScannerPage>
    with WidgetsBindingObserver
    implements BarcodeArHighlightProvider {

  final ScannerBloc _bloc = ScannerBloc();
  BarcodeArView? _barcodeArView;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _barcodeArView = BarcodeArView.forModeWithViewSettingsAndCameraSettings(
      _bloc.dataCaptureContext,
      _bloc.barcodeAr,
      _bloc.barcodeArViewSettings,
      _bloc.cameraSettings,
    )..highlightProvider = this;
    _requestCameraPermission();
  }

  @override
  Future<BarcodeArHighlight?> highlightForBarcode(Barcode barcode) async {
    // Return null to hide a barcode, or any highlight type.
    return BarcodeArRectangleHighlight(barcode);
  }
}
```

### BarcodeArHighlightProvider Interface

| Method | Signature | Description |
|--------|-----------|-------------|
| `highlightForBarcode` | `(Barcode) => Future<BarcodeArHighlight?>` | Return the highlight to display for the given barcode, or `null` to hide it. |

### Highlight types

**BarcodeArRectangleHighlight** — a rectangular overlay, matching the barcode shape.

```dart
final highlight = BarcodeArRectangleHighlight(barcode)
  ..brush = Brush(
    const Color(0x6600FFFF), // fill (with alpha)
    const Color(0xFF00FFFF), // stroke
    1.0,                     // stroke width
  )
  ..icon = ScanditIconBuilder()
      .withIcon(ScanditIconType.checkmark)
      .withIconColor(const Color(0xFFFFFFFF))
      .build();
```

| Property | Type | Description |
|----------|------|-------------|
| `barcode` | `Barcode` | Read-only; the barcode this highlight is for. |
| `brush` | `Brush` | Fill color, stroke color, stroke width. |
| `icon` | `ScanditIcon?` | Optional icon overlay. `null` = no icon. |

**BarcodeArCircleHighlight** — a circular dot or icon overlay.

```dart
final highlight = BarcodeArCircleHighlight(barcode, BarcodeArCircleHighlightPreset.dot)
  ..brush = Brush(const Color(0x660000FF), const Color(0xFF0000FF), 1.0)
  ..size = 36.0; // device-independent pixels, min 18
```

| Property | Type | Description |
|----------|------|-------------|
| `barcode` | `Barcode` | Read-only. |
| `brush` | `Brush` | Visual style. |
| `icon` | `ScanditIcon?` | Optional icon. |
| `size` | `double` | Circle diameter in dp. Minimum 18. |

`BarcodeArCircleHighlightPreset` values: `dot` (smaller circle), `icon` (larger circle).

**BarcodeArCustomHighlight** — attach any Flutter `Widget` as a highlight (available from SDK 8.1).

```dart
final highlight = BarcodeArCustomHighlight(
  barcode: barcode,
  child: Container(
    width: 44,
    height: 44,
    decoration: BoxDecoration(
      color: Colors.blue.withOpacity(0.6),
      shape: BoxShape.circle,
    ),
  ),
);
```

> **Snapshot limitation**: The widget is serialized as a still image at the time the provider returns. Animated widgets (e.g. `AnimatedContainer`, `Lottie`) will be captured as a single frame and will not animate inside the overlay. Use static widgets for custom highlights.

## Step 9 — BarcodeArViewUiListener

Receive tap events on highlights by implementing `BarcodeArViewUiListener` and assigning it to `barcodeArView.uiListener`. The BLoC is a natural owner because tap logic often modifies scan state.

```dart
class ScannerBloc implements BarcodeArListener, BarcodeArViewUiListener {
  // ...

  @override
  void didTapHighlightForBarcode(
    BarcodeAr barcodeAr,
    Barcode barcode,
    BarcodeArHighlight highlight,
  ) {
    // React to user tapping on a barcode overlay.
    debugPrint('Tapped: ${barcode.data}');
  }
}
```

Assign the listener when creating the view:

```dart
_barcodeArView = BarcodeArView.forMode(_bloc.dataCaptureContext, _bloc.barcodeAr)
  ..highlightProvider = this
  ..uiListener = _bloc;
```

### BarcodeArViewUiListener Interface

| Callback | Signature | Description |
|----------|-----------|-------------|
| `didTapHighlightForBarcode` | `(BarcodeAr, Barcode, BarcodeArHighlight) => void` | Called when the user taps a barcode highlight. |

## Step 10 — Annotations

Annotations are floating tooltips or action panels that appear alongside (not over) a tracked barcode. Supply them via `BarcodeArAnnotationProvider`. Only one annotation is shown per barcode at a time; return `null` to suppress the annotation for a given barcode.

```dart
class _ScannerPageState extends State<ScannerPage>
    with WidgetsBindingObserver
    implements BarcodeArHighlightProvider, BarcodeArAnnotationProvider {

  @override
  void initState() {
    super.initState();
    _barcodeArView = BarcodeArView.forModeWithViewSettingsAndCameraSettings(
      _bloc.dataCaptureContext,
      _bloc.barcodeAr,
      _bloc.barcodeArViewSettings,
      _bloc.cameraSettings,
    )
      ..highlightProvider = this
      ..annotationProvider = this;
  }

  @override
  Future<BarcodeArAnnotation?> annotationForBarcode(Barcode barcode) async {
    // Return the appropriate annotation type.
    return _bloc.annotationForBarcode(barcode);
  }
}
```

### BarcodeArAnnotationProvider Interface

| Method | Signature | Description |
|--------|-----------|-------------|
| `annotationForBarcode` | `(Barcode) => Future<BarcodeArAnnotation?>` | Return the annotation to show for this barcode, or `null` for none. |

### BarcodeArAnnotationTrigger

Controls when the annotation becomes visible:

| Value | Description |
|-------|-------------|
| `BarcodeArAnnotationTrigger.highlightTap` | Shown only when the user taps the barcode highlight. |
| `BarcodeArAnnotationTrigger.highlightTapAndBarcodeScan` | Shown immediately on scan; toggled by tapping the highlight. |

### Annotation type: BarcodeArInfoAnnotation

A structured tooltip with an optional header, body rows, and an optional footer.

```dart
final annotation = BarcodeArInfoAnnotation(barcode)
  ..width = BarcodeArInfoAnnotationWidthPreset.large
  ..anchor = BarcodeArInfoAnnotationAnchor.bottom
  ..isEntireAnnotationTappable = false
  ..listener = _bloc; // implements BarcodeArInfoAnnotationListener

// Header (optional)
final header = BarcodeArInfoAnnotationHeader()
  ..text = 'Product Info'
  ..backgroundColor = const Color(0xFF00FFFF);
annotation.header = header;

// Body rows
final row1 = BarcodeArInfoAnnotationBodyComponent()
  ..text = 'Barcode: ${barcode.data}';
final row2 = BarcodeArInfoAnnotationBodyComponent()
  ..text = 'Status: OK'
  ..leftIcon = ScanditIconBuilder()
      .withIcon(ScanditIconType.checkmark)
      .withIconColor(const Color(0xFF00AA00))
      .build();
annotation.body = [row1, row2];

// Footer (optional)
final footer = BarcodeArInfoAnnotationFooter()
  ..text = 'Tap for details'
  ..backgroundColor = const Color(0xFF121619);
annotation.footer = footer;
```

**BarcodeArInfoAnnotation Properties**

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `barcode` | `Barcode` | — | Read-only. |
| `width` | `BarcodeArInfoAnnotationWidthPreset` | `small` | `small`, `medium`, `large`. |
| `anchor` | `BarcodeArInfoAnnotationAnchor` | `bottom` | `top`, `bottom`, `left`, `right`. |
| `hasTip` | `bool` | `true` | Show a triangular pointer toward the barcode. |
| `isEntireAnnotationTappable` | `bool` | `false` | `true` = whole annotation tappable; `false` = individual elements are tappable. |
| `backgroundColor` | `Color` | `#CCFFFFFF` | Annotation background. |
| `header` | `BarcodeArInfoAnnotationHeader?` | `null` | Optional header. |
| `body` | `List<BarcodeArInfoAnnotationBodyComponent>` | `[]` | Body rows. |
| `footer` | `BarcodeArInfoAnnotationFooter?` | `null` | Optional footer. |
| `listener` | `BarcodeArInfoAnnotationListener?` | `null` | Tap callbacks. |

**BarcodeArInfoAnnotationBodyComponent Properties**

| Property | Type | Description |
|----------|------|-------------|
| `text` | `String?` | Row text. |
| `leftIcon` | `ScanditIcon?` | Tappable icon on the left. `null` = no icon. |
| `rightIcon` | `ScanditIcon?` | Tappable icon on the right. `null` = no icon. |
| `isLeftIconTappable` / `isRightIconTappable` | `bool` | Whether the icon is interactive. Default `true`. |
| `textColor` | `Color` | Text color. Default `#121619`. |
| `textAlign` | `TextAlignment` | Text alignment. Default `center`. |

**BarcodeArInfoAnnotationHeader Properties**

| Property | Type | Description |
|----------|------|-------------|
| `text` | `String?` | Header text. |
| `icon` | `ScanditIcon?` | Header icon. |
| `backgroundColor` | `Color?` | Header background. Default `#00FFFF`. |
| `textColor` | `Color?` | Text color. |

**BarcodeArInfoAnnotationListener Interface**

Implement to receive interaction events. All methods must be overridden:

| Callback | Dart signature | Description |
|----------|---------------|-------------|
| `didTapInfoAnnotation` | `(BarcodeArInfoAnnotation)` | Called when `isEntireAnnotationTappable` is `true` and the annotation is tapped. |
| `didTapInfoAnnotationHeader` | `(BarcodeArInfoAnnotation)` | Called when the header is tapped (when not entirely tappable). |
| `didTapInfoAnnotationFooter` | `(BarcodeArInfoAnnotation)` | Called when the footer is tapped. |
| `didTapInfoAnnotationLeftIcon` | `(BarcodeArInfoAnnotation, int)` | Called when a body row's left icon is tapped. The int is the row index. |
| `didTapInfoAnnotationRightIcon` | `(BarcodeArInfoAnnotation, int)` | Called when a body row's right icon is tapped. |

### Annotation type: BarcodeArPopoverAnnotation

A set of icon+text buttons that appears on highlight tap.

```dart
final buttons = [
  BarcodeArPopoverAnnotationButton(
    ScanditIconBuilder().withIcon(ScanditIconType.checkmark).build(),
    'Accept',
  ),
  BarcodeArPopoverAnnotationButton(
    ScanditIconBuilder().withIcon(ScanditIconType.exclamationMark).build(),
    'Flag',
  ),
];

final popover = BarcodeArPopoverAnnotation(barcode, buttons)
  ..isEntirePopoverTappable = false
  ..listener = _bloc; // implements BarcodeArPopoverAnnotationListener
```

**BarcodeArPopoverAnnotationListener Interface**

| Callback | Dart signature | Description |
|----------|---------------|-------------|
| `didTapPopoverButton` | `(BarcodeArPopoverAnnotation, BarcodeArPopoverAnnotationButton, int)` | Called when a button is tapped. The int is the button index. Called when `isEntirePopoverTappable` is `false`. |
| `didTapPopover` | `(BarcodeArPopoverAnnotation)` | Called when the entire popover is tapped. Called when `isEntirePopoverTappable` is `true`. |

### Annotation type: BarcodeArStatusIconAnnotation

A compact icon that expands to show text on tap.

```dart
final statusIcon = BarcodeArStatusIconAnnotation(barcode)
  ..icon = ScanditIconBuilder()
      .withIcon(ScanditIconType.exclamationMark)
      .withIconColor(const Color(0xFF000000))
      .build()
  ..text = 'Check stock' // max 20 chars; null = no expand
  ..backgroundColor = const Color(0xFFFBC02C)
  ..textColor = const Color(0xFF121619)
  ..hasTip = true;
```

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `icon` | `ScanditIcon` | exclamationMark on yellow | The icon shown in collapsed state. |
| `text` | `String?` | `null` | Text shown in expanded state. Max 20 chars. `null` = no expand. |
| `backgroundColor` | `Color` | `#FFFFFF` | Annotation background. |
| `textColor` | `Color` | `#121619` | Expanded text color. |
| `hasTip` | `bool` | `true` | Show pointer toward barcode. |

### Annotation type: BarcodeArResponsiveAnnotation

Automatically switches between two `BarcodeArInfoAnnotation` variants based on the barcode's size relative to the screen. Use when you want a detailed view close-up and a compact view when the barcode is far away.

```dart
final closeup = BarcodeArInfoAnnotation(barcode)
  ..width = BarcodeArInfoAnnotationWidthPreset.large
  ..body = [BarcodeArInfoAnnotationBodyComponent()..text = 'Detailed info'];

final faraway = BarcodeArInfoAnnotation(barcode)
  ..width = BarcodeArInfoAnnotationWidthPreset.small
  ..body = [BarcodeArInfoAnnotationBodyComponent()..text = 'Summary'];

final responsive = BarcodeArResponsiveAnnotation(barcode, closeup, faraway)
  ..threshold = 0.05; // barcode-area / screen-area ratio; default 0.05
```

Pass `null` for either variant to show nothing at that distance:

```dart
// Show annotation only when the barcode is close
BarcodeArResponsiveAnnotation(barcode, closeup, null)
```

### Annotation type: BarcodeArCustomAnnotation

Attach any Flutter `Widget` as an annotation (available from SDK 8.1).

```dart
final customAnnotation = BarcodeArCustomAnnotation(
  barcode: barcode,
  annotationTrigger: BarcodeArAnnotationTrigger.highlightTapAndBarcodeScan,
  child: Container(
    padding: const EdgeInsets.all(8),
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(8),
    ),
    child: Text(barcode.data ?? ''),
  ),
);
```

> **Snapshot limitation**: The widget is serialized as a static image at render time. Animated widgets will not animate inside the AR overlay. Use static widgets for custom annotations.

## Step 11 — Feedback

`BarcodeArFeedback` controls the sound and vibration emitted when barcodes are tracked. The default feedback has both sound and vibration enabled.

```dart
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

// Use the default feedback:
barcodeAr.feedback = BarcodeArFeedback.defaultFeedback;

// Disable sound, keep vibration:
final quietFeedback = BarcodeArFeedback()
  ..scanned = Feedback(vibration: Vibration.defaultVibration, sound: null);
barcodeAr.feedback = quietFeedback;

// Disable all feedback:
barcodeAr.feedback = BarcodeArFeedback();
```

### BarcodeArFeedback Properties

| Property | Type | Description |
|----------|------|-------------|
| `scanned` | `Feedback` | Feedback for the barcode-scanned event. |
| `tapped` | `Feedback` | Feedback for the element-tapped event. |
| `BarcodeArFeedback.defaultFeedback` | static | Returns default configuration (sound + vibration). |

`BarcodeArFeedback()` (empty constructor) creates a feedback with no sound and no vibration.

## Step 12 — Camera lifecycle

The camera is managed via `Camera.switchToDesiredState`. Do this from `WidgetsBindingObserver.didChangeAppLifecycleState` so scanning pauses when the app goes to background.

```dart
class _ScannerPageState extends State<ScannerPage> with WidgetsBindingObserver {
  final Camera _camera = Camera.defaultCamera!;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _requestCameraPermission();
  }

  Future<void> _requestCameraPermission() async {
    final status = await Permission.camera.request();
    if (!mounted) return;
    if (status.isGranted) {
      _camera.switchToDesiredState(FrameSourceState.on);
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    switch (state) {
      case AppLifecycleState.resumed:
        _requestCameraPermission();
        break;
      default:
        _camera.switchToDesiredState(FrameSourceState.off);
        break;
    }
  }

  @override
  void dispose() {
    _camera.switchToDesiredState(FrameSourceState.off);
    _bloc.dispose();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }
}
```

## Step 13 — Complete Example

A full working integration: plugin init, context, BLoC with listener, view creation with highlight and annotation providers.

### main.dart

```dart
import 'package:flutter/material.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ScanditFlutterDataCaptureBarcode.initialize();
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    title: 'MatrixScan AR',
    home: const ScannerPage(),
  );
}
```

### scanner_bloc.dart

```dart
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_ar.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

const String licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

class ScannerBloc implements BarcodeArListener {
  final DataCaptureContext dataCaptureContext =
      DataCaptureContext.forLicenseKey(licenseKey);
  final Camera camera = Camera.defaultCamera!;
  late final BarcodeAr barcodeAr;
  late final BarcodeArViewSettings barcodeArViewSettings;
  late final CameraSettings cameraSettings;

  ScannerBloc() {
    final settings = BarcodeArSettings()
      ..enableSymbologies({
        Symbology.ean13Upca,
        Symbology.code128,
        Symbology.qr,
      });

    barcodeAr = BarcodeAr(settings);
    barcodeAr.addListener(this);

    barcodeArViewSettings = BarcodeArViewSettings();
    cameraSettings = BarcodeAr.createRecommendedCameraSettings();

    dataCaptureContext.setFrameSource(camera);
  }

  void startCapturing() {
    camera.switchToDesiredState(FrameSourceState.on);
  }

  void stopCapturing() {
    camera.switchToDesiredState(FrameSourceState.off);
  }

  @override
  Future<void> didUpdateSession(
    BarcodeAr barcodeAr,
    BarcodeArSession session,
    Future<FrameData> Function() getFrameData,
  ) async {
    for (final tracked in session.addedTrackedBarcodes) {
      debugPrint('Tracked: ${tracked.barcode.data}');
    }
  }

  Future<BarcodeArHighlight?> highlightForBarcode(Barcode barcode) async {
    return BarcodeArRectangleHighlight(barcode)
      ..brush = Brush(
        const Color(0x6600FFFF),
        const Color(0xFF00FFFF),
        1.0,
      );
  }

  Future<BarcodeArAnnotation?> annotationForBarcode(Barcode barcode) async {
    final annotation = BarcodeArInfoAnnotation(barcode)
      ..width = BarcodeArInfoAnnotationWidthPreset.medium;
    annotation.body = [
      BarcodeArInfoAnnotationBodyComponent()
        ..text = barcode.data ?? 'No data',
    ];
    return annotation;
  }

  void dispose() {
    barcodeAr.removeListener(this);
  }
}
```

### scanner_page.dart

```dart
import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_ar.dart';

import 'scanner_bloc.dart';

class ScannerPage extends StatefulWidget {
  const ScannerPage({super.key});
  @override
  State<ScannerPage> createState() => _ScannerPageState();
}

class _ScannerPageState extends State<ScannerPage>
    with WidgetsBindingObserver
    implements BarcodeArHighlightProvider, BarcodeArAnnotationProvider {

  final ScannerBloc _bloc = ScannerBloc();
  BarcodeArView? _barcodeArView;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _barcodeArView = BarcodeArView.forModeWithViewSettingsAndCameraSettings(
      _bloc.dataCaptureContext,
      _bloc.barcodeAr,
      _bloc.barcodeArViewSettings,
      _bloc.cameraSettings,
    )
      ..highlightProvider = this
      ..annotationProvider = this;
    _requestCameraPermission();
  }

  Future<void> _requestCameraPermission() async {
    final status = await Permission.camera.request();
    if (!mounted) return;
    if (status.isGranted) _bloc.startCapturing();
  }

  @override
  Future<BarcodeArHighlight?> highlightForBarcode(Barcode barcode) {
    return _bloc.highlightForBarcode(barcode);
  }

  @override
  Future<BarcodeArAnnotation?> annotationForBarcode(Barcode barcode) {
    return _bloc.annotationForBarcode(barcode);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('MatrixScan AR')),
      body: _barcodeArView!,
    );
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    switch (state) {
      case AppLifecycleState.resumed:
        _requestCameraPermission();
        break;
      default:
        _bloc.stopCapturing();
        break;
    }
  }

  @override
  void dispose() {
    _bloc.dispose();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }
}
```

## Key Rules

1. **Initialize plugins first** — `await ScanditFlutterDataCaptureBarcode.initialize()` must be called in `main()` after `WidgetsFlutterBinding.ensureInitialized()` and before `runApp(...)`.
2. **Import** — BarcodeAr classes live in `scandit_flutter_datacapture_barcode_ar`, not in the main `scandit_flutter_datacapture_barcode` barrel. Always import both.
3. **Create BarcodeArView once** — create it in `initState()` and store as a field. Never create it inside `build()`; doing so tears down and rebuilds the native view on every rebuild.
4. **Providers are async** — `highlightForBarcode` and `annotationForBarcode` return `Future<...?>`. The SDK awaits these before rendering.
5. **Custom widgets are snapshots** — `BarcodeArCustomHighlight` and `BarcodeArCustomAnnotation` capture their `Widget` child as a still image. Animated widgets will not animate inside the AR overlay.
6. **Listener/provider ownership** — the BLoC owns `BarcodeArListener` and the scan logic; the `State` class implements `BarcodeArHighlightProvider` and `BarcodeArAnnotationProvider` because these interfaces receive `Barcode` instances and return view objects.
7. **Dispose cleanly** — call `barcodeAr.removeListener(this)` from the BLoC's `dispose()`, and invoke that from the `State.dispose()`. The native view tears itself down with the `State`.
8. **Camera permission** — iOS needs `NSCameraUsageDescription` in `Info.plist`. Android runtime permission is requested with `permission_handler`. Re-request on `AppLifecycleState.resumed` so the app recovers when the user grants permission from system settings.
9. **Camera lifecycle** — call `camera.switchToDesiredState(FrameSourceState.on/off)` from `didChangeAppLifecycleState` to pause scanning when the app goes to background.
10. **Symbologies** — only enable the ones the app actually needs. Each extra symbology increases tracking overhead.
11. **BarcodeArFilter** — `BarcodeArFilter` / `barcodeAr.setBarcodeFilter(...)` is documented for Flutter from SDK 8.5, but the latest **published** `scandit_flutter_datacapture_barcode` package is 8.4.0, where these symbols do not yet exist. Until an 8.5+ package ships on pub.dev, do **not** generate `BarcodeArFilter` code for Flutter — it will not compile. To limit what the SDK tracks on Flutter today, configure symbologies and properties on `BarcodeArSettings` instead.
