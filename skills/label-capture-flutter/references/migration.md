# Label Capture Flutter Migration Guide

## Step 1: Detect the installed SDK version

Find out which version of `scandit_flutter_datacapture_label` the project uses.

1. **`pubspec.yaml`** — look for `scandit_flutter_datacapture_label` (and `…_core` / `…_barcode`). The value is the installed version constraint.
2. **`pubspec.lock`** — for the exact resolved version.

If the package is not listed, fall back to `references/integration.md` instead of migrating.

## Web-only transitions that do not apply on Flutter

- **v7.6 → v8.0 regex property renames** (`pattern`/`dataTypePattern` → `valueRegex`/`anchorRegex`). Flutter uses builder setters that did not undergo the rename.
- **v8.4 → v8.5 ergonomic builder shorthand** (factory functions like `label(...)`, `customBarcode(...)`). The Flutter plugin already exposes builders; the v8.5 sugar is web-only.

Skip those sections in any web-flavoured migration guide.

---

## v8.1 → v8.2 — Validation Flow listener split + redesign

In v8.2, the Validation Flow listener was split into two interfaces and a manual-input callback was added. Existing code that only handled `didCaptureLabelWithFields` continues to work via the base listener; the new manual-input callback requires the **Extended** listener.

### What changed

- `LabelCaptureValidationFlowListener` — base interface, now declares only `didCaptureLabelWithFields(List<LabelField> fields)`.
- `LabelCaptureValidationFlowExtendedListener` — new interface, extends the base and adds:
  - `void didSubmitManualInputForField(LabelField field, String? oldValue, String newValue)` — fires when the user manually corrects or enters a field value.

### Migration

If your existing listener only handles capture, no change is required — it satisfies `LabelCaptureValidationFlowListener`.

If you want to react to manual corrections, switch to the extended listener:

```dart
class _ScanScreenState extends State<ScanScreen>
    implements LabelCaptureValidationFlowExtendedListener {
  @override
  void didCaptureLabelWithFields(List<LabelField> fields) { /* existing */ }

  @override
  void didSubmitManualInputForField(LabelField field, String? oldValue, String newValue) {
    // New in 8.2.
  }
}
```

Bump the package versions:

```yaml
dependencies:
  scandit_flutter_datacapture_core: ^8.2.0
  scandit_flutter_datacapture_barcode: ^8.2.0
  scandit_flutter_datacapture_label: ^8.2.0
```

Then `flutter pub get` and `cd ios && pod install`.

---

## v8.2 → v8.4 — additive `didUpdateValidationFlowResult` listener method (non-breaking)

`LabelCaptureValidationFlowExtendedListener` gained an optional method that fires as the validation flow accumulates partial results during capture. Existing extended listeners continue to compile; Dart will require you to implement `didUpdateValidationFlowResult` if you implement the extended interface.

### What changed

```dart
abstract class LabelCaptureValidationFlowExtendedListener
    extends LabelCaptureValidationFlowListener {
  void didSubmitManualInputForField(LabelField field, String? oldValue, String newValue);
  Future<void> didUpdateValidationFlowResult(
    LabelResultUpdateType type,
    int asyncId,
    List<LabelField> fields,
    Future<FrameData?> Function() getFrameData,
  );
}
```

`LabelResultUpdateType` is a new enum shipped alongside the listener method.

### Migration

Bump versions:

```yaml
dependencies:
  scandit_flutter_datacapture_core: ^8.4.0
  scandit_flutter_datacapture_barcode: ^8.4.0
  scandit_flutter_datacapture_label: ^8.4.0
```

Then `flutter pub get` and `cd ios && pod install`.

If your class implements `LabelCaptureValidationFlowExtendedListener`, add the new method:

```dart
@override
Future<void> didUpdateValidationFlowResult(
  LabelResultUpdateType type,
  int asyncId,
  List<LabelField> fields,
  Future<FrameData?> Function() getFrameData,
) async {
  // Optional — fires multiple times during capture as fields accumulate.
  // Leave the body empty if you don't need fine-grained progress feedback.
}
```

If you only implement the base `LabelCaptureValidationFlowListener`, no code change is required.

### When to add it

Useful only if the user needs fine-grained progress feedback as the Validation Flow accumulates partial results. If they don't ask for that, leave the body empty (you still need the override to satisfy the interface).

### Verify

- Existing `didCaptureLabelWithFields` / `didSubmitManualInputForField` callbacks still fire.
- If you implemented `didUpdateValidationFlowResult`, it fires multiple times during a capture as fields accumulate.
