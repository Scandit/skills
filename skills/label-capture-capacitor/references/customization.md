# Label Capture Capacitor — Customization beyond the Validation Flow

Use this reference when the user needs visual control the Validation Flow can't offer, or wants to retrieve camera frames during scanning. The Validation Flow only exposes text strings (see `references/validation-flow.md`). Anything visual lives in one of two overlays below.

## Basic overlay — brushes for captured/predicted fields

`LabelCaptureBasicOverlay` draws colored outlines around detected labels and fields. It does **not** ship a validation/correction UI — you build that yourself with a `LabelCaptureListener`.

```javascript
import { LabelCaptureBasicOverlay } from 'scandit-capacitor-datacapture-label';
import { Brush, Color } from 'scandit-capacitor-datacapture-core';

const overlay = new LabelCaptureBasicOverlay(labelCapture);

overlay.predictedFieldBrush = new Brush(Color.fromHex('80FFC107'), Color.fromHex('FFC107'), 2);
overlay.capturedFieldBrush = new Brush(Color.fromHex('8035B566'), Color.fromHex('35B566'), 2);
overlay.labelBrush = new Brush(Color.fromHex('1A000000'), Color.fromHex('00000000'), 0);

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

await view.addOverlay(overlay);
```

Field state is exposed on `LabelField`:
- `field.state`: `LabelFieldState` (e.g. `Captured`, `Predicted`, `Unvalidated`).
- `field.isRequired`: runtime read of whether the field was marked required (from `optional` / `numberOfMandatoryInstances`).
- `field.barcode` / `field.text` / `field.asDate()`: value accessors.

One-off brush overrides:

```javascript
await overlay.setBrushForFieldOfLabel(brush, field, label);
await overlay.setBrushForLabel(brush, label);
```

## Advanced overlay — render arbitrary native views on each captured label

Use `LabelCaptureAdvancedOverlay` for live AR overlays (a tag next to each detected field, an action button anchored to the label, a highlight ribbon, etc.). This is the recommended path when the customer's UI cannot be expressed with the Validation Flow.

```javascript
import { LabelCaptureAdvancedOverlay } from 'scandit-capacitor-datacapture-label';
import { Anchor, MeasureUnit, NumberWithUnit, PointWithUnit } from 'scandit-capacitor-datacapture-core';

const overlay = new LabelCaptureAdvancedOverlay(labelCapture);

overlay.listener = {
  viewForCapturedLabel(_overlay, _label) {
    // Return a LabelCaptureAdvancedOverlayView wrapper around a DOM element — or null.
    return null;
  },
  viewForCapturedLabelField(_overlay, _field, _label) {
    return null;
  },
  anchorForCapturedLabel(_overlay, _label) {
    return Anchor.Center;
  },
  anchorForCapturedLabelField(_overlay, _field, _label) {
    return Anchor.TopCenter;
  },
  offsetForCapturedLabel(_overlay, _label, _view) {
    return new PointWithUnit(
      new NumberWithUnit(0, MeasureUnit.DIP),
      new NumberWithUnit(0, MeasureUnit.DIP),
    );
  },
  offsetForCapturedLabelField(_overlay, _field, _label, _view) {
    return new PointWithUnit(
      new NumberWithUnit(0, MeasureUnit.DIP),
      new NumberWithUnit(-32, MeasureUnit.DIP),
    );
  },
};

await view.addOverlay(overlay);
```

Imperative API on the overlay:

```javascript
await overlay.setViewForCapturedLabel(label, customView);
await overlay.setViewForCapturedLabelField(field, label, customView);
await overlay.setAnchorForCapturedLabel(label, Anchor.TopCenter);
await overlay.setAnchorForCapturedLabelField(field, label, Anchor.TopCenter);
await overlay.setOffsetForCapturedLabel(label, offset);
await overlay.setOffsetForCapturedLabelField(field, label, offset);
await overlay.clearCapturedLabelViews();
```

Remember to toggle `view.webViewContentOnTop = true` whenever DOM-based custom views need to receive touch events.

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
import { LabelCaptureFeedback } from 'scandit-capacitor-datacapture-label';
import { Feedback, Sound, Vibration } from 'scandit-capacitor-datacapture-core';

const feedback = new LabelCaptureFeedback();
feedback.success = new Feedback(Vibration.defaultVibration, Sound.defaultSound);
labelCapture.feedback = feedback;
```
