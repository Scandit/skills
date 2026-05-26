# Label Capture Flutter — Customization beyond the Validation Flow

Use this reference when the user needs visual control the Validation Flow can't offer, or wants to retrieve camera frames during scanning. The Validation Flow only exposes text strings (see `references/validation-flow.md`). Anything visual lives in one of two overlays below.

## Basic overlay — brushes for captured/predicted fields

`LabelCaptureBasicOverlay` draws colored outlines around detected labels and fields. It does **not** ship a validation/correction UI — you build that yourself with a `LabelCaptureListener`.

```dart
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';
import 'package:scandit_flutter_datacapture_label/scandit_flutter_datacapture_label.dart';

final overlay = LabelCaptureBasicOverlay.withLabelCaptureForView(labelCapture, view);

overlay.predictedFieldBrush = Brush(Color.fromHex('80FFC107'), Color.fromHex('FFC107'), 2);
overlay.capturedFieldBrush = Brush(Color.fromHex('8035B566'), Color.fromHex('35B566'), 2);
overlay.labelBrush = Brush(Color.fromHex('1A000000'), Color.fromHex('00000000'), 0);

overlay.shouldShowScanAreaGuides = true;

class _MyOverlayListener implements LabelCaptureBasicOverlayListener {
  @override
  Brush? brushForFieldOfLabel(
    LabelCaptureBasicOverlay overlay,
    LabelField field,
    CapturedLabel label,
  ) {
    return field.isRequired ? overlay.predictedFieldBrush : null;
  }

  @override
  Brush? brushForLabel(LabelCaptureBasicOverlay overlay, CapturedLabel label) => null;

  @override
  void didTapLabel(LabelCaptureBasicOverlay overlay, CapturedLabel label) {
    // Capture-time tap handler.
  }
}

overlay.listener = _MyOverlayListener();
```

Field state exposed on `LabelField`:
- `field.state`: `LabelFieldState` (`Captured`, `Predicted`, `Unvalidated`).
- `field.isRequired`: runtime read of whether the field was marked required (from `isOptional` / `numberOfMandatoryInstances`).
- `field.barcode` / `field.text` / `field.asDate()`: value accessors.

One-off brush overrides:

```dart
await overlay.setBrushForFieldOfLabel(brush, field, label);
await overlay.setBrushForLabel(brush, label);
```

## Advanced overlay — render arbitrary Flutter widgets on each captured label

Use `LabelCaptureAdvancedOverlay` for live AR overlays (a tag next to each detected field, an action button anchored to the label, a highlight ribbon, etc.). This is the recommended path when the customer's UI cannot be expressed with the Validation Flow.

```dart
final overlay = LabelCaptureAdvancedOverlay.withLabelCaptureForView(labelCapture, view);

class _MyAdvancedOverlayListener implements LabelCaptureAdvancedOverlayListener {
  @override
  Future<LabelCaptureAdvancedOverlayWidget?> widgetForCapturedLabel(
    LabelCaptureAdvancedOverlay overlay,
    CapturedLabel label,
  ) async {
    return LabelCaptureAdvancedOverlayWidget(
      child: Container(/* your widget tree */),
      width: 120,
      height: 32,
    );
  }

  @override
  Future<LabelCaptureAdvancedOverlayWidget?> widgetForCapturedLabelField(
    LabelCaptureAdvancedOverlay overlay,
    LabelField field,
    CapturedLabel label,
  ) async => null;

  @override
  Anchor anchorForCapturedLabel(LabelCaptureAdvancedOverlay overlay, CapturedLabel label) =>
      Anchor.topCenter;

  @override
  Anchor anchorForCapturedLabelField(
    LabelCaptureAdvancedOverlay overlay,
    LabelField field,
    CapturedLabel label,
  ) => Anchor.topCenter;

  @override
  PointWithUnit offsetForCapturedLabel(
    LabelCaptureAdvancedOverlay overlay,
    CapturedLabel label,
    LabelCaptureAdvancedOverlayWidget widget,
  ) => PointWithUnit(NumberWithUnit(0, MeasureUnit.dip), NumberWithUnit(0, MeasureUnit.dip));

  @override
  PointWithUnit offsetForCapturedLabelField(
    LabelCaptureAdvancedOverlay overlay,
    LabelField field,
    CapturedLabel label,
    LabelCaptureAdvancedOverlayWidget widget,
  ) => PointWithUnit(NumberWithUnit(0, MeasureUnit.dip), NumberWithUnit(-32, MeasureUnit.dip));
}

overlay.listener = _MyAdvancedOverlayListener();
```

Imperative API on the overlay:

```dart
await overlay.setWidgetForCapturedLabel(label, customWidget);
await overlay.setWidgetForCapturedLabelField(field, label, customWidget);
await overlay.setAnchorForCapturedLabel(label, Anchor.topCenter);
await overlay.setAnchorForCapturedLabelField(field, label, Anchor.topCenter);
await overlay.setOffsetForCapturedLabel(label, offset);
await overlay.setOffsetForCapturedLabelField(field, label, offset);
await overlay.clearCapturedLabelWidgets();
```

## Retrieving the camera frame during scanning ("image listener")

Both `LabelCaptureListener.didUpdateSession` and `LabelCaptureValidationFlowExtendedListener.didUpdateValidationFlowResult` receive a `getFrameData` callback. Call it to get the frame that produced the current update. This is the supported way to grab images while scanning — there is no separate "image listener" mode.

```dart
class _MyListener implements LabelCaptureListener {
  @override
  Future<void> didUpdateSession(
    LabelCapture labelCapture,
    LabelCaptureSession session,
    Future<FrameData?> Function() getFrameData,
  ) async {
    if (session.capturedLabels.isEmpty) return;
    final frame = await getFrameData();
    // `frame` carries the underlying image buffer / metadata.
    // Use it to upload, audit, or persist alongside the scan result.
  }
}

labelCapture.addListener(_MyListener());
```

Inside the Validation Flow, the same callback is available on `didUpdateValidationFlowResult` (via the **Extended** listener). Call it as early as possible inside the listener body — frame data is only retained for the current call.

## Custom feedback (sound / vibration on success)

```dart
final feedback = LabelCaptureFeedback.defaultFeedback;
feedback.success = Feedback(Vibration.defaultVibration, Sound.defaultSound);
labelCapture.feedback = feedback;
```
