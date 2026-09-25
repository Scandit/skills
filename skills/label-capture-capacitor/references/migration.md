# Label Capture Capacitor Migration Guide

## Step 1: Detect the installed SDK version

Find out which version of `scandit-capacitor-datacapture-label` the project uses.

1. **`package.json`** — look for `scandit-capacitor-datacapture-label` (and `scandit-capacitor-datacapture-core` / `…-barcode`). The value is the installed version constraint.
2. **`package-lock.json`** / **`yarn.lock`** — for the exact resolved version.

If the package is not listed, fall back to `references/integration.md`.

## Web-only transitions that do not apply on Capacitor

- **v8.4 → v8.5 ergonomic builder shorthand** (factory functions like `label(...)`, `customBarcode(...)`). Capacitor does not expose builders to begin with — those changes are web-only sugar.

---

## v7.6 → v8.0 — regex property renames on `CustomText`

In v8.0, `CustomText` regex-property names were aligned with the rest of the SDK.

### What changed

| Old (≤ v7.6) | New (≥ v8.0) |
|---|---|
| `field.pattern` | `field.valueRegex` |
| `field.patterns` | `field.valueRegexes` |
| `field.dataTypePattern` | `field.anchorRegex` |
| `field.dataTypePatterns` | `field.anchorRegexes` |

### Migration

For every `CustomText` field, rename property assignments:

```javascript
// Before (≤ 7.6)
const sku = new CustomText('SKU');
sku.pattern = '\\d{8}';
sku.dataTypePattern = 'SKU\\s*:';

// After (≥ 8.0)
const sku = new CustomText('SKU');
sku.valueRegex = '\\d{8}';
sku.anchorRegex = 'SKU\\s*:';
```

Bump the package versions in `package.json`:

```json
{
  "dependencies": {
    "scandit-capacitor-datacapture-core": "^8.0.0",
    "scandit-capacitor-datacapture-barcode": "^8.0.0",
    "scandit-capacitor-datacapture-label": "^8.0.0"
  }
}
```

Then `npm install && npx cap sync` and `cd ios/App && pod install`.

---

## v8.1 → v8.2 — Validation Flow redesign

In v8.2, the Validation Flow gained a manual-input path: the user can correct or enter a field value if OCR fails.

### What changed

- New optional listener method: `didSubmitManualInputForField(field, oldValue, newValue)` on the validation flow listener.
- New settings type `LabelCaptureValidationFlowSettings` for tuning the redesigned flow (e.g. customising prompts via `setPlaceholderTextForLabelDefinition`).

### Migration

If your existing listener only handles `didCaptureLabelWithFields`, no rename is required. To react to manual corrections, add the new method:

```javascript
validationFlowOverlay.listener = {
  didCaptureLabelWithFields(fields) { /* existing */ },
  didSubmitManualInputForField(field, oldValue, newValue) {
    // New in 8.2.
  },
};
```

If you want to customise the placeholder copy, use `LabelCaptureValidationFlowSettings`:

```javascript
import { LabelCaptureValidationFlowSettings } from 'scandit-capacitor-datacapture-label';

const flowSettings = new LabelCaptureValidationFlowSettings();
flowSettings.setPlaceholderTextForLabelDefinition('Perishable Product', 'Enter expiry date');
validationFlowOverlay.flowSettings = flowSettings;
```

Bump versions in `package.json` to `^8.2.0` and run `npm install && npx cap sync`.

---

## v8.2 → v8.4 — additive `didUpdateValidationFlowResult` listener method (non-breaking)

The Validation Flow listener gained an optional method that fires as the validation flow accumulates partial results during capture. Existing listeners continue to work unchanged.

### What changed

```javascript
const listener = {
  didCaptureLabelWithFields(fields) { /* existing */ },
  didSubmitManualInputForField(field, oldValue, newValue) { /* existing since 8.2 */ },
  async didUpdateValidationFlowResult(type, asyncId, fields, getFrameData) {
    // New in 8.4.
  },
};
```

`LabelResultUpdateType` is a new enum imported from `scandit-capacitor-datacapture-label`.

### Migration

Bump versions:

```json
{
  "dependencies": {
    "scandit-capacitor-datacapture-core": "^8.4.0",
    "scandit-capacitor-datacapture-barcode": "^8.4.0",
    "scandit-capacitor-datacapture-label": "^8.4.0"
  }
}
```

Then `npm install && npx cap sync` and `cd ios/App && pod install`.

Add the new method to your existing listener if you want fine-grained progress feedback:

```javascript
import { LabelResultUpdateType } from 'scandit-capacitor-datacapture-label';

validationFlowOverlay.listener = {
  didCaptureLabelWithFields(fields) { /* existing */ },
  didSubmitManualInputForField(field, oldValue, newValue) { /* existing */ },
  async didUpdateValidationFlowResult(type, asyncId, fields, getFrameData) {
    // Optional — leave the body empty if you don't need progress callbacks.
  },
};
```

The signature is `(type: LabelResultUpdateType, asyncId: number, fields: LabelField[], getFrameData: () => Promise<unknown>) => Promise<void>`.

### When to add it

Only if the user needs fine-grained progress feedback as the Validation Flow accumulates partial results.

### Verify

- Existing `didCaptureLabelWithFields` / `didSubmitManualInputForField` callbacks still fire.
- If you added `didUpdateValidationFlowResult`, it fires multiple times during a capture as fields accumulate.
