# Label Capture React Native Migration Guide

## Step 1: Detect the installed SDK version

Find out which version of `scandit-react-native-datacapture-label` the project uses.

1. **`package.json`** — look for `scandit-react-native-datacapture-label` (and `scandit-react-native-datacapture-core` / `scandit-react-native-datacapture-barcode`). The value is the installed version constraint (e.g. `"^8.2.0"`).
2. **`package-lock.json`** or **`yarn.lock`** — if `package.json` only has a range, check the lockfile for the exact resolved version.

If the package is not listed at all, the project does not use Label Capture on React Native yet — fall back to `references/integration.md` instead of migrating.

## Web-only transitions that do not apply on React Native

Several Label Capture API changes shipped in the Web SDK that do **not** apply to the React Native plugin. Do not attempt to apply them:

- **v7.6 → v8.0 regex property renames** (`pattern`/`patterns`/`dataTypePattern`/`dataTypePatterns` → `valueRegex`/`valueRegexes`/`anchorRegex`/`anchorRegexes`). The React Native plugin does not expose these as builder setters; field definitions are class-based and configured via direct property assignment that did not undergo the rename.
- **v8.1 → v8.2 Validation Flow text-setter deprecation** (`setRequiredFieldErrorText` / `setMissingFieldsHintText` / `setManualInputButtonText`, replaced by `setPlaceholderTextForLabelDefinition` on web). The React Native plugin never exposed those text setters in the first place.
- **v8.4 → v8.5 ergonomic builder shorthand** (factory functions like `label(...)`, `customBarcode(...)`, inline pre-built/builder unification). The RN plugin has no builders to begin with — those changes are web-only sugar.

Skip those sections in any web-flavoured migration guide and apply only the React Native transitions below.

---

## v8.2 → v8.4 — additive `didUpdateValidationFlowResult` listener method (non-breaking)

`LabelCaptureValidationFlowListener` gained an optional method that fires when a validation-flow result is updated during capture. Existing listeners continue to work unchanged.

```typescript
import {
  type LabelCaptureValidationFlowListener,
  type LabelField,
  LabelResultUpdateType,
} from 'scandit-react-native-datacapture-label';

const listener: LabelCaptureValidationFlowListener = {
  didCaptureLabelWithFields(_fields: LabelField[]) {
    // Fired when the validation flow finishes for a label (existing API).
  },
  didSubmitManualInputForField(_field, _oldValue, _newValue) {
    // Fired when the user manually corrects or enters a value (existing API since 8.2).
  },
  didUpdateValidationFlowResult(
    _type: LabelResultUpdateType,
    _asyncId: number,
    _fields: LabelField[],
    _getFrameData: () => Promise<unknown>,
  ) {
    // New in 8.4 — fires as the validation flow accumulates partial results.
    // Optional. Implement only if you need fine-grained progress feedback during capture.
  },
};
```

`LabelResultUpdateType` is a new enum shipped alongside the listener method — import it from `scandit-react-native-datacapture-label` when you use the new method.

### When to add it

Useful only if the user needs fine-grained progress feedback as the Validation Flow accumulates partial results (e.g. to update UI mid-flow rather than only at its end). If the user doesn't ask for that, leave their listener alone — the method is optional.

### Step 1: Update the package versions

```json
{
  "dependencies": {
    "scandit-react-native-datacapture-core": "^8.4.0",
    "scandit-react-native-datacapture-barcode": "^8.4.0",
    "scandit-react-native-datacapture-label": "^8.4.0"
  }
}
```

Then:

```bash
npm install
npx pod-install
# Restart Metro with cache reset:
npx react-native start --reset-cache
```

### Step 2: (Optional) add the new listener method

Only edit your existing `LabelCaptureValidationFlowListener` implementation if you want the new behaviour. Add `didUpdateValidationFlowResult` to the listener object as shown above. The signature is `(type: LabelResultUpdateType, asyncId: number, fields: LabelField[], getFrameData: () => Promise<unknown>) => void`.

### Step 3: Verify

Run the app and confirm:

- Existing `didCaptureLabelWithFields` / `didSubmitManualInputForField` callbacks still fire.
- If you added `didUpdateValidationFlowResult`, it fires multiple times during a capture as fields accumulate.

No other code changes are required.
