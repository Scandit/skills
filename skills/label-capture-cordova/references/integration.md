# Label Capture Cordova Integration Guide

Label Capture (Smart Label Capture) extracts multiple fields from a single label in one scan — e.g. a barcode, an expiry date, and a total price on a grocery label.

## Prerequisites

- Scandit Cordova plugins installed:
  - `scandit-cordova-datacapture-core`
  - `scandit-cordova-datacapture-barcode`
  - `scandit-cordova-datacapture-label`
- After installing, run `cordova prepare ios` and `cordova prepare android`. For iOS, a fresh `pod install` inside `platforms/ios/` may be required.
- Cordova `>=11`, `cordova-ios >=6.2`, `cordova-android >=10`.
- A valid Scandit license key from <https://ssl.scandit.com>.
- Camera permissions:
  - iOS: `NSCameraUsageDescription` in `Info.plist` (or via `<config-file>` in `config.xml`).
  - Android: declared automatically by the plugin; request at runtime via `cordova.plugins.diagnostic` (or similar) if `minSdkVersion >= 23`.

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
   const expiry = new Scandit.ExpiryDateText('Expiry Date');
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
| Vehicle identification number (VIN) on a car / dashboard | `Scandit.LabelDefinition.createVinLabelDefinition('<name>')` |
| Retail price tag (price + unit price + weight) | `Scandit.LabelDefinition.createPriceCaptureDefinition('<name>')` — **not** compatible with the Validation Flow; see `references/validation-flow.md` |
| Seven-segment digital display (scales, meters, glucose monitors) | `Scandit.LabelDefinition.createSevenSegmentDisplayLabelDefinition('<name>')` |
| Full receipt (store name, line items, total) | Use `Scandit.LabelCaptureAdaptiveRecognitionOverlay` — different product path, requires ARE. See `references/adaptive-recognition.md`. |

**Pre-made labels are sealed.** Do NOT call `.addField(...)` or otherwise mutate the returned `LabelDefinition`. The schema is fixed native-side; mixing in custom fields is not supported. If the customer needs a hybrid (e.g. "VIN plus an inventory barcode"), build the whole definition manually with custom fields — do not modify a pre-made one.

If a pre-made label fits, **stop here** — skip Questions A/B/C and just instantiate the pre-made definition. Only proceed with the field-by-field interactive flow below when no pre-made label matches.

**Question A — What's on your label?** Show the field-type catalogue:

*Barcode fields:* `Scandit.CustomBarcode`, `Scandit.ImeiOneBarcode`, `Scandit.ImeiTwoBarcode`, `Scandit.PartNumberBarcode`, `Scandit.SerialNumberBarcode`.

*Text fields (preset recognisers):* `Scandit.ExpiryDateText`, `Scandit.PackingDateText`, `Scandit.DateText`, `Scandit.WeightText`, `Scandit.UnitPriceText`, `Scandit.TotalPriceText`.

*Text fields (custom):* `Scandit.CustomText` — any text, user provides a regex.

**Question B — For each selected field:**
- Required or optional? (required = label is not considered captured until this field matches.)
- Does the user need at least N instances of the same field matched before the label is considered captured? If so, set `field.numberOfMandatoryInstances = N`. Leave `null` (default) otherwise.
- For `CustomBarcode`: which **symbologies**? Mention to the user that enabling only the symbologies they actually need improves scanning performance and accuracy.
- For `CustomText` and date/text presets: what **value regex(es)** should the text match? Set via `field.valueRegexes = ['<pattern>']` (or `field.valueRegex = '<pattern>'` for a single pattern — the property is an array under the hood).
- Optionally, **anchor regex(es)** — context words near the value that help the SDK locate the field (e.g. `EXP:`, `Best before`, `LOT`). Set via `field.anchorRegexes = ['<pattern>']`. To reset/clear, assign an empty array: `field.anchorRegexes = []`. The presets ship with default anchor regexes — override only if the default doesn't match the customer's labels.

**Question C — Which file should the integration code go in?** (typically `www/js/index.js` for the default Cordova template). Then write the code directly into that file.

After writing the code, show this setup checklist:

1. `cordova plugin add scandit-cordova-datacapture-core scandit-cordova-datacapture-barcode scandit-cordova-datacapture-label`
2. `cordova prepare ios && cordova prepare android`
3. iOS: `cd platforms/ios && pod install`
4. Add `NSCameraUsageDescription` to `Info.plist` (or `<config-file>` in `config.xml`).
5. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with your key.

## Step 1 — Initialize DataCaptureContext (after `deviceready`)

All Scandit code must run after the `deviceready` event — the `Scandit.*` global is not populated before then.

```javascript
document.addEventListener('deviceready', () => {
  const context = Scandit.DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
  // …rest of setup below…
}, false);
```

`Scandit.DataCaptureContext.initialize(licenseKey)` returns the singleton context. Do **not** call it more than once and do **not** construct additional contexts.

## Step 2 — Define the label fields (class-based)

Field definitions on Cordova are class-based, same shape as RN/Capacitor. **Do not use builders or factory functions** — those are web-only.

```javascript
const barcode = Scandit.CustomBarcode.initWithNameAndSymbologies('Barcode', [
  Scandit.Symbology.EAN13UPCA,
  Scandit.Symbology.Code128,
]);
barcode.optional = false;

const expiry = new Scandit.ExpiryDateText('Expiry Date');
expiry.optional = false;
expiry.labelDateFormat = new Scandit.LabelDateFormat(Scandit.LabelDateComponentFormat.MDY, false);

const total = new Scandit.TotalPriceText('Total Price');
total.optional = true;

const labelDefinition = new Scandit.LabelDefinition('Perishable Product');
labelDefinition.fields = [barcode, expiry, total];
```

**Field constructors at a glance:**

| Field type | Constructor |
|---|---|
| `CustomBarcode` | `Scandit.CustomBarcode.initWithNameAndSymbologies(name, [Scandit.Symbology.X, ...])` |
| `ImeiOneBarcode` / `ImeiTwoBarcode` | `Scandit.ImeiOneBarcode.initWithNameAndSymbologies(name, [...])` |
| `PartNumberBarcode` / `SerialNumberBarcode` | `Scandit.SerialNumberBarcode.initWithNameAndSymbologies(name, [...])` |
| `ExpiryDateText` / `PackingDateText` / `DateText` | `new Scandit.ExpiryDateText(name)` (etc.) |
| `WeightText` / `UnitPriceText` / `TotalPriceText` | `new Scandit.WeightText(name)` (etc.) |
| `CustomText` | `new Scandit.CustomText(name)` then `field.valueRegex = '<pattern>'` |

## Step 3 — Build LabelCaptureSettings

```javascript
const settings = Scandit.LabelCaptureSettings.settingsFromLabelDefinitions([labelDefinition], {});
```

Do **not** use `LabelCaptureSettingsBuilder` — it does not exist on Cordova.

## Step 4 — Create the LabelCapture mode and bind it to the context

```javascript
const labelCapture = new Scandit.LabelCapture(settings);
context.setMode(labelCapture);
```

## Step 5 — Configure the recommended camera

```javascript
const cameraSettings = Scandit.LabelCapture.createRecommendedCameraSettings();
const camera = Scandit.Camera.default;
camera.applySettings(cameraSettings);
context.setFrameSource(camera);
```

## Step 6 — Embed `DataCaptureView` and add the overlay

The Cordova `DataCaptureView` connects to a DOM element you reserve for it.

```html
<!-- index.html -->
<div id="data-capture-view" style="position:fixed; inset:0;"></div>
```

```javascript
const view = Scandit.DataCaptureView.forContext(context);
view.connectToElement(document.getElementById('data-capture-view'));

const basicOverlay = new Scandit.LabelCaptureBasicOverlay(labelCapture);
view.addOverlay(basicOverlay);
```

## Step 7 — Validation Flow (recommended default)

`LabelCaptureValidationFlowOverlay` is the recommended default UX on Cordova — it ships the guided checklist, manual-entry sheet, and final-result callback so the customer doesn't have to build them. Render it **full-screen** (do not embed it inside a card / partial-height container).

`LabelCaptureValidationFlowListener` on Cordova is a **single interface with three required methods** (no base/Extended split). If the listener object omits a method, the runtime dispatcher throws when that event fires — provide empty bodies for callbacks you don't care about.

```javascript
const validationFlowOverlay = new Scandit.LabelCaptureValidationFlowOverlay(labelCapture);
validationFlowOverlay.listener = {
  didCaptureLabelWithFields(fields) {
    labelCapture.isEnabled = false;
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

view.addOverlay(validationFlowOverlay);
```

To customize the Validation Flow texts/placeholders (the only customization surface — colors, layout, fonts are **not** customizable), see `references/validation-flow.md`.

> **Listener naming.** On Cordova the methods are iOS-style: `didCaptureLabelWithFields`, `didSubmitManualInputForField`, `didUpdateValidationFlowResult`. Web names (`onValidationFlowLabelCaptured`, `onManualInput`) do not exist on Cordova.

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

## Step 9 — Lifecycle (pause/resume + cleanup)

Cordova fires `pause` and `resume` events on `document`:

```javascript
let wasOn = false;
document.addEventListener('pause', async () => {
  wasOn = (await camera.getCurrentState()) === Scandit.FrameSourceState.On;
  await camera.switchToDesiredState(Scandit.FrameSourceState.Off);
});
document.addEventListener('resume', async () => {
  if (wasOn) await camera.switchToDesiredState(Scandit.FrameSourceState.On);
});
```

Do **not** call `context.dispose()` — the singleton context lives for the entire app lifetime.

## Step 10 — Complete working example

```javascript
let labelCapture;

document.addEventListener('deviceready', () => {
  const context = Scandit.DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  const cameraSettings = Scandit.LabelCapture.createRecommendedCameraSettings();
  const camera = Scandit.Camera.default;
  camera.applySettings(cameraSettings);
  context.setFrameSource(camera);

  const barcode = Scandit.CustomBarcode.initWithNameAndSymbologies('Barcode', [
    Scandit.Symbology.EAN13UPCA,
    Scandit.Symbology.Code128,
  ]);
  barcode.optional = false;

  const expiry = new Scandit.ExpiryDateText('Expiry Date');
  expiry.optional = false;

  const total = new Scandit.TotalPriceText('Total Price');
  total.optional = true;

  const labelDefinition = new Scandit.LabelDefinition('Perishable Product');
  labelDefinition.fields = [barcode, expiry, total];

  const settings = Scandit.LabelCaptureSettings.settingsFromLabelDefinitions([labelDefinition], {});
  labelCapture = new Scandit.LabelCapture(settings);
  context.setMode(labelCapture);

  const view = Scandit.DataCaptureView.forContext(context);
  view.connectToElement(document.getElementById('data-capture-view'));

  const basicOverlay = new Scandit.LabelCaptureBasicOverlay(labelCapture);
  view.addOverlay(basicOverlay);

  const validationFlowOverlay = new Scandit.LabelCaptureValidationFlowOverlay(labelCapture);
  validationFlowOverlay.listener = {
    didCaptureLabelWithFields(fields) {
      labelCapture.isEnabled = false;
      showResult(formatLabelFields(fields));
    },
  };
  view.addOverlay(validationFlowOverlay);

  camera.switchToDesiredState(Scandit.FrameSourceState.On);
  labelCapture.isEnabled = true;
}, false);

function formatLabelFields(fields) {
  return fields
    .map((field) => {
      let value;
      if (field.barcode != null) value = field.barcode.data;
      else if (field.date != null) value = `${field.date.day}-${field.date.month}-${field.date.year}`;
      else if (field.text != null) value = field.text;
      else value = 'N/A';
      return `${field.name}: ${value}`;
    })
    .join('\n');
}

function showResult(text) {
  document.getElementById('modal-message').textContent = text;
  document.getElementById('result-modal').classList.remove('hidden');
}

function continueScan() {
  document.getElementById('result-modal').classList.add('hidden');
  if (labelCapture) labelCapture.isEnabled = true;
}
```

## Key Rules

- **`deviceready` first.** All Scandit code goes inside `document.addEventListener('deviceready', () => {...}, false)`.
- **Class-based field API only.** `Scandit.CustomBarcode.initWithNameAndSymbologies(...)`, `new Scandit.ExpiryDateText(name)`, `field.optional = true`, `Scandit.LabelCaptureSettings.settingsFromLabelDefinitions([...], {})`. No builders, no factory functions.
- **iOS-style listener names.** `didCaptureLabelWithFields`, `didSubmitManualInputForField` (8.2+), `didUpdateValidationFlowResult` (8.4+). Never `onValidationFlowLabelCaptured` / `onManualInput` (web).
- **Singleton context.** `Scandit.DataCaptureContext.initialize(licenseKey)` is called once. Never `dispose()` it.
- **DOM-anchored view.** `view.connectToElement(document.getElementById(...))`. Make sure the host `<div>` is sized.
- **License key in source is a placeholder** (`'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'`). Replace it before shipping.

## Where to Go Next

- [Label Definitions](https://docs.scandit.com/sdks/cordova/label-capture/label-definitions/)
- [Advanced Configurations](https://docs.scandit.com/sdks/cordova/label-capture/advanced/)
- [LabelCaptureSimpleSample (Cordova)](https://github.com/Scandit/datacapture-cordova-samples/tree/master/03_Advanced_Batch_Scanning_Samples/05_Smart_Label_Capture/LabelCaptureSimpleSample)
