# Label Capture Web Migration Guide

When a user asks to upgrade or migrate a Label Capture integration, identify which version boundary they're crossing. Prefer reading `package.json` for `@scandit/web-datacapture-label`. Otherwise ask directly: "Which version are you on, and which version are you upgrading to?"

The sections below are cumulative — if the user is going from v7.6 to v8.5, walk them through §1, §2, §3, and §4 in order.

## 1. v7.6 → v8.0 — `LabelFieldDefinition` regex renames (breaking)

At the v7 → v8 major version bump, the regex-configuration properties on every `LabelFieldDefinition` subclass were renamed. The old names no longer exist from v8.0 onwards.

| Old (v7.x) | New (v8.0+) |
|---|---|
| `pattern` | `valueRegex` |
| `patterns` | `valueRegexes` |
| `dataTypePattern` | `anchorRegex` |
| `dataTypePatterns` | `anchorRegexes` |

The same rename applies to the matching setter methods on every field builder (`CustomTextBuilder`, `ExpiryDateTextBuilder`, `TotalPriceTextBuilder`, `WeightTextBuilder`, etc.): `setPattern` → `setValueRegex`, `setPatterns` → `setValueRegexes`, `setDataTypePattern` → `setAnchorRegex`, `setDataTypePatterns` → `setAnchorRegexes`.

### Before (v7.x)

```typescript
const expiryBuilder = new ExpiryDateTextBuilder()
  .setDataTypePattern("EXP[:\\s]+")
  .setPattern("\\d{2}/\\d{2}/\\d{2,4}");
```

### After (v8.0+)

```typescript
const expiryBuilder = new ExpiryDateTextBuilder()
  .setAnchorRegex("EXP[:\\s]+")
  .setValueRegex("\\d{2}/\\d{2}/\\d{2,4}");
```

Apply the rename across every field definition in the user's codebase. No other logic changes. If the user is already on v8.0 or later, this section does not apply — skip to §2.

## 2. v8.1 → v8.2 — Validation Flow listener change + redesign

Two things change between 8.1 and 8.2.

**(a) Listener interface gains `onManualInput` (breaking).** `LabelCaptureValidationFlowListener` in 8.1 had only `onValidationFlowLabelCaptured`. In 8.2 a second required method is added:

```ts
onManualInput(field: LabelField, oldValue: string | undefined, newValue: string): void;
```

Existing listeners that don't implement it will fail to satisfy the interface after upgrade — add the method (a no-op is fine if the user doesn't care about manual-input events).

**(b) Redesigned flow deprecates the old text setters (non-breaking).** The Validation Flow UI was redesigned. These async setters on `LabelCaptureValidationFlowSettings` still exist and are callable, but they have no effect in the redesigned UI:

- `setRequiredFieldErrorText`
- `setMissingFieldsHintText`
- `setManualInputButtonText`

A new method, `setPlaceholderTextForLabelDefinition(fieldName, placeholder)`, is the recommended way to customise per-field hints in the redesigned flow. If the user wants their existing text customisation to have a visible effect, switch to the new method.

### Before (v8.1)

```typescript
const validationFlowSettings = await LabelCaptureValidationFlowSettings.create();
await validationFlowSettings.setRequiredFieldErrorText("This field is required");
await validationFlowSettings.setMissingFieldsHintText("Please fill the missing fields");
await validationFlowSettings.setManualInputButtonText("Enter manually");
await overlay.applySettings(validationFlowSettings);

overlay.listener = {
  onValidationFlowLabelCaptured: (fields) => { /* ... */ },
} satisfies LabelCaptureValidationFlowListener;
```

### After (v8.2+)

```typescript
const validationFlowSettings = await LabelCaptureValidationFlowSettings.create();
await validationFlowSettings.setPlaceholderTextForLabelDefinition("Expiry Date", "MM.DD.YY");
await validationFlowSettings.setPlaceholderTextForLabelDefinition("Total Price", "e.g., $13.66");
await overlay.applySettings(validationFlowSettings);

overlay.listener = {
  onValidationFlowLabelCaptured: (fields) => { /* ... */ },
  onManualInput: (_field, _oldValue, _newValue) => {
    // Fires when the user manually enters or corrects a value.
  },
} satisfies LabelCaptureValidationFlowListener;
```

Leave the old setter calls in place if the user wants to stay with a non-redesigned build path, but add `onManualInput` — it is now a required listener method.

## 3. v8.2 → v8.4 — new optional `onValidationFlowResultUpdate` listener (additive, non-breaking)

`LabelCaptureValidationFlowListener` gains an optional method that fires when a validation-flow result is updated during capture. Existing listeners continue to work unchanged.

```typescript
export interface LabelCaptureValidationFlowListener {
  onValidationFlowLabelCaptured(fields: LabelField[]): void;
  onManualInput(field: LabelField, oldValue: string | undefined, newValue: string): void;
  onValidationFlowResultUpdate?(
    type: LabelResultUpdateType,
    fields: LabelField[],
    frameData: FrameData | null
  ): void;
}
```

`LabelResultUpdateType` is a new enum shipped alongside the listener method — import it from `@scandit/web-datacapture-label` when you use the new method.

### When to add it

The new method is useful if the user needs fine-grained progress feedback as the Validation Flow accumulates partial results (e.g. to update UI during the flow rather than only at its end). If the user doesn't ask for that, leave their listener alone — the method is optional.

### Example — adding the method

```typescript
import {
  type LabelCaptureValidationFlowListener,
  type LabelField,
  LabelResultUpdateType,
} from "@scandit/web-datacapture-label";
import type { FrameData } from "@scandit/web-datacapture-core";

overlay.listener = {
  onManualInput: (_field, _oldValue, _newValue) => { /* ... */ },
  onValidationFlowLabelCaptured: (_fields) => { /* ... */ },
  onValidationFlowResultUpdate: (
    type: LabelResultUpdateType,
    fields: LabelField[],
    _frameData: FrameData | null
  ) => {
    // Fires when the validation flow's current result is updated.
    // See LabelResultUpdateType for the update kind (e.g. added, modified).
  },
} satisfies LabelCaptureValidationFlowListener;
```

## 4. v8.4 → v8.5 — ergonomic builder improvements (additive, non-breaking)

Two purely additive changes. All existing code continues to work — upgrading is a stylistic preference.

### Change A — inline builders, name in constructor, single outer `await`

`LabelDefinitionBuilder.addXxx()` now accepts either a pre-built field or the corresponding field builder. `LabelCaptureSettingsBuilder.addLabel()` similarly accepts either a `LabelDefinition` or a `LabelDefinitionBuilder`. Pending builders are resolved inside the top-level `build()` call. Field-builder constructors also accept an optional name; `build(name?)` falls back to the constructor-set value if no name is passed.

**Before (still valid in 8.5):**

```typescript
const settings = await new LabelCaptureSettingsBuilder()
  .addLabel(
    await new LabelDefinitionBuilder()
      .addCustomBarcode(
        await new CustomBarcodeBuilder()
          .setSymbology(Symbology.EAN13UPCA)
          .build("Barcode")
      )
      .addExpiryDateText(await new ExpiryDateTextBuilder().build("Expiry Date"))
      .build("Perishable Product")
  )
  .build();
```

**After (new in 8.5):**

```typescript
const settings = await new LabelCaptureSettingsBuilder()
  .addLabel(
    new LabelDefinitionBuilder("Perishable Product")
      .addCustomBarcode(new CustomBarcodeBuilder("Barcode").setSymbology(Symbology.EAN13UPCA))
      .addExpiryDateText(new ExpiryDateTextBuilder("Expiry Date"))
  )
  .build();
```

One `await` at the outermost `build()`, and each builder's name is co-located with its constructor.

### Change B — factory-function helpers (optional sugar)

Each `LabelDefinitionBuilder` and `LabelFieldDefinitionBuilder` now has a matching factory function whose name is the builder name with a lowercase first letter and no `Builder` suffix. Equivalent to the class constructors, but less noise at call sites.

```typescript
import {
  customBarcode,
  expiryDateText,
  label,
  labelCaptureSettings,
  LabelCapture,
} from "@scandit/web-datacapture-label";

const settings = await labelCaptureSettings()
  .addLabel(
    label("Perishable Product")
      .addCustomBarcode(customBarcode("Barcode").setSymbology(Symbology.EAN13UPCA))
      .addExpiryDateText(expiryDateText("Expiry Date"))
  )
  .build();
```

### When to migrate

Only if the user explicitly asks for the terser syntax. Both styles are fully supported. Do not rewrite working code just because a newer style exists.
