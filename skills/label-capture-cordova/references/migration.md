# Label Capture Cordova Migration Guide

## Step 1: Detect the installed SDK version

Find out which version of `scandit-cordova-datacapture-label` the project uses.

1. **`config.xml`** — look for `<plugin name="scandit-cordova-datacapture-label" spec="..." />`. The `spec` is the installed version constraint.
2. **`package.json`** — for projects that pin Cordova plugins via npm (under `cordova.plugins` or `dependencies`).
3. **`plugins/scandit-cordova-datacapture-label/plugin.xml`** — the `version` attribute is the exact installed version.

If the plugin is not listed, fall back to `references/integration.md` instead of migrating.

## Web-only transitions that do not apply on Cordova

- **v8.4 → v8.5 ergonomic builder shorthand** (factory functions like `label(...)`, `customBarcode(...)`). Cordova does not expose builders to begin with — those changes are web-only sugar.

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

For every `Scandit.CustomText` field, rename property assignments:

```javascript
// Before (≤ 7.6)
const sku = new Scandit.CustomText('SKU');
sku.pattern = '\\d{8}';
sku.dataTypePattern = 'SKU\\s*:';

// After (≥ 8.0)
const sku = new Scandit.CustomText('SKU');
sku.valueRegex = '\\d{8}';
sku.anchorRegex = 'SKU\\s*:';
```

Bump the plugin version in `config.xml`:

```xml
<plugin name="scandit-cordova-datacapture-core" spec="^8.0.0" />
<plugin name="scandit-cordova-datacapture-barcode" spec="^8.0.0" />
<plugin name="scandit-cordova-datacapture-label" spec="^8.0.0" />
```

Then `cordova prepare ios && cordova prepare android` (and `cd platforms/ios && pod install`).

---

## v8.1 → v8.2 — Validation Flow redesign

In v8.2, the Validation Flow gained a manual-input path: the user can correct or enter a field value if OCR fails. The listener gained an additional optional method.

### What changed

- New optional listener method: `didSubmitManualInputForField(field, oldValue, newValue)` on `LabelCaptureValidationFlowListener`. Fires when the user manually enters or corrects a field value.
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

If you previously used internal text-setter properties like `requiredFieldErrorText` directly on the overlay, switch to `LabelCaptureValidationFlowSettings`:

```javascript
const flowSettings = new Scandit.LabelCaptureValidationFlowSettings();
flowSettings.setPlaceholderTextForLabelDefinition('Perishable Product', 'Enter expiry date');
validationFlowOverlay.flowSettings = flowSettings;
```

Bump versions in `config.xml` to `^8.2.0` and run `cordova prepare ios && cordova prepare android`.

---

## v8.2 → v8.4 — additive `didUpdateValidationFlowResult` listener method (non-breaking)

`LabelCaptureValidationFlowListener` gained an optional method that fires as the validation flow accumulates partial results during capture. Existing listeners continue to work unchanged.

### What changed

```javascript
const listener = {
  didCaptureLabelWithFields(fields) { /* existing */ },
  didSubmitManualInputForField(field, oldValue, newValue) { /* existing since 8.2 */ },
  didUpdateValidationFlowResult(type, asyncId, fields, getFrameData) {
    // New in 8.4.
  },
};
```

`Scandit.LabelResultUpdateType` is a new enum shipped alongside the listener method.

### Migration

Bump versions:

```xml
<plugin name="scandit-cordova-datacapture-core" spec="^8.4.0" />
<plugin name="scandit-cordova-datacapture-barcode" spec="^8.4.0" />
<plugin name="scandit-cordova-datacapture-label" spec="^8.4.0" />
```

Then `cordova prepare ios && cordova prepare android` (and `cd platforms/ios && pod install`).

Add the new method to your existing listener if you want fine-grained progress feedback:

```javascript
validationFlowOverlay.listener = {
  didCaptureLabelWithFields(fields) { /* existing */ },
  didSubmitManualInputForField(field, oldValue, newValue) { /* existing */ },
  didUpdateValidationFlowResult(type, asyncId, fields, getFrameData) {
    // Optional — leave unimplemented if you don't need progress callbacks.
  },
};
```

The signature is `(type: Scandit.LabelResultUpdateType, asyncId: number, fields: Scandit.LabelField[], getFrameData: () => Promise<unknown>) => void`.

### When to add it

Only if the user needs fine-grained progress feedback as the Validation Flow accumulates partial results.

### Verify

- Existing `didCaptureLabelWithFields` / `didSubmitManualInputForField` callbacks still fire.
- If you added `didUpdateValidationFlowResult`, it fires multiple times during a capture as fields accumulate.
