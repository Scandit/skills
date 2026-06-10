# Label Capture Flutter Integration Guide

Label Capture (Smart Label Capture) extracts multiple fields from a single label in one scan — e.g. a barcode, an expiry date, and a total price on a grocery label. You declare the structure of the label (which fields, required/optional, barcode symbologies or text regex) and the SDK returns all matched fields per frame.

## Prerequisites

- Scandit Flutter packages added to `pubspec.yaml`:
  - `scandit_flutter_datacapture_core`
  - `scandit_flutter_datacapture_barcode`
  - `scandit_flutter_datacapture_label`
- Flutter `>=3.10`, Dart `>=3.0`. iOS deployment target `>=14.0`. Android `minSdkVersion >=23`.
- A valid Scandit license key:
  - Sign in at <https://ssl.scandit.com> to generate one.
  - No account yet? Sign up at <https://ssl.scandit.com/dashboard/sign-up?p=test>.
- Camera permissions configured by the app:
  - iOS: add `NSCameraUsageDescription` to `ios/Runner/Info.plist`.
  - Android: the manifest permission is declared by the plugin; request it at runtime with `permission_handler` (or equivalent) before pushing the scan screen.

## Recognition Limits

Before defining fields, sanity-check whether Smart Label Capture can read the customer's labels at all. These limits apply to **text** fields (barcodes are not subject to them).

- **Supported character set**: ``0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz ()-./:,$¶"`` — digits, Latin upper/lower case, and a small set of punctuation. **Diacritics (é, ñ, ü, etc.), accented letters, and non-Latin scripts (CJK, Cyrillic, Arabic, etc.) are not in the supported set.** If the customer's labels contain characters outside this set, Smart Label Capture is not the right tool for those fields.
- **Handwriting is not supported.** Only printed text. There is no partial-support path — if the field value is handwritten, the OCR will not read it.
- **Capture conditions matter**: glare, motion blur, low contrast, and oblique angles all degrade recognition. There is no documented minimum font size or contrast threshold — recommend the customer test with their actual labels.

If the customer needs handwriting recognition, non-Latin scripts, or characters outside the supported set, surface the limit explicitly before writing code rather than letting them discover it after integration.

## Language Coverage for Pre-Made Text Fields

The pre-made text fields ship with **default anchor regexes (`anchorRegexes`) in English, German, and French**. These cover the contextual keywords used to locate the value on the label (e.g. `EXP`, `Verfallsdatum`, `À consommer avant`):

| Field | Out-of-the-box languages |
|---|---|
| `ExpiryDateText` | EN / DE / FR |
| `PackingDateText` | EN / DE / FR |
| `UnitPriceText` | EN / DE / FR |
| `TotalPriceText` | EN / DE / FR |
| `WeightText` | EN / DE / FR |
| `DateText` | Generic — no language-specific anchors (used when no specific date type fits). |
| Barcode fields (`SerialNumberBarcode`, `PartNumberBarcode`, `ImeiOneBarcode`, `ImeiTwoBarcode`) | Not language-bound — they match barcode symbologies and the data they encode. |

**If the customer's labels are in another language** (Italian, Spanish, Polish, Portuguese, etc.), they have two options:
1. **Override the anchor regex(es)** on the preset field builder with localized keywords:
   ```dart
   final expiry = ExpiryDateTextBuilder()
       .setAnchorRegexes(['Scadenza', 'Da consumarsi entro', 'Caducidad']) // Italian / Spanish
       .isOptional(false)
       .build('Expiry Date');
   ```
   This keeps the preset's value-recognition logic (date parsing, price parsing, etc.) and only swaps the localization layer.
2. **Rebuild from scratch with `CustomText`** — set both `anchorRegexes` and `valueRegexes` manually. Use this when the preset's value pattern itself doesn't match the customer's label format.

Option 1 is preferred when the only mismatch is the keyword language; option 2 when the value format also differs (e.g. dot-separated dates vs. slash-separated, comma decimals vs. dot decimals).

## Interactive Label Definition

Before writing any code, walk the user through their label. Ask one question at a time.

**Question 0 — Is this one of the pre-made label types?** Before defining individual fields, check whether the SDK already ships a complete `LabelDefinition` for this use case. If yes, use it directly — the schema is baked in native-side.

| Use case | How |
|---|---|
| Vehicle identification number (VIN) on a car / dashboard | `LabelDefinition.vinLabelDefinitionWithName('<name>')` |
| Retail price tag (price + unit price + weight) | `LabelDefinition.priceCaptureDefinitionWithName('<name>')` — **not** compatible with the Validation Flow; see `references/validation-flow.md` |
| Seven-segment digital display (scales, meters, glucose monitors) | `LabelDefinition.sevenSegmentDisplayLabelDefinitionWithName('<name>')` |
| Full receipt (store name, line items, total) | Use `LabelCaptureAdaptiveRecognitionOverlay` — different product path, requires ARE. See `references/adaptive-recognition.md`. |

**Pre-made label definitions are sealed.** The three pre-built definitions — `priceCaptureDefinitionWithName(...)`, `vinLabelDefinitionWithName(...)`, and `sevenSegmentDisplayLabelDefinitionWithName(...)` — return a fixed `LabelDefinition` whose schema is baked in native-side. They expose **no** `addField`/`addCustomBarcode`/`addX` methods and cannot be extended with custom fields; do NOT try to mutate the returned object. If the customer needs a **hybrid** (e.g. "VIN plus an inventory barcode"), build the whole definition from scratch with `LabelDefinitionBuilder().addX(...)` using custom + pre-built *fields* — do not modify a pre-made definition.

If a pre-made label fits, **stop here** — skip Questions A/B/C and just instantiate the pre-made definition. Only proceed with the field-by-field interactive flow below when no pre-made label matches.

**Question A — What's on your label?** Present this checklist of supported field types:

*Barcode fields:* `CustomBarcode`, `ImeiOneBarcode`, `ImeiTwoBarcode`, `PartNumberBarcode`, `SerialNumberBarcode`.

*Text fields (preset recognisers):* `ExpiryDateText`, `PackingDateText`, `DateText`, `WeightText`, `UnitPriceText`, `TotalPriceText`.

*Text fields (custom):* `CustomText` — any text, user provides a regex.

**Question B — For each selected field:**
- Required or optional? (required = label is not considered captured until this field matches.)
- `LabelField.numberOfMandatoryInstances` is a **read-only** property on Flutter (there is no builder setter for it — do not invent `setNumberOfMandatoryInstances`). Express required/optional purely via `.isOptional(false)` / `.isOptional(true)`.
- For `CustomBarcode`: which **symbologies**? Mention to the user that enabling only the symbologies they actually need improves scanning performance and accuracy.
- For `CustomText` and date/text presets: what **value regex(es)** should the text match? Set via `.setValueRegexes(['<p1>', '<p2>'])` — on Flutter the value setter is the **list** form (`setValueRegexes`); there is no singular `setValueRegex` String setter. Calling it **overrides** the preset's default value patterns.
- Optionally, **anchor regex(es)** — context words near the value that help the SDK locate the field (e.g. `EXP:`, `Best before`, `LOT`). Set via `.setAnchorRegexes(['<keyword>', ...])` (list of strings) or `.setAnchorRegex(Regex('<pattern>'))` (a single Dart `Regex`). Use `.resetAnchorRegexes()` to clear the preset's default anchors and rely on the value regex alone. The presets ship with default anchor regexes — override only if the default doesn't match the customer's labels.

**Question C — Which file should the integration code go in?** Then write the code directly into that file.

After writing the code, show this setup checklist:

1. Add the Scandit packages to `pubspec.yaml` and run `flutter pub get`.
2. iOS: open `ios/Runner.xcworkspace`, set deployment target to 14.0+, add `NSCameraUsageDescription` to `Info.plist`. Then `cd ios && pod install`.
3. Android: confirm `minSdkVersion 23` in `android/app/build.gradle`. The `CAMERA` permission is declared automatically; runtime request via `permission_handler` is your responsibility.
4. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with your key from <https://ssl.scandit.com>.

## Step 1 — Initialize the plugins and the DataCaptureContext

The Flutter plugins each ship a one-time `initialize()` that wires the underlying MethodChannels. **It must run before any Scandit API call**, including `DataCaptureContext.initialize(licenseKey)`.

```dart
import 'package:flutter/material.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_label/scandit_flutter_datacapture_label.dart';

const licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ScanditFlutterDataCaptureBarcode.initialize();
  await ScanditFlutterDataCaptureLabel.initialize();
  DataCaptureContext.initialize(licenseKey);
  runApp(const MyApp());
}
```

`DataCaptureContext.sharedInstance` is the singleton accessor used everywhere else.

## Step 2 — Define the label fields (builder API on Flutter)

On Flutter, fields and the label definition use **builders**. Do **not** use class-based constructors here — that pattern is for RN/Cordova/Capacitor.

```dart
final customBarcode = CustomBarcodeBuilder()
    .setSymbologies({Symbology.ean13Upca, Symbology.code128})
    .isOptional(false)
    .build('Barcode');

final expiryDate = ExpiryDateTextBuilder()
    .isOptional(false)
    .build('Expiry Date');

final totalPrice = TotalPriceTextBuilder()
    .isOptional(true)
    .build('Total Price');

final labelDefinition = LabelDefinitionBuilder()
    .addCustomBarcode(customBarcode)
    .addExpiryDateText(expiryDate)
    .addTotalPriceText(totalPrice)
    .build('Perishable Product');
```

**Builders at a glance** (each `.build(name)` returns the field instance):

| Field type | Builder |
|---|---|
| `CustomBarcode` | `CustomBarcodeBuilder().setSymbologies({...}).isOptional(...).build(name)` |
| `ImeiOneBarcode` / `ImeiTwoBarcode` | `ImeiOneBarcodeBuilder().isOptional(...).build(name)` |
| `PartNumberBarcode` / `SerialNumberBarcode` | `SerialNumberBarcodeBuilder().setSymbologies({...}).build(name)` |
| `ExpiryDateText` / `PackingDateText` / `DateText` | `ExpiryDateTextBuilder().isOptional(...).build(name)` |
| `WeightText` / `UnitPriceText` / `TotalPriceText` | `TotalPriceTextBuilder().isOptional(...).build(name)` |
| `CustomText` | `CustomTextBuilder().setValueRegexes(['<pattern>']).build(name)` |

`LabelDefinitionBuilder` exposes one `addX` method per field type (`addCustomBarcode`, `addExpiryDateText`, `addTotalPriceText`, …). Call `.build('<label name>')` to produce the `LabelDefinition`.

### Value regexes vs. anchor regexes

Two distinct regex roles control text-field recognition:

- **`valueRegexes`** — match the actual field **value** (the date, price, lot code, …). Set with `.setValueRegexes(['<pattern>', ...])` (list form; there is no singular `setValueRegex` String setter on Flutter). Required for `CustomText`; preset fields ship with sensible defaults that calling this **overrides**. Keep these patterns standard — the SDK regex engine does **not** support lookahead/lookbehind (`(?=…)`, `(?<=…)`) or backreferences (see the note below).
- **`anchorRegexes`** — match the **contextual keyword** printed near the value (e.g. `EXP`, `BBE`, `Best before`, `LOT`). They disambiguate when several fields share the same value format (e.g. an expiry date and a packaging date both `dd/mm/yyyy`). Set with `.setAnchorRegexes(['<keyword>', ...])` (list of strings) or `.setAnchorRegex(Regex('<pattern>'))` (single Dart `Regex`).

When the customer's label has **no keyword** next to the value, clear the preset's default anchors with `.resetAnchorRegexes()` and let the value regex do the work:

```dart
final expiry = ExpiryDateTextBuilder()
    .resetAnchorRegexes()                 // no 'EXP'/'BBE' keyword on this label
    .setValueRegexes([r'\d{2}/\d{2}/\d{4}'])
    .isOptional(false)
    .build('Expiry Date');
```

To pin a specific keyword instead (e.g. a label that prints `BBE` and also a packaging date):

```dart
final bestBefore = ExpiryDateTextBuilder()
    .setAnchorRegexes(['BBE', 'Best before'])
    .build('Best Before');
```

`CustomText` is the last-resort builder — use it only when no preset field type fits. It requires both `valueRegexes` and (optionally) `anchorRegexes`:

```dart
final lot = CustomTextBuilder()
    .setAnchorRegexes(['LOT'])
    .setValueRegexes([r'[A-Z0-9]{6,}'])
    .isOptional(true)
    .build('Lot Number');
```

> **Regex engine limits.** The SDK's regex engine supports standard character classes, quantifiers, alternation, and groups only. It does **not** support lookahead/lookbehind assertions (`(?=…)`, `(?<=…)`), backreferences, or Unicode property escapes. Keep patterns simple.

## Step 3 — Build LabelCaptureSettings

```dart
final settings = LabelCaptureSettings([labelDefinition]);
```

The `LabelCaptureSettings` constructor takes a `List<LabelDefinition>` directly. There is also `LabelCaptureSettingsBuilder` if you prefer; either is fine on Flutter.

## Step 4 — Create the LabelCapture mode and bind it to the context

```dart
final context = DataCaptureContext.sharedInstance;
final labelCapture = LabelCapture.forContext(context, settings);
```

`forContext` adds the mode to the context in one call. (You can also use `LabelCapture(settings)` followed by `context.addMode(labelCapture)`.)

## Step 5 — Configure the recommended camera

```dart
final camera = Camera.defaultCamera;
if (camera == null) throw StateError('Failed to initialize camera!');
camera.applySettings(LabelCapture.createRecommendedCameraSettings());
context.setFrameSource(camera);
await camera.switchToDesiredState(FrameSourceState.on);
```

`Camera.defaultCamera` is the documented accessor for the default (world-facing) camera and is **nullable** — guard it before use. `LabelCapture.createRecommendedCameraSettings()` is a **method** on Flutter (there is no `recommendedCameraSettings` property — that form is iOS/Android-only). Switch the camera on with `switchToDesiredState(FrameSourceState.on)` and off with `FrameSourceState.off`.

## Step 6 — Embed the `DataCaptureView` widget

```dart
class _ScanScreenState extends State<ScanScreen> {
  late final DataCaptureView _view;

  @override
  void initState() {
    super.initState();
    _view = DataCaptureView.forContext(DataCaptureContext.sharedInstance);
    // Add overlays (Step 7) here, after the view is constructed.
  }

  @override
  Widget build(BuildContext context) => Scaffold(body: _view);
}
```

## Step 7 — Validation Flow (recommended default)

`LabelCaptureValidationFlowOverlay` is the recommended default UX. It ships the guided field checklist, manual-entry sheet, and final-result callback — features the customer would otherwise have to build themselves on top of `LabelCaptureBasicOverlay`. Render it **full-screen** (do not embed it inside a card / partial-height container). To customize the texts (the only customization surface — colors, layout, fonts are **not** customizable), see `references/validation-flow.md`.

```dart
class _ScanScreenState extends State<ScanScreen>
    implements LabelCaptureValidationFlowExtendedListener {
  late final LabelCaptureValidationFlowOverlay _overlay;

  @override
  void initState() {
    super.initState();
    _overlay = LabelCaptureValidationFlowOverlay.withLabelCaptureForView(
      _labelCapture,
      _view,
    );
    _overlay.listener = this;
  }

  @override
  void didCaptureLabelWithFields(List<LabelField> fields) {
    // Final result for one label, after the user has confirmed any required corrections.
  }

  @override
  void didSubmitManualInputForField(LabelField field, String? oldValue, String newValue) {
    // Fires when the user manually enters or corrects a field value (8.2+).
  }

  @override
  Future<void> didUpdateValidationFlowResult(
    LabelResultUpdateType type,
    int asyncId,
    List<LabelField> fields,
    Future<FrameData?> Function() getFrameData,
  ) async {
    // 8.4+ optional. Implement only for fine-grained progress feedback during capture.
  }
}
```

> **Listener interfaces.**
> - `LabelCaptureValidationFlowListener` — base interface, declares only `didCaptureLabelWithFields`. Implement this if you only need the final result.
> - `LabelCaptureValidationFlowExtendedListener` — extends the base; adds `didSubmitManualInputForField` (8.2+) and `didUpdateValidationFlowResult` (8.4+). Implement this if you want the manual-input or progress callbacks.

> **Listener naming.** On Flutter the methods are iOS-style: `didCaptureLabelWithFields`, `didSubmitManualInputForField`, `didUpdateValidationFlowResult`. Web names (`onValidationFlowLabelCaptured`, `onManualInput`) do not exist on Flutter.

## Step 8 — Result handling without the Validation Flow

Use this path only when the customer needs a live AR overlay or a custom UI the Validation Flow can't produce (otherwise stick with Step 7). The `getFrameData` argument is the supported hook for retrieving the camera frame during scanning ("image listener") — call it inside the callback to get the frame that produced the update.

If you only use `LabelCaptureBasicOverlay`, attach a `LabelCaptureListener` to the mode:

```dart
class _ScanScreenState extends State<ScanScreen> implements LabelCaptureListener {
  @override
  void didUpdateSession(LabelCapture mode, LabelCaptureSession session, Future<FrameData?> Function() getFrameData) {
    for (final captured in session.capturedLabels) {
      for (final field in captured.fields) {
        final value = field.barcode?.data ?? field.text;
        debugPrint('${field.name} = $value');
        // For dates, you can also call field.asDate().
      }
    }
  }
}

_labelCapture.addListener(this);
```

Add `LabelCaptureBasicOverlay.withLabelCaptureForView(_labelCapture, _view);` in `initState`.

## Step 9 — Lifecycle (WidgetsBindingObserver + dispose)

```dart
class _ScanScreenState extends State<ScanScreen> with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _camera?.switchToDesiredState(FrameSourceState.on);
      _labelCapture.isEnabled = true;
    } else if (state == AppLifecycleState.paused) {
      _camera?.switchToDesiredState(FrameSourceState.off);
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _labelCapture.removeListener(this);
    _overlay.listener = null;
    super.dispose();
  }
}
```

Do **not** call `DataCaptureContext.dispose()` — the singleton context lives for the entire app lifetime.

## Step 10 — Complete working example

```dart
import 'package:flutter/material.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_label/scandit_flutter_datacapture_label.dart';

const licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ScanditFlutterDataCaptureBarcode.initialize();
  await ScanditFlutterDataCaptureLabel.initialize();
  DataCaptureContext.initialize(licenseKey);
  runApp(const MaterialApp(home: ScanScreen()));
}

class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key});
  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen>
    with WidgetsBindingObserver
    implements LabelCaptureValidationFlowExtendedListener {
  late final DataCaptureContext _context;
  late final Camera? _camera;
  late final LabelCapture _labelCapture;
  late final DataCaptureView _view;
  late final LabelCaptureValidationFlowOverlay _overlay;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _context = DataCaptureContext.sharedInstance;

    _camera = Camera.defaultCamera;
    _camera?.applySettings(LabelCapture.createRecommendedCameraSettings());
    _context.setFrameSource(_camera);

    final barcode = CustomBarcodeBuilder()
        .setSymbologies({Symbology.ean13Upca, Symbology.code128})
        .isOptional(false)
        .build('Barcode');
    final expiry = ExpiryDateTextBuilder().isOptional(false).build('Expiry Date');
    final total = TotalPriceTextBuilder().isOptional(true).build('Total Price');
    final definition = LabelDefinitionBuilder()
        .addCustomBarcode(barcode)
        .addExpiryDateText(expiry)
        .addTotalPriceText(total)
        .build('Perishable Product');

    final settings = LabelCaptureSettings([definition]);
    _labelCapture = LabelCapture.forContext(_context, settings);

    _view = DataCaptureView.forContext(_context);
    _overlay = LabelCaptureValidationFlowOverlay.withLabelCaptureForView(_labelCapture, _view);
    _overlay.listener = this;

    _camera?.switchToDesiredState(FrameSourceState.on);
    _labelCapture.isEnabled = true;
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _camera?.switchToDesiredState(FrameSourceState.on);
      _labelCapture.isEnabled = true;
    } else if (state == AppLifecycleState.paused) {
      _camera?.switchToDesiredState(FrameSourceState.off);
    }
  }

  @override
  void didCaptureLabelWithFields(List<LabelField> fields) {
    final body = fields
        .map((f) => '${f.name}: ${f.barcode?.data ?? f.text ?? 'N/A'}')
        .join('\n');
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('LABEL CAPTURED'),
        content: Text(body),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              _camera?.switchToDesiredState(FrameSourceState.on);
              _labelCapture.isEnabled = true;
            },
            child: const Text('CONTINUE'),
          ),
        ],
      ),
    );
  }

  @override
  void didSubmitManualInputForField(LabelField field, String? oldValue, String newValue) {}

  @override
  Future<void> didUpdateValidationFlowResult(
    LabelResultUpdateType type,
    int asyncId,
    List<LabelField> fields,
    Future<FrameData?> Function() getFrameData,
  ) async {}

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _overlay.listener = null;
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(body: _view);
}
```

## Key Rules

- **Builder API on Flutter.** `CustomBarcodeBuilder().setSymbologies({...}).isOptional(...).build(name)`, `LabelDefinitionBuilder().addX(...).build(name)`, `LabelCaptureSettings([definition])`. RN/Cordova/Capacitor are class-based — do not mix.
- **Plugin initialization required.** `await ScanditFlutterDataCaptureLabel.initialize();` (and `…Barcode.initialize()`) must run before `DataCaptureContext.initialize(licenseKey)`.
- **iOS-style listener names.** `didCaptureLabelWithFields`, `didSubmitManualInputForField` (8.2+), `didUpdateValidationFlowResult` (8.4+). Never `onValidationFlowLabelCaptured` / `onManualInput` (web).
- **Two listener interfaces.** `LabelCaptureValidationFlowListener` (capture only) vs. `LabelCaptureValidationFlowExtendedListener` (capture + manual-input + result-update).
- **Singleton context.** Always `DataCaptureContext.initialize(licenseKey)` once and access via `DataCaptureContext.sharedInstance`. Never `dispose()` it.
- **Lifecycle via `WidgetsBindingObserver`.** Pause/resume the camera in `didChangeAppLifecycleState`; clear listeners in `dispose()`.
- **License key in source is a placeholder** (`'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'`). Replace it before shipping.

## Troubleshooting common failures

When the user reports a problem, map the symptom to its cause before suggesting code changes. The most common failures are environmental, not API misuse.

- **Black / blank camera preview, no error** — almost always the camera permission was never granted, or the camera was never switched on. Check that (1) on iOS `NSCameraUsageDescription` is in `ios/Runner/Info.plist` and the OS prompt was accepted; on Android the runtime `CAMERA` permission is requested and granted with `permission_handler` (or equivalent) **before** the scan screen is pushed; (2) `camera.switchToDesiredState(FrameSourceState.on)` runs after permission is granted; and (3) `Camera.defaultCamera` did not return `null` (it is nullable — guard it) and `context.setFrameSource(camera)` was called.

- **Camera preview shows but nothing is ever captured** — verify the `LabelCaptureBasicOverlay` (or a Validation Flow overlay) was attached to the `DataCaptureView`, that `labelCapture.isEnabled` is `true`, and that the mode was not left disabled after a previous capture (re-enable with `labelCapture.isEnabled = true`). Confirm the `LabelDefinitionBuilder().addX(...).build(name)` chain actually added fields (a definition with no fields never captures) and that the barcode field enables the symbologies actually printed on the label.

- **Text / OCR fields never match (expiry date, total price, custom text, etc.) but the barcode reads fine** — the barcode reading correctly is the tell: **barcode-only fields (e.g. `CustomBarcode`, `SerialNumberBarcode`) do NOT need the on-device text models**, so a working barcode plus empty text fields points squarely at a missing text-models module. Text, price, and date/semantic *text* fields **do** require them: `ScanditLabelCaptureText` is needed for arbitrary text/date fields and `ScanditPriceLabel` for price fields (unit price / total price). Both ship with the `scandit_flutter_datacapture_label` package, so confirm it is in `pubspec.yaml` and `flutter pub get` was re-run, and that `await ScanditFlutterDataCaptureLabel.initialize();` ran before `DataCaptureContext.initialize(licenseKey)`.

- **A field never matches even though the text is on the label** — the value regex or anchor regex is too strict. Prefer the preset builder field (its regexes are tuned) over a hand-written custom-text field. If the label has no keyword near the value, clear the anchors (pass an empty anchor-regex list) and rely on the value regex alone. Keep regexes simple — lookahead/lookbehind are not supported and silently fail to match.

- **Handwritten or non-Latin text is never read** — expected. Label Capture reads **printed text** in the supported Latin character set only (see Recognition Limits above). Use the Validation Flow's manual-entry sheet so the user can type the value when it cannot be scanned.

## Where to Go Next

- [Label Definitions](https://docs.scandit.com/sdks/flutter/label-capture/label-definitions/) — full catalogue of pre-built field types and how to tune their regex anchors and value patterns.
- [Advanced Configurations](https://docs.scandit.com/sdks/flutter/label-capture/advanced/) — Validation Flow customisation, adaptive recognition, custom overlays.
- [LabelCaptureSimpleSample (Flutter)](https://github.com/Scandit/datacapture-flutter-samples/tree/master/03_Advanced_Batch_Scanning_Samples/05_Smart_Label_Capture/LabelCaptureSimpleSample) — working reference sample.
