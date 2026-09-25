# Label Capture Web Integration Guide

Label Capture (Smart Label Capture) extracts multiple fields from a single label in one scan — e.g. a barcode, an expiry date, and a total price on a grocery label. You declare the structure of the label (which fields, required/optional, barcode symbologies or text regex) and the SDK returns all matched fields per frame.

> **Label Capture reads printed text only.** Handwritten text is not supported.

## Starting from zero? Use the pre-built sample

If the user has no existing app yet, offer the official sample as the fastest path to a working integration — it already has the correct project structure, dependencies, and best practices in place:

- **LabelCaptureSimpleSample:** <https://github.com/Scandit/datacapture-web-samples/tree/master/03_Advanced_Batch_Scanning_Samples/05_Smart_Label_Capture/LabelCaptureSimpleSample>

Tell the user to clone the repo and open the sample folder. Once they have it open, help them:

1. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with their key from <https://ssl.scandit.com>
2. Adjust the label definition to match their use case (fields, symbologies, regex patterns)
3. Run `npm install` (or their package manager of choice) and start the app

Only proceed to the manual integration steps below if the user already has an existing project they need to add Label Capture to.

---

## Prerequisites

- Scandit Data Capture SDK for web — install three npm packages with your user's package manager (npm, pnpm, or yarn):
  - `@scandit/web-datacapture-core`
  - `@scandit/web-datacapture-barcode`
  - `@scandit/web-datacapture-label`
- A valid Scandit license key:
  - Sign in at <https://ssl.scandit.com> to generate one.
  - No account yet? Sign up at <https://ssl.scandit.com/dashboard/sign-up?p=test>.

## Interactive Label Definition

Before writing any code, walk the user through their label. Ask one question at a time.

**Question A — What's on your label?** Present this checklist of supported field types and ask the user to pick everything that applies.

> **Always prefer pre-built field builders over custom ones.** If the user's use case matches a pre-built type (e.g. expiry date, weight, price), use that builder — it ships with tuned regex patterns and anchor text optimised for that field type. Only reach for `CustomTextBuilder` when no pre-built type covers the field, and only use `CustomBarcodeBuilder` when none of the pre-built barcode types (`ImeiOneBarcodeBuilder`, `PartNumberBarcodeBuilder`, etc.) apply.

*Barcode fields:*

- `CustomBarcodeBuilder` — any barcode, user chooses symbologies
- `ImeiOneBarcodeBuilder` — IMEI 1 (typically for smartphone boxes)
- `ImeiTwoBarcodeBuilder` — IMEI 2
- `PartNumberBarcodeBuilder` — part number
- `SerialNumberBarcodeBuilder` — serial number

*Text fields (preset recognisers):*

- `ExpiryDateTextBuilder` — expiry date (with configurable date format)
- `PackingDateTextBuilder` — packing date
- `DateTextBuilder` — generic date
- `WeightTextBuilder` — weight
- `UnitPriceTextBuilder` — unit price
- `TotalPriceTextBuilder` — total price

> **Language limitation:** predefined text field builders have hardcoded anchor keyword values in **English, French, and German** only (e.g. "EXP", "BBE", "DLC", "Poids", "Gewicht"). If the label uses anchor text in another language, the predefined builder will not match it — use `CustomTextBuilder` with a custom `anchorRegex` instead.

*Text fields (custom):*

- `CustomTextBuilder` — any text, user provides a regex. Supports any language since both `anchorRegex` and `valueRegex` are fully user-defined.

**Question B — For each selected field:**

- Is it **required** or **optional**?
  - **Required** (default): the label is not considered captured until this field is successfully read. In the Validation Flow, a required field also blocks the user from completing the flow — they must either scan it or type it in manually before the `onValidationFlowLabelCaptured` callback fires.
  - **Optional**: the field is captured if found, but its absence does not block capture or the Validation Flow submission. The user can complete the flow without it.
- For `CustomBarcodeBuilder`: which **symbologies**? Mention to the user that enabling only the symbologies they actually need improves scanning performance and accuracy.
- For `CustomTextBuilder`: what **regex pattern** should the text match?

**Question C — What scanning experience do you need?**

| Option | When to use |
|---|---|
| **Validation Flow** *(recommended)* | The user wants a guided scanning experience: the SDK shows which fields have been captured and which are still missing, lets users manually type a value when OCR fails, and confirms the result before handing it back. Best for most production integrations. |
| **Basic Overlay** | Fully automated scanning with no confirmation step. The app processes results as soon as all required fields match, with no chance for the user to review or correct. Use when the label is very clean and OCR accuracy is not a concern. |
| **Advanced Overlay** | The app needs fully custom AR rendering — drawing its own overlays on top of the camera feed with full control over position, style, and animations. Only choose this if Basic Overlay and Validation Flow are not flexible enough visually. |

Default to recommending Validation Flow unless the user explicitly says they do not want a confirmation step or need a fully custom AR experience.

> **VIN and price label use cases with the Validation Flow:** The web SDK ships ready-made `LabelDefinition.createVinLabelDefinition(name)` and `LabelDefinition.createPriceCaptureDefinition(name)` definitions (see **Pre-built Label Definitions** below). These pre-made definitions are **not compatible with the Validation Flow overlay** — use them only with the Basic Overlay. If the user specifically wants VIN or price capture *inside the Validation Flow*, build the label by hand with custom field builders (`CustomBarcodeBuilder` + `CustomTextBuilder`) instead; the builder API gives full control over the fields the Validation Flow can render.

**Question D — Which file should the integration code go in?** Then write the code directly into that file. Do not just show it in chat.

## Minimal Integration (Web)

Once the user has answered Questions A, B, and C, generate the integration code using the class-builder API. This form works across all shipped 8.x versions. Substitute the placeholders `[LABEL_NAME]`, `[FIELD_NAME]`, and the correct field builders based on the user's answers. Fields marked optional should call `.isOptional(true)`; required fields can omit the call (required is the default) or call `.isOptional(false)` explicitly for clarity.

```typescript
import { Symbology } from "@scandit/web-datacapture-barcode";
import { Camera, DataCaptureContext, DataCaptureView, FrameSourceState } from "@scandit/web-datacapture-core";
import {
  CustomBarcodeBuilder,
  ExpiryDateTextBuilder,
  LabelCapture,
  LabelCaptureBasicOverlay,
  LabelCaptureSettingsBuilder,
  LabelDefinitionBuilder,
  labelCaptureLoader,
  type LabelCaptureSession,
  type LabelField,
} from "@scandit/web-datacapture-label";

async function run() {
  const view = new DataCaptureView();
  view.connectToElement(document.getElementById("data-capture-view")!);

  const context = await DataCaptureContext.forLicenseKey(
    "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
    {
      libraryLocation: new URL("self-hosted-scandit-sdc-lib", document.baseURI).toString(),
      moduleLoaders: [labelCaptureLoader()],
    }
  );
  await view.setContext(context);

  const camera = Camera.pickBestGuess();
  await context.setFrameSource(camera);
  await camera.applySettings(LabelCapture.createRecommendedCameraSettings());
  await camera.switchToDesiredState(FrameSourceState.On);

  const settings = await new LabelCaptureSettingsBuilder()
    .addLabel(
      await new LabelDefinitionBuilder()
        .addCustomBarcode(
          await new CustomBarcodeBuilder()
            .setSymbologies([Symbology.EAN13UPCA, Symbology.Code128])
            .isOptional(false)
            .build("Barcode")
        )
        .addExpiryDateText(
          await new ExpiryDateTextBuilder()
            .isOptional(false)
            .build("Expiry Date")
        )
        .build("Perishable Product")
    )
    .build();

  const mode = await LabelCapture.forContext(context, settings);

  await LabelCaptureBasicOverlay.withLabelCaptureForView(mode, view);

  const labelCaptureListener = {
    didUpdateSession: (_labelCapture, session: LabelCaptureSession, _frameData) => {
      for (const capturedLabel of session.capturedLabels) {
        for (const field of capturedLabel.fields as LabelField[]) {
          console.log(field.name, "=", field.barcode?.data ?? field.text);
        }
      }
    },
  };
  mode.addListener(labelCaptureListener);

  async function cleanup() {
    mode.removeListener(labelCaptureListener);
    await DataCaptureContext.sharedInstance.frameSource?.switchToDesiredState(FrameSourceState.Off);
  }

  return cleanup;
}

run();
```

## anchorRegex vs valueRegex

Every text field definition has two kinds of regex:

- **`anchorRegex`** — identifies the *context* of the field on the label. It matches the keyword or phrase near the value (e.g. `"EXP"`, `"BBE"`, `"Best Before"`). The SDK uses this to locate which part of the label contains this field, especially when multiple fields could otherwise match the same value pattern.
- **`valueRegex`** — validates the *content* of the field. It matches the actual data to extract (e.g. `"\\d{2}/\\d{2}/\\d{4}"` for a date).

**Pre-built field builders ship with default anchor and value regexes** tuned for their field type and the supported languages (English, French, German). You can override them with `setAnchorRegex(pattern)` / `setAnchorRegexes([...])` and `setValueRegex(pattern)` / `setValueRegexes([...])`.

**Resetting the anchorRegex** — available only on pre-built field builders, not on `CustomTextBuilder`. Call `resetAnchorRegexes()` to remove all default anchor patterns and let the SDK rely solely on the `valueRegex` for detection. Use this when the label has no consistent anchor keyword near the field:

```typescript
await new ExpiryDateTextBuilder()
  .resetAnchorRegexes()
  .setValueRegex("\\d{2}/\\d{2}/\\d{4}")
  .build("Expiry Date")
```

**Keep regexes simple.** The SDK regex engine supports standard character classes (`\d`, `[A-Z]`), quantifiers (`{2}`, `+`, `*`), and groups. Lookahead and lookbehind assertions are not supported and will cause the pattern to fail to match.

## Notes when generating this code

- Import ONLY the field builders the user actually selected (`CustomBarcodeBuilder`, `ExpiryDateTextBuilder`, etc.). Do not import unused ones.
- The corresponding `addXxx` method on `LabelDefinitionBuilder` mirrors the field type: `addCustomBarcode`, `addExpiryDateText`, `addWeightText`, `addUnitPriceText`, `addTotalPriceText`, `addCustomText`, `addPackingDateText`, `addDateText`, `addImeiOneBarcode`, `addImeiTwoBarcode`, `addPartNumberBarcode`, `addSerialNumberBarcode`.
- For `CustomBarcodeBuilder`, use `setSymbologies([...])` with the symbologies the user selected. For a single symbology, `setSymbology(Symbology.X)` is also valid.
- For `CustomTextBuilder`, use `.setValueRegex(pattern)` (or `.setValueRegexes([patterns])` for multiple). Do not use `.setPattern` or `.setPatterns` — those names were renamed in v8.1 and no longer exist.
- Do NOT use the factory-function sugar (`label(...)`, `customBarcode(...)`, `labelCaptureSettings()`) — that shorthand is only guaranteed from v8.5. The class-builder form above works on all 8.x versions.

## Setup Checklist

After writing the integration code, show this checklist:

1. Install the three npm packages with the user's package manager (npm, pnpm, or yarn):
   - `@scandit/web-datacapture-core`
   - `@scandit/web-datacapture-barcode`
   - `@scandit/web-datacapture-label`
2. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your license key from <https://ssl.scandit.com>.
3. Make sure `libraryLocation` points to a self-hosted copy of the SDK library (the path in `new URL(...)`). You can copy the `sdc-lib` directory from `node_modules/@scandit/web-datacapture-label/sdc-lib/`, or use the CDN instead: `libraryLocation: "https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-label@8/sdc-lib/"`.
4. Ensure a DOM element with id `data-capture-view` exists on the page before `run()` executes. The element must have a defined size and be visible — `DataCaptureView` renders the camera feed into it, so if the element has zero dimensions or `display: none` the viewfinder will not appear. A common setup is `width: 100%; height: 100vh;` or any other CSS that gives the element a non-zero area.

## Overlay Integration

### Validation Flow (recommended default)

The Validation Flow gives users a guided scanning experience: a persistent checklist shows which fields have been captured and which are still missing, and users can manually type a value when OCR fails. It handles partial captures across multiple package surfaces and confirms the result before returning it to the app. **Use this for most production integrations.**

> **The Validation Flow must be implemented full screen.** The `data-capture-view` element must cover the full viewport. Do not embed the Validation Flow inside a card, modal, or partial-screen widget — it will not work correctly. The entire page/screen should be dedicated to the scanning experience for the duration of the capture.

**Before writing Validation Flow code, determine the user's SDK version.** Prefer reading `package.json` for `@scandit/web-datacapture-label`. If that is unreadable or missing, ask: "Which version of `@scandit/web-datacapture-label` are you on?" Then write the version-matched block below — write only one, not both.

### v8.2+ — Redesigned Validation Flow

Import the Validation Flow classes and replace the `LabelCaptureBasicOverlay` line in the minimal integration with the Validation Flow overlay. Replace the existing `mode.addListener` block with the redesigned listener.

```typescript
import {
  LabelCaptureValidationFlowOverlay,
  LabelCaptureValidationFlowSettings,
  type LabelCaptureValidationFlowListener,
  type LabelField,
} from "@scandit/web-datacapture-label";

const overlay = await LabelCaptureValidationFlowOverlay.withLabelCaptureForView(mode, view);

const validationFlowSettings = await LabelCaptureValidationFlowSettings.create();
await validationFlowSettings.setPlaceholderTextForLabelDefinition("Expiry Date", "MM.DD.YY");
await validationFlowSettings.setPlaceholderTextForLabelDefinition("Total Price", "e.g., $13.66");
await overlay.applySettings(validationFlowSettings);

overlay.listener = {
  onManualInput: (_field: LabelField, _oldValue: string | undefined, _newValue: string) => {
    // User manually entered or corrected a value for a field.
  },
  onValidationFlowLabelCaptured: (fields: LabelField[]) => {
    for (const field of fields) {
      console.log(field.name, "=", field.barcode?.data ?? field.text);
    }
  },
} satisfies LabelCaptureValidationFlowListener;
```

The setter methods `setRequiredFieldErrorText`, `setMissingFieldsHintText`, and `setManualInputButtonText` still exist in 8.2.x for backward compatibility, but they are deprecated — they have no effect in the redesigned UI. Do not call them for new v8.2+ integrations. Use `setPlaceholderTextForLabelDefinition` (and other new methods on `LabelCaptureValidationFlowSettings`) for customisation.

### v8.1 and earlier — Original Validation Flow

On v8.1 the listener interface has **only** `onValidationFlowLabelCaptured` — `onManualInput` did not exist yet (it was added in v8.2). Customise the flow via async setter methods on `LabelCaptureValidationFlowSettings`. There is **no** `setPlaceholderTextForLabelDefinition` in 8.1 — that method was added in v8.2.

```typescript
import {
  LabelCaptureValidationFlowOverlay,
  LabelCaptureValidationFlowSettings,
  type LabelCaptureValidationFlowListener,
  type LabelField,
} from "@scandit/web-datacapture-label";

const overlay = await LabelCaptureValidationFlowOverlay.withLabelCaptureForView(mode, view);

const validationFlowSettings = await LabelCaptureValidationFlowSettings.create();
await validationFlowSettings.setRequiredFieldErrorText("This field is required");
await validationFlowSettings.setMissingFieldsHintText("Please fill the missing fields");
await validationFlowSettings.setManualInputButtonText("Enter manually");
await overlay.applySettings(validationFlowSettings);

overlay.listener = {
  onValidationFlowLabelCaptured: (fields: LabelField[]) => {
    for (const field of fields) {
      console.log(field.name, "=", field.barcode?.data ?? field.text);
    }
  },
} satisfies LabelCaptureValidationFlowListener;
```

If the user plans to upgrade to v8.2+, route them to the migration guide (`migration.md` §2) for the listener change (`onManualInput` becomes required) and the optional switch to `setPlaceholderTextForLabelDefinition`.

### Validation Flow customization

The Validation Flow is a **fully managed UI component**. Scandit owns the layout, colors, button styles, and branding. This is intentional — the VF provides a battle-tested, accessible scanning experience without requiring the integrator to design or maintain the UI.

**What you can customize** (via `LabelCaptureValidationFlowSettings`):

| What | API | Version |
|---|---|---|
| Placeholder text shown inside a field input (e.g. expected format hint) | `setPlaceholderTextForLabelDefinition(fieldName, placeholder)` | v8.2+ |
| Text of the manual-input button | `setManualInputButtonText(text)` | v8.1 only (deprecated in v8.2, no effect) |
| Error message shown when a required field is missing | `setRequiredFieldErrorText(text)` | v8.1 only (deprecated in v8.2, no effect) |
| Hint shown when optional fields are absent | `setMissingFieldsHintText(text)` | v8.1 only (deprecated in v8.2, no effect) |

**What you cannot customize**: colors, button styles, layout, fonts, spacing, branding, or any visual aspect of the VF panel. If a customer asks to change these, explain that the VF is a managed component and these are not exposed. If they need full visual control, they should use `LabelCaptureAdvancedOverlay` and build their own UI — but that comes with significantly more implementation cost.

**Customizing field highlighting on the camera feed (brushes):** Even when using the Validation Flow, you can add a `LabelCaptureBasicOverlay` alongside it to control how detected fields are highlighted in the live camera view. The VF manages the panel UI; the Basic Overlay manages the AR highlight brushes. Add both:

```typescript
const vfOverlay = await LabelCaptureValidationFlowOverlay.withLabelCaptureForView(mode, view);
const basicOverlay = await LabelCaptureBasicOverlay.withLabelCaptureForView(mode, view);
```

Store both references — they can be removed from the view later with `view.removeOverlay(vfOverlay)` / `view.removeOverlay(basicOverlay)`. Then attach a `LabelCaptureBasicOverlayListener` to the basic overlay to customize brushes per field and per label (see the Basic Overlay section below).

Validation Flow listener callbacks (assigned to `overlay.listener`):

| Callback | When it fires | Version |
|---|---|---|
| `onValidationFlowLabelCaptured(fields)` | All required fields captured and user confirmed | v8.1+ |
| `onManualInput(field, oldValue, newValue)` | User manually entered or corrected a field value | v8.2+ |
| `onValidationFlowResultUpdate(type, fields, frameData)` | Partial result updated during capture (useful for live progress UI) | v8.4+ |

### Basic Overlay

Use `LabelCaptureBasicOverlay` when fully automated scanning is sufficient and no confirmation step is needed. It renders AR highlights over detected fields directly in the camera feed.

```typescript
const basicOverlay = await LabelCaptureBasicOverlay.withLabelCaptureForView(mode, view);
```

Store the reference — it lets you remove the overlay from the view later when scanning is done:

```typescript
view.removeOverlay(basicOverlay);
```

**Customizing brushes via `LabelCaptureBasicOverlayListener`:**

Attach a listener to control how individual fields and whole labels are highlighted:

```typescript
basicOverlay.listener = {
  brushForField: (overlay, field, label) => {
    // Return a Brush for a specific field, or null to use the default
    if (field.name === "Expiry Date") {
      return new Brush(Color.fromRGBA(255, 0, 0, 0.3), Color.fromRGBA(255, 0, 0, 1), 2);
    }
    return null;
  },
  brushForLabel: (overlay, label) => {
    // Return a Brush for the whole label bounding box, or null to use the default
    return null;
  },
  onLabelTapped: (overlay, label) => {
    // Handle user tap gestures on a highlighted label.
  },
};
```

`Brush` takes a fill color, stroke color, and stroke width. Import `Brush` and `Color` from `@scandit/web-datacapture-core`. Return `null` from either method to keep the default highlight for that element. Use brush colors with transparency (alpha &lt; 1) so they do not occlude the captured barcode or text. `Brush.transparent` hides a highlight entirely. `onLabelTapped` fires when the user taps a highlighted label.

For the full list of styling options, fetch the [Advanced Configurations](https://docs.scandit.com/sdks/web/label-capture/advanced/) page.

### Capturing the scanned frame image

When users want to store or display the image of the frame alongside the captured label data, use `frameData.toBlob()`. The approach differs depending on which overlay is in use.

**Do not `await` the blob conversion** — use `.then()/.catch()` instead. JPEG at quality 0.3 is the fastest option.

**With Validation Flow** — use `onValidationFlowResultUpdate` (v8.4+):

```typescript
overlay.listener = {
  onManualInput: (_field, _oldValue, _newValue) => {},
  onValidationFlowLabelCaptured: (fields) => { /* handle final result */ },
  onValidationFlowResultUpdate: (_type, fields, frameData) => {
    if (!frameData) return;
    // JPEG is fastest — do not await
    frameData
      .toBlob("image/jpeg", 0.3)
      .then((blob) => {
        addScanResult(blob, fields);
      })
      .catch((error) => {
        console.error(error);
        addScanResult(null, fields);
      });
  },
};
```

**With Basic or Advanced Overlay** — use `didUpdateSession`:

`didUpdateSession` fires on every camera frame (~30 times per second). Do not call `toBlob()` unconditionally — only capture the frame when a label is actually fully captured, and disable the mode first so scanning stops before the conversion runs:

```typescript
const labelCaptureListener = {
  didUpdateSession: async (_labelCapture, session, frameData) => {
    if (session.capturedLabels.length === 0) return;

    // Disable mode to stop scanning before capturing the frame
    await mode.setEnabled(false);

    const capturedLabel = session.capturedLabels[0];
    const fields = capturedLabel.fields as LabelField[];

    // JPEG is fastest — do not await
    frameData
      .toBlob("image/jpeg", 0.3)
      .then((blob) => {
        addScanResult(blob, fields);
      })
      .catch((error) => {
        console.error(error);
        addScanResult(null, fields);
      });
  },
};
mode.addListener(labelCaptureListener);
```

---

### Advanced Overlay

Use `LabelCaptureAdvancedOverlay` only when the app needs fully custom AR rendering — drawing its own HTML elements or canvas graphics on top of the camera feed with full positional control. This requires significantly more implementation work. Refer to the [Advanced Configurations](https://docs.scandit.com/sdks/web/label-capture/advanced/) page for the listener interface and anchor points.

---

## ARE — Adaptive Recognition Engine

ARE is Scandit's cloud-based fallback for on-device text recognition. When the on-device OCR engine cannot confidently read a text field, ARE sends the frame to the cloud for processing and returns the result. This improves accuracy on difficult labels (low contrast, unusual fonts, worn text) without requiring a custom model.

**Important constraints — tell the user all of these before they try to enable it:**

- **Validation Flow only.** ARE works exclusively with the Validation Flow overlay (`LabelCaptureValidationFlowOverlay`). It does not work with `LabelCaptureBasicOverlay` or `LabelCaptureAdvancedOverlay`.
- **Requires a license key with the ARE feature flag.** The standard license key does not include ARE. Trial license keys can be issued with ARE enabled for evaluation — direct the user to <support@scandit.com> to request one.
- **For production use, contact Scandit.** ARE is in Beta and requires explicit enablement on the production license key. Tell the user to contact <support@scandit.com> to get it enabled for their production key before going live.

Enable ARE by setting `AdaptiveRecognitionMode.Auto` on the label definition:

```typescript
import { AdaptiveRecognitionMode } from "@scandit/web-datacapture-label";

const labelDef = await new LabelDefinitionBuilder()
  .adaptiveRecognitionMode(AdaptiveRecognitionMode.Auto)
  .addExpiryDateText(await new ExpiryDateTextBuilder().build("Expiry Date"))
  .build("My Label");
```

With `Auto`, the SDK decides when to invoke the cloud fallback. Results arrive through the same Validation Flow callbacks — no additional handling is needed.

Mention ARE only if the user asks about improving OCR accuracy or mentions difficulty reading certain labels. Do not enable it by default.

## Semantic Barcode Fields (IMEI / serial number / part number)

For barcodes that carry a known semantic meaning, prefer the pre-built barcode field builders over `CustomBarcodeBuilder` — they ship with tuned symbology defaults for that field type. Each has a matching `addXxxBarcode` method on `LabelDefinitionBuilder`:

- `ImeiOneBarcodeBuilder` → `addImeiOneBarcode(...)` — IMEI 1 (e.g. smartphone boxes).
- `ImeiTwoBarcodeBuilder` → `addImeiTwoBarcode(...)` — IMEI 2.
- `SerialNumberBarcodeBuilder` → `addSerialNumberBarcode(...)` — serial number.
- `PartNumberBarcodeBuilder` → `addPartNumberBarcode(...)` — part number.

Like every field builder they support `.setSymbologies([...])` / `.setSymbology(...)` and `.isOptional(true)`, and `.build(name)` returns a `Promise`, so `await` each one:

```typescript
import { Symbology } from "@scandit/web-datacapture-barcode";
import {
  ImeiOneBarcodeBuilder,
  ImeiTwoBarcodeBuilder,
  LabelCaptureSettingsBuilder,
  LabelDefinitionBuilder,
  PartNumberBarcodeBuilder,
  SerialNumberBarcodeBuilder,
} from "@scandit/web-datacapture-label";

const settings = await new LabelCaptureSettingsBuilder()
  .addLabel(
    await new LabelDefinitionBuilder()
      .addImeiOneBarcode(await new ImeiOneBarcodeBuilder().build("IMEI 1"))
      .addImeiTwoBarcode(await new ImeiTwoBarcodeBuilder().isOptional(true).build("IMEI 2"))
      .addSerialNumberBarcode(
        await new SerialNumberBarcodeBuilder().setSymbologies([Symbology.Code128]).build("Serial Number")
      )
      .addPartNumberBarcode(await new PartNumberBarcodeBuilder().build("Part Number"))
      .build("Device Box")
  )
  .build();
```

## Pre-built Label Definitions

For the two most common whole-label use cases the web SDK ships ready-made definitions, so you do not have to declare each field by hand. Both are `async` static factories on `LabelDefinition` that return a `Promise<LabelDefinition>` — `await` them and pass the result to `LabelCaptureSettingsBuilder.addLabel(...)`:

- `LabelDefinition.createPriceCaptureDefinition(name)` — retail price labels (price, unit price, weight).
- `LabelDefinition.createVinLabelDefinition(name)` — Vehicle Identification Number labels.

```typescript
import {
  LabelCapture,
  LabelCaptureBasicOverlay,
  LabelCaptureSettingsBuilder,
  LabelDefinition,
  labelCaptureLoader,
} from "@scandit/web-datacapture-label";

const settings = await new LabelCaptureSettingsBuilder()
  .addLabel(await LabelDefinition.createPriceCaptureDefinition("price-label"))
  .build();

const mode = await LabelCapture.forContext(context, settings);
await LabelCaptureBasicOverlay.withLabelCaptureForView(mode, view);
```

Swap `createPriceCaptureDefinition` for `createVinLabelDefinition` for VIN labels.

> **Pre-built definitions are Basic-Overlay only.** `createPriceCaptureDefinition` and `createVinLabelDefinition` are **not compatible with the Validation Flow overlay** — pair them with `LabelCaptureBasicOverlay`. Do not mutate the returned definition (do not add extra fields to it). If the user needs VIN or price capture inside the Validation Flow, hand-build the label with `CustomBarcodeBuilder` / `CustomTextBuilder` instead.

Both factories accept an optional second `AdaptiveRecognitionMode` argument (see **ARE** below).

## Receipt Scanning (Beta)

> **Beta.** Receipt Scanning is built on the Adaptive Recognition Engine and is still in Beta — it may change in future SDK versions. It requires a subscription with the feature enabled; tell the user to contact <support@scandit.com> to enable it. Do not suggest it by default.

Receipt Scanning extracts structured data from a whole receipt (store details, payment totals, line items) in the cloud. It uses a **different integration pattern** from standard label capture — a dedicated overlay and listener rather than the Basic / Validation Flow overlays:

- `LabelCaptureAdaptiveRecognitionOverlay.withLabelCaptureForView(mode, view)` — the receipt-scanning overlay (shows the processing animation).
- `overlay.listener` implementing `onRecognized(result)` — `result` is a `ReceiptScanningResult`.

```typescript
import {
  LabelCaptureAdaptiveRecognitionOverlay,
  LabelCaptureAdaptiveRecognitionSettings,
  type LabelCaptureAdaptiveRecognitionListener,
  type ReceiptScanningResult,
} from "@scandit/web-datacapture-label";

const overlay = await LabelCaptureAdaptiveRecognitionOverlay.withLabelCaptureForView(mode, view);

const settings = await LabelCaptureAdaptiveRecognitionSettings.create();
await settings.setProcessingHintText("Scanning receipt…");
await overlay.applySettings(settings);

overlay.listener = {
  onRecognized: (result: ReceiptScanningResult) => {
    console.log(result.storeName, result.paymentTotal);
    for (const item of result.lineItems) {
      console.log(item.name, item.quantity, item.totalPrice);
    }
  },
  onFailure: () => {
    // Cloud processing failed for this receipt.
  },
} satisfies LabelCaptureAdaptiveRecognitionListener;
```

`ReceiptScanningResult` exposes `storeName`, `storeAddress`, `storeCity`, `date`, `time`, `paymentPreTaxTotal`, `paymentTax`, `paymentTotal`, `loyaltyNumber` (each nullable) and `lineItems` (each with `name`, `unitPrice`, `discount`, `quantity`, `totalPrice`).

## Where to Go Next

After the core integration is running, point the user at the right resource for follow-ups:

- [Label Definitions](https://docs.scandit.com/sdks/web/label-capture/label-definitions/) — full catalogue of pre-built text/barcode field types and how to tune their regex anchors and value patterns.
- [Advanced Configurations](https://docs.scandit.com/sdks/web/label-capture/advanced/) — Validation Flow customisation, adaptive recognition, custom overlays.
- [LabelCaptureSimpleSample](https://github.com/Scandit/datacapture-web-samples/tree/master/03_Advanced_Batch_Scanning_Samples/05_Smart_Label_Capture/LabelCaptureSimpleSample) — working reference sample.
