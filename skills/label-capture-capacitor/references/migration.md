# Label Capture Capacitor Migration Guide

## Migration principles

- **Authority.** When this guide and the API reference disagree, trust the API reference — and a runtime check in the user's project — over this guide. Say which source you followed and why in the summary.
- **Behaviour changes.** Never present a visual or behaviour change (new default, different overlay look, changed feedback, changed scan timing) as a 1:1 rename. List each one in the summary as a judgment call the user must confirm.
- **Compatibility layer.** When the scanning code sits behind a shared scanner library or wrapper that other code calls, keep that library's public API frozen (same types, method names, callbacks) and change only the Scandit calls underneath.
- **Dual-version code.** When code must run on both the old and the target version, branch on a symbol this guide lists as removed in the target version — never on a version string, and never on the presence of the new API. A deprecated symbol that is still present proves nothing about the installed version. Example: `BarcodeCapture.forContext` is removed on Flutter and React Native 7→8, but still exists on Web and deprecated-but-present on Capacitor and Cordova.

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
