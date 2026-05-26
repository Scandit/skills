# Label Capture Cordova — Customization beyond the Validation Flow

Use this reference when the user needs visual control the Validation Flow can't offer, or wants to retrieve camera frames during scanning. The Validation Flow only exposes text strings (see `references/validation-flow.md`). Anything visual lives in one of two overlays below.

## Basic overlay — brushes for captured/predicted fields

`LabelCaptureBasicOverlay` draws colored outlines around detected labels and fields. It does **not** ship a validation/correction UI — you build that yourself with a `LabelCaptureListener`.

```javascript
const overlay = new Scandit.LabelCaptureBasicOverlay(labelCapture);

overlay.predictedFieldBrush = new Scandit.Brush(Scandit.Color.fromHex('80FFC107'), Scandit.Color.fromHex('FFC107'), 2);
overlay.capturedFieldBrush = new Scandit.Brush(Scandit.Color.fromHex('8035B566'), Scandit.Color.fromHex('35B566'), 2);
overlay.labelBrush = new Scandit.Brush(Scandit.Color.fromHex('1A000000'), Scandit.Color.fromHex('00000000'), 0);

overlay.shouldShowScanAreaGuides = true;

overlay.listener = {
  brushForFieldOfLabel(_overlay, field, _label) {
    return field.isRequired ? overlay.predictedFieldBrush : null;
  },
  brushForLabel(_overlay, _label) {
    return null;
  },
  didTapLabel(_overlay, label) {
    // Capture-time tap handler.
  },
};

view.addOverlay(overlay);
```

Field state exposed on `LabelField`:
- `field.state`: `Scandit.LabelFieldState` (e.g. `Captured`, `Predicted`, `Unvalidated`).
- `field.isRequired`: runtime read of whether the field was marked required (from `optional` / `numberOfMandatoryInstances`).
- `field.barcode` / `field.text` / `field.asDate()`: value accessors.

One-off brush overrides:

```javascript
overlay.setBrushForFieldOfLabel(brush, field, label);
overlay.setBrushForLabel(brush, label);
```

## Advanced overlay — render arbitrary native views on each captured label

Use `LabelCaptureAdvancedOverlay` for live AR overlays (a tag next to each detected field, an action button anchored to the label, a highlight ribbon, etc.). This is the recommended path when the customer's UI cannot be expressed with the Validation Flow.

```javascript
const overlay = new Scandit.LabelCaptureAdvancedOverlay(labelCapture);

overlay.listener = {
  viewForCapturedLabel(_overlay, _label) {
    return null; // return a LabelCaptureAdvancedOverlayView wrapping a DOM element
  },
  viewForCapturedLabelField(_overlay, _field, _label) {
    return null;
  },
  anchorForCapturedLabel(_overlay, _label) {
    return Scandit.Anchor.Center;
  },
  anchorForCapturedLabelField(_overlay, _field, _label) {
    return Scandit.Anchor.TopCenter;
  },
  offsetForCapturedLabel(_overlay, _label, _view) {
    return new Scandit.PointWithUnit(
      new Scandit.NumberWithUnit(0, Scandit.MeasureUnit.DIP),
      new Scandit.NumberWithUnit(0, Scandit.MeasureUnit.DIP),
    );
  },
  offsetForCapturedLabelField(_overlay, _field, _label, _view) {
    return new Scandit.PointWithUnit(
      new Scandit.NumberWithUnit(0, Scandit.MeasureUnit.DIP),
      new Scandit.NumberWithUnit(-32, Scandit.MeasureUnit.DIP),
    );
  },
};

view.addOverlay(overlay);
```

Imperative API on the overlay:

```javascript
overlay.setViewForCapturedLabel(label, customView);
overlay.setViewForCapturedLabelField(field, label, customView);
overlay.setAnchorForCapturedLabel(label, Scandit.Anchor.TopCenter);
overlay.setAnchorForCapturedLabelField(field, label, Scandit.Anchor.TopCenter);
overlay.setOffsetForCapturedLabel(label, offset);
overlay.setOffsetForCapturedLabelField(field, label, offset);
overlay.clearCapturedLabelViews();
```

## Retrieving the camera frame during scanning ("image listener")

Both `LabelCaptureListener.didUpdateSession` and `LabelCaptureValidationFlowListener.didUpdateValidationFlowResult` receive a `getFrameData` callback. Call it to get the frame that produced the current update. This is the supported way to grab images while scanning — there is no separate "image listener" mode.

```javascript
labelCapture.addListener({
  async didUpdateSession(_mode, session, getFrameData) {
    if (session.capturedLabels.length === 0) return;
    const frame = await getFrameData();
    // `frame` carries the underlying image buffer / metadata.
    // Use it to upload, audit, or persist alongside the scan result.
  },
});
```

Inside the Validation Flow, the same callback is available on `didUpdateValidationFlowResult`. Call it as early as possible inside the listener body — frame data is only retained for the current call.

## Custom feedback (sound / vibration on success)

```javascript
const feedback = new Scandit.LabelCaptureFeedback();
feedback.success = new Scandit.Feedback(Scandit.Vibration.defaultVibration, Scandit.Sound.defaultSound);
labelCapture.feedback = feedback;
```
