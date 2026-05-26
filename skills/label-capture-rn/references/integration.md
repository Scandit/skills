# Label Capture React Native Integration Guide

Label Capture (Smart Label Capture) extracts multiple fields from a single label in one scan — e.g. a barcode, an expiry date, and a total price on a grocery label. You declare the structure of the label (which fields, required/optional, barcode symbologies or text regex) and the SDK returns all matched fields per frame.

> **Language note**: Examples below use TypeScript (`.tsx`) because it is the default for React Native templates. For plain JavaScript projects, drop the type annotations and keep the same imports and structure.

## Prerequisites

- Scandit React Native packages installed:
  - `scandit-react-native-datacapture-core`
  - `scandit-react-native-datacapture-barcode`
  - `scandit-react-native-datacapture-label`
- After installing, run `npx pod-install` (or `cd ios && pod install`) for iOS. Android auto-links via Gradle — no manual step.
- React Native `>=0.70`. The New Architecture (Fabric / TurboModules) is supported — no additional setup required beyond the standard RN template.
- A valid Scandit license key:
  - Sign in at <https://ssl.scandit.com> to generate one.
  - No account yet? Sign up at <https://ssl.scandit.com/dashboard/sign-up?p=test>.
- Camera permissions configured by the app:
  - iOS: add `NSCameraUsageDescription` to `ios/<App>/Info.plist`.
  - Android: the manifest permission is declared by the plugin; request at runtime via `PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.CAMERA)` before rendering the scan screen.

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
   ```typescript
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

**Question A — What's on your label?** Present this checklist of supported field types and ask the user to pick everything that applies.

*Barcode fields:*
- `CustomBarcode` — any barcode, user chooses symbologies
- `ImeiOneBarcode` — IMEI 1 (typically for smartphone boxes)
- `ImeiTwoBarcode` — IMEI 2
- `PartNumberBarcode` — part number
- `SerialNumberBarcode` — serial number

*Text fields (preset recognisers):*
- `ExpiryDateText` — expiry date (with configurable date format)
- `PackingDateText` — packing date
- `DateText` — generic date
- `WeightText` — weight
- `UnitPriceText` — unit price
- `TotalPriceText` — total price

*Text fields (custom):*
- `CustomText` — any text, user provides a regex

**Question B — For each selected field:**
- Is it **required** or **optional**? (required = label is not considered captured until this field matches; optional = captured when/if it matches.)
- Does the user need at least N instances of the same field to be matched before the label is considered captured? If so, set `field.numberOfMandatoryInstances = N`. Leave `null` (default) for the normal one-instance behavior.
- For `CustomBarcode`: which **symbologies**? Mention to the user that enabling only the symbologies they actually need improves scanning performance and accuracy.
- For `CustomText` and date/text presets: what **value regex(es)** should the text match? Set via `field.valueRegexes = ['<pattern>']` (or `field.valueRegex = '<pattern>'` for a single pattern — note the property is an array under the hood).
- Optionally, **anchor regex(es)** — context words near the value that help the SDK locate the field (e.g. `EXP:`, `Best before`, `LOT`). Set via `field.anchorRegexes = ['<pattern>']`. To reset/clear, assign an empty array: `field.anchorRegexes = []`. The presets ship with default anchor regexes — override only if the default doesn't match the customer's labels.

**Question C — Which file should the integration code go in?** Then write the code directly into that file. Do not just show it in chat.

After writing the code, show this setup checklist:

1. Install packages:
   ```bash
   npm install scandit-react-native-datacapture-core scandit-react-native-datacapture-barcode scandit-react-native-datacapture-label
   ```
2. Run `npx pod-install` (iOS). Android auto-links.
3. Add `NSCameraUsageDescription` to `ios/<App>/Info.plist`.
4. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from <https://ssl.scandit.com>.
5. If Metro was running, restart it with `--reset-cache`.

## Step 1 — Initialize DataCaptureContext (singleton module)

Create a small module that initializes the context exactly once at import time and re-exports the singleton:

```typescript
// CaptureContext.ts
import { DataCaptureContext } from 'scandit-react-native-datacapture-core';

const licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

DataCaptureContext.initialize(licenseKey);

export default DataCaptureContext.sharedInstance;
```

- `DataCaptureContext.initialize(licenseKey)` is the v8 API. It is idempotent per process — call it once.
- `DataCaptureContext.sharedInstance` is the singleton accessor used everywhere else in the app.
- Do **not** create additional `DataCaptureContext` instances — there is only one per app.

> **Note**: The official `LabelCaptureSimpleSample` uses the legacy `DataCaptureContext.forLicenseKey(...)` form. Both work, but new integrations should use `initialize` for consistency with the rest of the v8 RN docs and the SparkScan / MatrixScan skills.

## Step 2 — Define the label fields (class-based, RN-specific)

Construct each field as a class instance, set `optional`, and assemble them into a `LabelDefinition`. **Do not use `LabelCaptureSettingsBuilder` / `LabelDefinitionBuilder` / factory functions like `customBarcode(...)`** — those are web-only. The RN plugin uses the class-based API:

```typescript
import { Symbology } from 'scandit-react-native-datacapture-barcode';
import {
  CustomBarcode,
  ExpiryDateText,
  LabelDefinition,
  LabelDateFormat,
  LabelDateComponentFormat,
} from 'scandit-react-native-datacapture-label';

const barcode = CustomBarcode.initWithNameAndSymbologies('Barcode', [
  Symbology.EAN13UPCA,
  Symbology.Code128,
]);
barcode.optional = false;

const expiry = new ExpiryDateText('Expiry Date');
expiry.labelDateFormat = new LabelDateFormat(LabelDateComponentFormat.MDY, false);
expiry.optional = false;

const label = new LabelDefinition('Perishable Product');
label.fields = [barcode, expiry];
```

**Field constructors at a glance:**

| Field type | Constructor |
|---|---|
| `CustomBarcode` | `CustomBarcode.initWithNameAndSymbologies(name, [Symbology.X, ...])` |
| `ImeiOneBarcode` / `ImeiTwoBarcode` | `ImeiOneBarcode.initWithNameAndSymbologies(name, [...])` |
| `PartNumberBarcode` / `SerialNumberBarcode` | `SerialNumberBarcode.initWithNameAndSymbologies(name, [...])` |
| `ExpiryDateText` / `PackingDateText` / `DateText` | `new ExpiryDateText(name)` (etc.) |
| `WeightText` / `UnitPriceText` / `TotalPriceText` | `new WeightText(name)` (etc.) |
| `CustomText` | `new CustomText(name)` then assign `field.valueRegex = '<pattern>'` |

For every field you can set `field.optional = true` (default for some presets) or `field.optional = false`.

## Step 3 — Build LabelCaptureSettings

```typescript
import { LabelCaptureSettings } from 'scandit-react-native-datacapture-label';

const settings = LabelCaptureSettings.settingsFromLabelDefinitions([label], {});
```

`settingsFromLabelDefinitions` takes an array of `LabelDefinition` instances (you can declare multiple per scan if needed) and a properties dictionary (usually empty). Do **not** use `LabelCaptureSettingsBuilder` — it does not exist on RN.

## Step 4 — Create the LabelCapture mode and bind it to the context

```typescript
import { LabelCapture } from 'scandit-react-native-datacapture-label';
import dataCaptureContext from './CaptureContext';

const labelCapture = new LabelCapture(settings);
dataCaptureContext.setMode(labelCapture);
```

## Step 5 — Configure the recommended camera

```typescript
import { Camera, FrameSourceState } from 'scandit-react-native-datacapture-core';

const camera = Camera.withSettings(LabelCapture.createRecommendedCameraSettings());
if (!camera) throw new Error('No camera available');
dataCaptureContext.setFrameSource(camera);
await camera.switchToDesiredState(FrameSourceState.On);
```

## Step 6 — Embed `<DataCaptureView>` and add the overlay

In your function component, render `<DataCaptureView>` and add the overlay through the `ref` callback (this is the imperative side of the RN bridge):

```tsx
import { DataCaptureView } from 'scandit-react-native-datacapture-core';
import {
  LabelCaptureBasicOverlay,
  LabelCaptureValidationFlowOverlay,
} from 'scandit-react-native-datacapture-label';

<DataCaptureView
  style={{ flex: 1 }}
  context={dataCaptureContext}
  ref={(view) => {
    if (viewRef.current || view === null) return;
    viewRef.current = view;

    // Either the basic overlay…
    const basicOverlay = new LabelCaptureBasicOverlay(labelCaptureRef.current);
    view.addOverlay(basicOverlay);

    // …or the Validation Flow overlay (see Step 7).
  }}
/>
```

## Step 7 — Validation Flow (recommended default)

`LabelCaptureValidationFlowOverlay` is the recommended default UX. It ships the guided field checklist, manual-entry sheet, and final-result callback — features the customer would otherwise have to build themselves on top of `LabelCaptureBasicOverlay`. Render it **full-screen** (do not embed it inside a card / partial-height container).

`LabelCaptureValidationFlowListener` is a **single interface with three required methods**. There is no base/Extended split on RN. If a listener object omits a method, the runtime dispatcher throws when that event fires — provide empty bodies for callbacks you don't care about.

```tsx
import {
  LabelCaptureValidationFlowOverlay,
  LabelResultUpdateType,
  type LabelCaptureValidationFlowListener,
  type LabelField,
} from 'scandit-react-native-datacapture-label';
import type { FrameData } from 'scandit-react-native-datacapture-core';

const listener: LabelCaptureValidationFlowListener = {
  didCaptureLabelWithFields(fields: LabelField[]) {
    // Final result for one label, after the user has confirmed any required corrections.
  },

  didSubmitManualInputForField(_field, _oldValue, _newValue) {
    // Fires whenever the user manually enters or corrects a field value.
    // Leave the body empty if you don't need this signal.
  },

  async didUpdateValidationFlowResult(
    _type: LabelResultUpdateType,
    _asyncId: number,
    _fields: LabelField[],
    _getFrameData: () => Promise<FrameData | null>,
  ): Promise<void> {
    // Fires multiple times during capture as fields accumulate.
    // Call `await _getFrameData()` here to retrieve the camera frame
    // that produced this partial result (image upload / auditing).
    // Leave the body empty if you don't need progress feedback.
  },
};

const overlay = new LabelCaptureValidationFlowOverlay(labelCaptureRef.current);
overlay.listener = listener;
view.addOverlay(overlay);
```

To customize the Validation Flow texts/placeholders (the only customization surface — colors, layout, fonts are **not** customizable), see `references/validation-flow.md`.

> **Listener naming**: On React Native the listener uses iOS-style method names (`didCaptureLabelWithFields`, `didSubmitManualInputForField`, `didUpdateValidationFlowResult`). Do **not** use the web equivalents (`onValidationFlowLabelCaptured`, `onManualInput`) — they do not exist on RN.

## Step 8 — Result handling without the Validation Flow

Use this path only when the customer needs a live AR overlay or a custom UI the Validation Flow can't produce (otherwise stick with Step 7).

Attach a `LabelCaptureListener` to the mode and read `session.capturedLabels` in `didUpdateSession`. `getFrameData` is the supported hook for retrieving the camera frame during scanning ("image listener"):

```typescript
import type { LabelCaptureListener, LabelCaptureSession, LabelField } from 'scandit-react-native-datacapture-label';
import type { FrameData } from 'scandit-react-native-datacapture-core';

const listener: LabelCaptureListener = {
  async didUpdateSession(
    _labelCapture,
    session: LabelCaptureSession,
    getFrameData: () => Promise<FrameData | null>,
  ) {
    if (session.capturedLabels.length === 0) return;
    for (const captured of session.capturedLabels) {
      for (const field of captured.fields as LabelField[]) {
        const value = field.barcode?.data ?? field.text;
        console.log(`${field.name} = ${value}`);
        // For dates you can also call field.asDate().
      }
    }
    // Optionally: const frame = await getFrameData(); to grab the image
    // that produced this update. Only valid for the duration of the callback.
  },
};

labelCaptureRef.current.addListener(listener);
```

For brushes, advanced overlays, and the full image-listener pattern, see `references/customization.md`.

## Step 9 — Lifecycle (AppState + cleanup)

Pause the camera when the app backgrounds and resume on return; remove the mode from the context when the screen unmounts.

```tsx
useEffect(() => {
  const sub = AppState.addEventListener('change', async (next) => {
    if (next === 'inactive' || next === 'background') {
      wasOn.current = (await cameraRef.current.getCurrentState()) === FrameSourceState.On;
    } else if (next === 'active' && wasOn.current) {
      await cameraRef.current.switchToDesiredState(FrameSourceState.On);
      labelCaptureRef.current.isEnabled = true;
    }
  });
  return () => {
    sub.remove();
    dataCaptureContext.removeMode(labelCaptureRef.current);
  };
}, []);
```

Do **not** call `dataCaptureContext.dispose()` — the singleton context lives for the entire app lifetime.

## Step 10 — Complete working example

```tsx
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AppState, Modal, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import {
  Camera,
  DataCaptureContext,
  DataCaptureView,
  FrameSourceState,
} from 'scandit-react-native-datacapture-core';
import { Symbology } from 'scandit-react-native-datacapture-barcode';
import {
  CustomBarcode,
  ExpiryDateText,
  LabelCapture,
  LabelCaptureBasicOverlay,
  LabelCaptureSettings,
  LabelCaptureValidationFlowListener,
  LabelCaptureValidationFlowOverlay,
  LabelDefinition,
  LabelField,
  TotalPriceText,
} from 'scandit-react-native-datacapture-label';

DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
const dataCaptureContext = DataCaptureContext.sharedInstance;

export default function App() {
  const viewRef = useRef<DataCaptureView | null>(null);
  const overlayRef = useRef<LabelCaptureValidationFlowOverlay | null>(null);
  const wasOn = useRef(false);
  const [resultText, setResultText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);

  const cameraRef = useRef<Camera>(null!);
  if (!cameraRef.current) {
    const camera = Camera.withSettings(LabelCapture.createRecommendedCameraSettings());
    if (!camera) throw new Error('No camera');
    dataCaptureContext.setFrameSource(camera);
    cameraRef.current = camera;
  }

  const labelCaptureRef = useRef<LabelCapture>(null!);
  if (!labelCaptureRef.current) {
    const barcode = CustomBarcode.initWithNameAndSymbologies('Barcode', [
      Symbology.EAN13UPCA,
      Symbology.Code128,
    ]);
    barcode.optional = false;

    const expiry = new ExpiryDateText('Expiry Date');
    expiry.optional = false;

    const total = new TotalPriceText('Total Price');
    total.optional = true;

    const label = new LabelDefinition('Perishable Product');
    label.fields = [barcode, expiry, total];

    const settings = LabelCaptureSettings.settingsFromLabelDefinitions([label], {});
    const labelCapture = new LabelCapture(settings);
    dataCaptureContext.setMode(labelCapture);
    labelCaptureRef.current = labelCapture;
  }

  const listener = useMemo<LabelCaptureValidationFlowListener>(
    () => ({
      didCaptureLabelWithFields(fields: LabelField[]) {
        setResultText(
          fields.map((f) => `${f.name}: ${f.barcode?.data ?? f.text ?? 'N/A'}`).join('\n'),
        );
        setModalVisible(true);
      },
      didSubmitManualInputForField(_field, _oldValue, _newValue) {
        // User manually corrected a field value.
      },
    }),
    [],
  );

  useEffect(() => {
    void cameraRef.current.switchToDesiredState(FrameSourceState.On);
    labelCaptureRef.current.isEnabled = true;
  }, []);

  useEffect(() => {
    const sub = AppState.addEventListener('change', async (next) => {
      if (next === 'inactive' || next === 'background') {
        wasOn.current = (await cameraRef.current.getCurrentState()) === FrameSourceState.On;
      } else if (next === 'active' && wasOn.current) {
        await cameraRef.current.switchToDesiredState(FrameSourceState.On);
        labelCaptureRef.current.isEnabled = true;
      }
    });
    return () => {
      sub.remove();
      dataCaptureContext.removeMode(labelCaptureRef.current);
    };
  }, []);

  useEffect(() => {
    if (overlayRef.current) overlayRef.current.listener = listener;
    return () => {
      if (overlayRef.current) overlayRef.current.listener = null;
    };
  }, [listener]);

  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.safeArea}>
        <DataCaptureView
          style={styles.captureView}
          context={dataCaptureContext}
          ref={(view) => {
            if (viewRef.current || view === null) return;
            viewRef.current = view;

            const basic = new LabelCaptureBasicOverlay(labelCaptureRef.current);
            view.addOverlay(basic);

            const flow = new LabelCaptureValidationFlowOverlay(labelCaptureRef.current);
            flow.listener = listener;
            overlayRef.current = flow;
            view.addOverlay(flow);
          }}
        />
        <Modal visible={modalVisible} transparent animationType="fade">
          <View style={styles.modalOverlay}>
            <View style={styles.modalCard}>
              <Text style={styles.modalTitle}>LABEL CAPTURED</Text>
              <Text>{resultText}</Text>
              <TouchableOpacity
                style={styles.continueBtn}
                onPress={async () => {
                  setModalVisible(false);
                  await cameraRef.current.switchToDesiredState(FrameSourceState.On);
                  labelCaptureRef.current.isEnabled = true;
                }}>
                <Text style={styles.continueText}>CONTINUE SCANNING</Text>
              </TouchableOpacity>
            </View>
          </View>
        </Modal>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1 },
  captureView: { flex: 1 },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  modalCard: { backgroundColor: 'white', padding: 24, borderRadius: 8, width: '85%' },
  modalTitle: { fontSize: 18, fontWeight: 'bold', marginBottom: 12 },
  continueBtn: { backgroundColor: 'black', padding: 12, marginTop: 16, borderRadius: 4 },
  continueText: { color: 'white', textAlign: 'center', fontWeight: 'bold' },
});
```

## Key Rules

- **Class-based field API only.** `CustomBarcode.initWithNameAndSymbologies(...)`, `new ExpiryDateText(name)`, `field.optional = true`, `LabelCaptureSettings.settingsFromLabelDefinitions([...], {})`. Do not use builders or factory functions — those are web-only.
- **iOS-style listener names.** `didCaptureLabelWithFields`, `didSubmitManualInputForField`, `didUpdateValidationFlowResult` (8.4+). Never `onValidationFlowLabelCaptured` / `onManualInput` — those are web.
- **Singleton context.** Always `DataCaptureContext.initialize(licenseKey)` once at import time and access via `DataCaptureContext.sharedInstance`. Never `dispose()` it.
- **Overlay attachment via the `ref` callback.** `<DataCaptureView>` is a native bridge — overlays are added imperatively after the view mounts.
- **Cleanup on unmount.** Call `dataCaptureContext.removeMode(labelCapture)` and remove the `AppState` subscription in the `useEffect` cleanup.
- **License key in source is a placeholder** (`-- ENTER YOUR SCANDIT LICENSE KEY HERE --`). Replace it before shipping.

## Where to Go Next

- [Label Definitions](https://docs.scandit.com/sdks/react-native/label-capture/label-definitions/) — full catalogue of pre-built text/barcode field types and how to tune their regex anchors and value patterns.
- [Advanced Configurations](https://docs.scandit.com/sdks/react-native/label-capture/advanced/) — Validation Flow customisation, adaptive recognition, custom overlays.
- [LabelCaptureSimpleSample (RN)](https://github.com/Scandit/datacapture-react-native-samples/tree/master/03_Advanced_Batch_Scanning_Samples/05_Smart_Label_Capture/LabelCaptureSimpleSample) — working reference sample.
