# Label Capture React Native — Customization beyond the Validation Flow

Use this reference when the user needs visual control the Validation Flow can't offer, or wants to retrieve camera frames during scanning. The Validation Flow only exposes text strings (see `references/validation-flow.md`). Anything visual lives in one of two overlays below.

## Basic overlay — brushes for captured/predicted fields

`LabelCaptureBasicOverlay` draws colored outlines around detected labels and fields. It does **not** ship a validation/correction UI — you build that yourself with a `LabelCaptureListener`.

```typescript
import {
  LabelCaptureBasicOverlay,
  type LabelCaptureBasicOverlayListener,
} from 'scandit-react-native-datacapture-label';
import { Brush, Color } from 'scandit-react-native-datacapture-core';

const overlay = new LabelCaptureBasicOverlay(labelCapture);

// Default brushes applied to all detected labels/fields:
overlay.predictedFieldBrush = new Brush(Color.fromHex('80FFC107'), Color.fromHex('FFC107'), 2);
overlay.capturedFieldBrush = new Brush(Color.fromHex('8035B566'), Color.fromHex('35B566'), 2);
overlay.labelBrush = new Brush(Color.fromHex('1A000000'), Color.fromHex('00000000'), 0);

overlay.shouldShowScanAreaGuides = true;

// Per-instance brush overrides (return null to use the defaults):
const listener: LabelCaptureBasicOverlayListener = {
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
overlay.listener = listener;

view.addOverlay(overlay);
```

Field state is exposed on `LabelField`:
- `field.state`: `LabelFieldState` (e.g. `Captured`, `Predicted`, `Unvalidated`).
- `field.isRequired`: runtime read of whether the field was marked required (from `optional` / `numberOfMandatoryInstances`).
- `field.barcode` / `field.text` / `field.asDate()`: value accessors.

You can also set a one-off brush imperatively:

```typescript
await overlay.setBrushForFieldOfLabel(brush, field, label);
await overlay.setBrushForLabel(brush, label);
```

## Advanced overlay — render arbitrary native views on each captured label

Use `LabelCaptureAdvancedOverlay` for live AR overlays (a tag next to each detected field, an action button anchored to the label, a highlight ribbon, etc.). This is the recommended path when the customer's UI cannot be expressed with the Validation Flow.

```typescript
import {
  LabelCaptureAdvancedOverlay,
  type LabelCaptureAdvancedOverlayListener,
} from 'scandit-react-native-datacapture-label';
import { Anchor, MeasureUnit, NumberWithUnit, PointWithUnit } from 'scandit-react-native-datacapture-core';

const overlay = new LabelCaptureAdvancedOverlay(labelCapture);

const listener: LabelCaptureAdvancedOverlayListener = {
  viewForCapturedLabel(_overlay, _label) {
    // Return a LabelCaptureAdvancedOverlayView (an RN view wrapper) — or null.
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
overlay.listener = listener;

view.addOverlay(overlay);
```

Imperative API on the overlay (call from anywhere after the overlay is attached):

```typescript
await overlay.setViewForCapturedLabel(label, customView);
await overlay.setViewForCapturedLabelField(field, label, customView);
await overlay.setAnchorForCapturedLabel(label, Anchor.TopCenter);
await overlay.setAnchorForCapturedLabelField(field, label, Anchor.TopCenter);
await overlay.setOffsetForCapturedLabel(label, offset);
await overlay.setOffsetForCapturedLabelField(field, label, offset);
await overlay.clearCapturedLabelViews();
```

## Retrieving the camera frame during scanning ("image listener")

Both `LabelCaptureListener.didUpdateSession` and `LabelCaptureValidationFlowListener.didUpdateValidationFlowResult` receive a `getFrameData: () => Promise<FrameData | null>` callback. Call it to get the frame that produced the current update. This is the supported way to grab images while scanning — there is no separate "image listener" mode.

```typescript
import type { LabelCaptureListener, LabelCaptureSession } from 'scandit-react-native-datacapture-label';
import type { FrameData } from 'scandit-react-native-datacapture-core';

const listener: LabelCaptureListener = {
  async didUpdateSession(
    _mode,
    session: LabelCaptureSession,
    getFrameData: () => Promise<FrameData | null>,
  ) {
    if (session.capturedLabels.length === 0) return;
    const frame = await getFrameData();
    // `frame` carries the underlying image buffer / metadata.
    // Use it to upload, audit, or persist alongside the scan result.
  },
};

labelCapture.addListener(listener);
```

Inside the Validation Flow, the same callback is available on `didUpdateValidationFlowResult`. Call it as early as possible inside the listener body — frame data is only retained for the current call.

## Custom feedback (sound / vibration on success)

```typescript
import { LabelCaptureFeedback } from 'scandit-react-native-datacapture-label';
import { Feedback, Sound, Vibration } from 'scandit-react-native-datacapture-core';

const feedback = new LabelCaptureFeedback();
feedback.success = new Feedback(Vibration.defaultVibration, Sound.defaultSound);
labelCapture.feedback = feedback;
```
