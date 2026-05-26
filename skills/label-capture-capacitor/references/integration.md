# Label Capture Capacitor Integration Guide

Label Capture (Smart Label Capture) extracts multiple fields from a single label in one scan — e.g. a barcode, an expiry date, and a total price on a grocery label.

## Prerequisites

- Scandit Capacitor packages installed:
  - `scandit-capacitor-datacapture-core`
  - `scandit-capacitor-datacapture-barcode`
  - `scandit-capacitor-datacapture-label`
- After installing, run `npx cap sync` and `cd ios/App && pod install` for iOS.
- Capacitor `>=5`, `@capacitor/ios >=5`, `@capacitor/android >=5`.
- A valid Scandit license key from <https://ssl.scandit.com>.
- Camera permissions:
  - iOS: `NSCameraUsageDescription` in `ios/App/App/Info.plist`.
  - Android: declared automatically by the plugin; request at runtime if `minSdkVersion >= 23`.

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
1. **Override the anchor regex(es)** on the preset field with localized keywords:
   ```javascript
   const expiry = new ExpiryDateText('Expiry Date');
   expiry.anchorRegexes = ['Scadenza', 'Da consumarsi entro', 'Caducidad']; // Italian / Spanish
   ```
   This keeps the preset's value-recognition logic (date parsing, price parsing, etc.) and only swaps the localization layer.
2. **Rebuild from scratch with `CustomText`** — set both `anchorRegexes` and `valueRegexes` manually. Use this when the preset's value pattern itself doesn't match the customer's label format.

Option 1 is preferred when the only mismatch is the keyword language; option 2 when the value format also differs (e.g. dot-separated dates vs. slash-separated, comma decimals vs. dot decimals).

## Interactive Label Definition

Before writing any code, walk the user through their label. Ask one question at a time.

**Question 0 — Is this one of the pre-made label types?** Before defining individual fields, check whether the SDK already ships a complete `LabelDefinition` for this use case. If yes, use it directly — the schema is baked in native-side.

| Use case | How |
|---|---|
| Vehicle identification number (VIN) on a car / dashboard | `LabelDefinition.createVinLabelDefinition('<name>')` |
| Retail price tag (price + unit price + weight) | `LabelDefinition.createPriceCaptureDefinition('<name>')` — **not** compatible with the Validation Flow; see `references/validation-flow.md` |
| Seven-segment digital display (scales, meters, glucose monitors) | `LabelDefinition.createSevenSegmentDisplayLabelDefinition('<name>')` |
| Full receipt (store name, line items, total) | Use `LabelCaptureAdaptiveRecognitionOverlay` — different product path, requires ARE. See `references/adaptive-recognition.md`. |

**Pre-made labels are sealed.** Do NOT call `.addField(...)` or otherwise mutate the returned `LabelDefinition`. The schema is fixed native-side; mixing in custom fields is not supported. If the customer needs a hybrid (e.g. "VIN plus an inventory barcode"), build the whole definition manually with custom fields — do not modify a pre-made one.

If a pre-made label fits, **stop here** — skip Questions A/B/C and just instantiate the pre-made definition. Only proceed with the field-by-field interactive flow below when no pre-made label matches.

**Question A — What's on your label?** Show the field-type catalogue:

*Barcode fields:* `CustomBarcode`, `ImeiOneBarcode`, `ImeiTwoBarcode`, `PartNumberBarcode`, `SerialNumberBarcode`.

*Text fields (preset recognisers):* `ExpiryDateText`, `PackingDateText`, `DateText`, `WeightText`, `UnitPriceText`, `TotalPriceText`.

*Text fields (custom):* `CustomText` — any text, user provides a regex.

**Question B — For each selected field:**
- Required or optional? (required = label is not considered captured until this field matches.)
- Does the user need at least N instances of the same field matched before the label is considered captured? If so, set `field.numberOfMandatoryInstances = N`. Leave `null` (default) otherwise.
- For `CustomBarcode`: which **symbologies**? Mention to the user that enabling only the symbologies they actually need improves scanning performance and accuracy.
- For `CustomText` and date/text presets: what **value regex(es)** should the text match? Set via `field.valueRegexes = ['<pattern>']` (or `field.valueRegex = '<pattern>'` for a single pattern — note the property is an array under the hood).
- Optionally, **anchor regex(es)** — context words near the value that help the SDK locate the field (e.g. `EXP:`, `Best before`, `LOT`). Set via `field.anchorRegexes = ['<pattern>']`. To reset/clear, assign an empty array: `field.anchorRegexes = []`. The presets ship with default anchor regexes — override only if the default doesn't match the customer's labels.

**Question C — Which file should the integration code go in?** Then write the code directly into that file.

After writing the code, show this setup checklist:

1. `npm install scandit-capacitor-datacapture-core scandit-capacitor-datacapture-barcode scandit-capacitor-datacapture-label`
2. `npx cap sync`
3. iOS: `cd ios/App && pod install`. Add `NSCameraUsageDescription` to `Info.plist`.
4. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with your key.

## Step 1 — Initialize plugins, then the DataCaptureContext

```javascript
import { ScanditCaptureCorePlugin, DataCaptureContext } from 'scandit-capacitor-datacapture-core';

async function runApp() {
  await ScanditCaptureCorePlugin.initializePlugins();
  const context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
  // …rest of setup below…
}

runApp();
```

`initializePlugins()` wires the underlying Capacitor bridge. **It must run before any other Scandit API call**, including `DataCaptureContext.initialize`.

## Step 2 — Define the label fields (class-based)

Field definitions on Capacitor are class-based, same shape as RN/Cordova. **Do not use builders or factory functions** — those are web-only.

```javascript
import { Symbology } from 'scandit-capacitor-datacapture-barcode';
import {
  CustomBarcode,
  ExpiryDateText,
  TotalPriceText,
  LabelDefinition,
} from 'scandit-capacitor-datacapture-label';

const barcode = CustomBarcode.initWithNameAndSymbologies('Barcode', [
  Symbology.EAN13UPCA,
  Symbology.Code128,
]);
barcode.optional = false;

const expiry = new ExpiryDateText('Expiry Date');
expiry.optional = false;

const total = new TotalPriceText('Total Price');
total.optional = true;

const labelDefinition = new LabelDefinition('Perishable Product');
labelDefinition.fields = [barcode, expiry, total];
```

**Field constructors at a glance:**

| Field type | Constructor |
|---|---|
| `CustomBarcode` | `CustomBarcode.initWithNameAndSymbologies(name, [Symbology.X, ...])` |
| `ImeiOneBarcode` / `ImeiTwoBarcode` | `ImeiOneBarcode.initWithNameAndSymbologies(name, [...])` |
| `PartNumberBarcode` / `SerialNumberBarcode` | `SerialNumberBarcode.initWithNameAndSymbologies(name, [...])` |
| `ExpiryDateText` / `PackingDateText` / `DateText` | `new ExpiryDateText(name)` (etc.) |
| `WeightText` / `UnitPriceText` / `TotalPriceText` | `new WeightText(name)` (etc.) |
| `CustomText` | `new CustomText(name)` then `field.valueRegex = '<pattern>'` |

## Step 3 — Build LabelCaptureSettings

```javascript
import { LabelCaptureSettings } from 'scandit-capacitor-datacapture-label';

const settings = LabelCaptureSettings.settingsFromLabelDefinitions([labelDefinition], {});
```

Do **not** use `LabelCaptureSettingsBuilder` — it does not exist on Capacitor.

## Step 4 — Create the LabelCapture mode and bind it to the context

```javascript
import { LabelCapture } from 'scandit-capacitor-datacapture-label';

const labelCapture = new LabelCapture(settings);
context.setMode(labelCapture);
```

## Step 5 — Configure the recommended camera

```javascript
import { Camera, FrameSourceState } from 'scandit-capacitor-datacapture-core';

const camera = Camera.withSettings(LabelCapture.createRecommendedCameraSettings());
context.setFrameSource(camera);
```

## Step 6 — Embed `DataCaptureView` and add the overlay

```html
<!-- index.html -->
<div id="data-capture-view" style="position:fixed; inset:0;"></div>
```

```javascript
import { DataCaptureView } from 'scandit-capacitor-datacapture-core';
import { LabelCaptureBasicOverlay } from 'scandit-capacitor-datacapture-label';

const view = DataCaptureView.forContext(context);
view.connectToElement(document.getElementById('data-capture-view'));

const basicOverlay = new LabelCaptureBasicOverlay(labelCapture);
await view.addOverlay(basicOverlay);

// Native scan UI is BEHIND the WebView. While scanning, let the native overlays receive touches:
view.webViewContentOnTop = false;
```

## Step 7 — Validation Flow (recommended default)

`LabelCaptureValidationFlowOverlay` is the recommended default UX on Capacitor — it ships the guided checklist, manual-entry sheet, and final-result callback so the customer doesn't have to build them. Render it **full-screen** (do not embed it inside a card / partial-height container).

`LabelCaptureValidationFlowListener` on Capacitor is a **single interface with three required methods** (no base/Extended split). If the listener object omits a method, the runtime dispatcher throws when that event fires — provide empty bodies for callbacks you don't care about.

```javascript
import { LabelCaptureValidationFlowOverlay } from 'scandit-capacitor-datacapture-label';

const validationFlowOverlay = new LabelCaptureValidationFlowOverlay(labelCapture);

validationFlowOverlay.listener = {
  didCaptureLabelWithFields(fields) {
    labelCapture.isEnabled = false;
    // Show DOM modal on top of the native view:
    view.webViewContentOnTop = true;
    showResult(fields);
  },

  didSubmitManualInputForField(field, oldValue, newValue) {
    // Fires whenever the user manually enters or corrects a field value.
    // Leave the body empty if you don't need this signal.
  },

  async didUpdateValidationFlowResult(type, asyncId, fields, getFrameData) {
    // Fires multiple times during capture as fields accumulate.
    // Call `await getFrameData()` here to retrieve the camera frame
    // that produced this partial result (image upload / auditing).
    // Leave the body empty if you don't need progress feedback.
  },
};

await view.addOverlay(validationFlowOverlay);
```

To customize the Validation Flow texts/placeholders (the only customization surface — colors, layout, fonts are **not** customizable), see `references/validation-flow.md`.

> **Listener naming.** On Capacitor the methods are iOS-style: `didCaptureLabelWithFields`, `didSubmitManualInputForField`, `didUpdateValidationFlowResult`. Web names (`onValidationFlowLabelCaptured`, `onManualInput`) do not exist on Capacitor.

> **`webViewContentOnTop` toggle.** Set to `false` while scanning so the native overlay receives touches. Set to `true` whenever you show DOM-based UI (modal, alert) over the scan view. Toggle back to `false` when resuming scanning.

## Step 8 — Result handling without the Validation Flow

Use this path only when the customer needs a live AR overlay or a custom UI the Validation Flow can't produce (otherwise stick with Step 7).

Attach a `LabelCaptureListener` to the mode. The `getFrameData` argument on `didUpdateSession` is the supported hook for retrieving the camera frame during scanning ("image listener"):

```javascript
labelCapture.addListener({
  async didUpdateSession(_mode, session, getFrameData) {
    if (session.capturedLabels.length === 0) return;
    for (const captured of session.capturedLabels) {
      for (const field of captured.fields) {
        const value = field.barcode?.data ?? field.text;
        console.log(`${field.name} = ${value}`);
      }
    }
    // Optionally: const frame = await getFrameData(); to grab the image
    // that produced this update. Only valid for the duration of the callback.
  },
});
```

For brushes, advanced overlays, and the full image-listener pattern, see `references/customization.md`.

## Step 9 — Lifecycle (App pause/resume + cleanup)

Use the `App` plugin from Capacitor to handle background/foreground transitions:

```javascript
import { App } from '@capacitor/app';

let wasOn = false;
App.addListener('appStateChange', async ({ isActive }) => {
  if (!isActive) {
    wasOn = (await camera.getCurrentState()) === FrameSourceState.On;
    await camera.switchToDesiredState(FrameSourceState.Off);
  } else if (wasOn) {
    await camera.switchToDesiredState(FrameSourceState.On);
  }
});
```

Do **not** call `context.dispose()` — the singleton context lives for the entire app lifetime.

## Step 10 — Complete working example

```javascript
import { Camera, DataCaptureContext, DataCaptureView, FrameSourceState, ScanditCaptureCorePlugin } from 'scandit-capacitor-datacapture-core';
import { Symbology } from 'scandit-capacitor-datacapture-barcode';
import {
  CustomBarcode,
  ExpiryDateText,
  LabelCapture,
  LabelCaptureBasicOverlay,
  LabelCaptureSettings,
  LabelCaptureValidationFlowOverlay,
  LabelDefinition,
  TotalPriceText,
} from 'scandit-capacitor-datacapture-label';

let labelCapture;

async function runApp() {
  await ScanditCaptureCorePlugin.initializePlugins();
  const context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  const camera = Camera.withSettings(LabelCapture.createRecommendedCameraSettings());
  context.setFrameSource(camera);

  const barcode = CustomBarcode.initWithNameAndSymbologies('Barcode', [
    Symbology.EAN13UPCA,
    Symbology.Code128,
  ]);
  barcode.optional = false;

  const expiry = new ExpiryDateText('Expiry Date');
  expiry.optional = false;

  const total = new TotalPriceText('Total Price');
  total.optional = true;

  const labelDefinition = new LabelDefinition('Perishable Product');
  labelDefinition.fields = [barcode, expiry, total];

  const settings = LabelCaptureSettings.settingsFromLabelDefinitions([labelDefinition], {});
  labelCapture = new LabelCapture(settings);
  context.setMode(labelCapture);

  const view = DataCaptureView.forContext(context);
  view.connectToElement(document.getElementById('data-capture-view'));

  const basicOverlay = new LabelCaptureBasicOverlay(labelCapture);
  await view.addOverlay(basicOverlay);

  const validationFlowOverlay = new LabelCaptureValidationFlowOverlay(labelCapture);
  validationFlowOverlay.listener = {
    didCaptureLabelWithFields(fields) {
      labelCapture.isEnabled = false;
      view.webViewContentOnTop = true;
      showResult(formatLabelFields(fields));
    },
    didSubmitManualInputForField() {},
    async didUpdateValidationFlowResult() {},
  };
  await view.addOverlay(validationFlowOverlay);

  view.webViewContentOnTop = false;
  await camera.switchToDesiredState(FrameSourceState.On);
  labelCapture.isEnabled = true;
}

function formatLabelFields(fields) {
  return fields
    .map((f) => {
      const value = f.barcode?.data ?? (f.date ? `${f.date.day}-${f.date.month}-${f.date.year}` : f.text ?? 'N/A');
      return `${f.name}: ${value}`;
    })
    .join('\n');
}

function showResult(text) {
  document.getElementById('modal-message').textContent = text;
  document.getElementById('result-modal').classList.remove('hidden');
}

runApp();
```

## Key Rules

- **`initializePlugins()` first.** Always `await ScanditCaptureCorePlugin.initializePlugins()` before `DataCaptureContext.initialize(licenseKey)`.
- **`webViewContentOnTop` toggle.** `false` while scanning (so native overlays receive touches), `true` when showing DOM modals.
- **Class-based field API only.** `CustomBarcode.initWithNameAndSymbologies(...)`, `new ExpiryDateText(name)`, `field.optional = true`, `LabelCaptureSettings.settingsFromLabelDefinitions([...], {})`. No builders, no factory functions.
- **iOS-style listener names.** `didCaptureLabelWithFields`, `didSubmitManualInputForField` (8.2+), `didUpdateValidationFlowResult` (8.4+). Never `onValidationFlowLabelCaptured` / `onManualInput` (web).
- **Singleton context.** `DataCaptureContext.initialize(licenseKey)` once. Never `dispose()` it.
- **License key in source is a placeholder** (`'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'`).

## Where to Go Next

- [Label Definitions](https://docs.scandit.com/sdks/capacitor/label-capture/label-definitions/)
- [Advanced Configurations](https://docs.scandit.com/sdks/capacitor/label-capture/advanced/)
- [LabelCaptureSimpleSample (Capacitor)](https://github.com/Scandit/datacapture-capacitor-samples/tree/master/03_Advanced_Batch_Scanning_Samples/05_Smart_Label_Capture/LabelCaptureSimpleSample)
