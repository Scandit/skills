# Label Capture iOS Migration Guide

When a user asks to upgrade or migrate a Label Capture integration, identify which version boundary they're crossing. Prefer reading `Package.resolved` (or the project's SPM pinning) for the resolved `datacapture-spm` version. Otherwise ask directly: "Which version are you on, and which version are you upgrading to?"

The sections below are cumulative — if the user is going from v7 to v8.x, apply §1 first. Walk through each applicable section in order.

## 1. v7 → v8 — `LabelFieldDefinition` regex builder renames (breaking)

At the v7 → v8 major version bump, the regex-configuration methods on every field builder were renamed. The old method names no longer exist from v8.0 onwards.

| Old (v7.x) | New (v8.0+) |
| --- | --- |
| `setPattern(_:)` | `valueRegex(_:)` |
| `setPatterns(_:)` | `valueRegexes(_:)` |
| `setDataTypePattern(_:)` | `anchorRegex(_:)` |
| `setDataTypePatterns(_:)` | `anchorRegexes(_:)` |

The same rename applies to the matching setter methods on every field builder (`CustomText`, `ExpiryDateText`, `TotalPriceText`, `WeightText`, etc.).

### Before (v7.x)

```swift
let settings = try LabelCaptureSettings {
    LabelDefinition("Shipping Label") {
        ExpiryDateText(name: "Expiry Date")
            .setDataTypePattern("EXP[:\\s]+")
            .setPattern("\\d{2}/\\d{2}/\\d{2,4}")

        CustomText(name: "Lot Number")
            .setDataTypePatterns(["LOT[:\\s]+", "Batch[:\\s]+"])
            .setPatterns(["[A-Z0-9]{6,}"])
            .optional(true)
    }
}
```

### After (v8.0+)

```swift
let settings = try LabelCaptureSettings {
    LabelDefinition("Shipping Label") {
        ExpiryDateText(name: "Expiry Date")
            .anchorRegex("EXP[:\\s]+")
            .valueRegex("\\d{2}/\\d{2}/\\d{2,4}")

        CustomText(name: "Lot Number")
            .anchorRegexes(["LOT[:\\s]+", "Batch[:\\s]+"])
            .valueRegexes(["[A-Z0-9]{6,}"])
            .optional(true)
    }
}
```

Apply the rename across every field builder in the user's codebase. No other logic changes. If the user is already on v8.0 or later, this section does not apply.

## 2. v8.0 → v8.1 — Swift ergonomics + optional delegate method (additive, non-breaking)

Three additive changes ship in v8.1. Existing v8.0 integrations continue to compile, but users may want to adopt the new shapes.

### (a) Result-builder DSL for `LabelDefinition`

v8.1 introduces the Swift result-builder form `LabelCaptureSettings { LabelDefinition("...") { ... } }`. Pre-8.1 codebases that built settings via the array-based initializer can switch to the DSL — it's the canonical shape used throughout this skill's integration guide. Both forms are supported in 8.1+; migration is stylistic.

```swift
// Pre-8.1 — array-based initializer (still works)
let labelDef = LabelDefinition(
    name: "Perishable Product",
    fields: [
        CustomBarcode(name: "Barcode", symbologies: [.ean13UPCA]),
        ExpiryDateText(name: "Expiry Date"),
    ]
)
let settings = try LabelCaptureSettings(labelDefinitions: [labelDef])

// 8.1+ — result-builder DSL (preferred)
let settings = try LabelCaptureSettings {
    LabelDefinition("Perishable Product") {
        CustomBarcode(name: "Barcode", symbologies: [.ean13UPCA])
        ExpiryDateText(name: "Expiry Date")
    }
}
```

### (b) `Symbology` enum auto-bridging

Pre-8.1 required boxing symbologies in `NSNumber` because the Obj-C bridge couldn't import the Swift enum directly. From v8.1 the enum cases are bridged and can be passed as-is.

```swift
// Pre-8.1 — NSNumber boxing required
CustomBarcode(
    name: "Barcode",
    symbologies: [NSNumber(value: Symbology.ean13UPCA.rawValue)]
)

// 8.1+ — pass enum cases directly
CustomBarcode(name: "Barcode", symbologies: [.ean13UPCA])
```

Unwrap any `NSNumber(value: Symbology.X.rawValue)` calls in the user's codebase when upgrading.

### (c) Optional `didSubmitManualInputFor` delegate method

`LabelCaptureValidationFlowDelegate` gains an optional method that fires when the user manually submits a value for a field through the validation-flow UI.

```swift
extension ScanViewController: LabelCaptureValidationFlowDelegate {
    // existing didCaptureLabelWith: stays here

    func labelCaptureValidationFlowOverlay(
        _ overlay: LabelCaptureValidationFlowOverlay,
        didSubmitManualInputFor field: LabelField,
        replacingValue oldValue: String?,
        withValue newValue: String
    ) {
        // Fires when the user manually enters or corrects a value via the VF input.
    }
}
```

Only add this if the user needs to react to manual-entry events (e.g. log them, validate against a back-end, update analytics). If they don't ask for that behaviour, leave the delegate alone — the method is optional.

## 3. v8.1 → v8.2 — Validation Flow 2.0 + optional `didUpdateResult` delegate method

Two things change between 8.1 and 8.2.

**(a) Validation Flow UI redesign (visual, non-breaking).** The `LabelCaptureValidationFlowOverlay` and `LabelCaptureValidationFlowSettings` API surface is the same — existing code keeps compiling — but the visual layout, brush behaviour, and adaptive-recognition hints were overhauled. Rebuild and re-test the integration against the new visuals; no code changes are required unless the user wants the new placeholder-text API.

**(b) New optional `didUpdateResult` delegate method (additive, non-breaking).** `LabelCaptureValidationFlowDelegate` gains a method that fires when validation-flow results are updated during capture, with an optional `FrameData`:

```swift
extension ScanViewController: LabelCaptureValidationFlowDelegate {
    // existing didCaptureLabelWith: stays here

    func labelCaptureValidationFlowOverlay(
        _ overlay: LabelCaptureValidationFlowOverlay,
        didUpdateResult type: LabelResultUpdateType,
        asyncId: Int,
        fields: [LabelField],
        frameData: FrameData?
    ) {
        // Progressive update — useful for live progress UI or capturing the frame image.
    }
}
```

**New API in v8.2+ on `LabelCaptureValidationFlowSettings`:** `setPlaceholderText(_:forLabelDefinition:)` — sets per-field placeholder text shown inside the manual-entry input.

```swift
let validationFlowSettings = LabelCaptureValidationFlowSettings()
validationFlowSettings.setPlaceholderText("MM/DD/YYYY", forLabelDefinition: "Expiry Date")
validationFlowSettings.setPlaceholderText("e.g., $13.66", forLabelDefinition: "Total Price")
validationFlowOverlay.apply(validationFlowSettings)
```

### When to add `didUpdateResult`

If the user needs progressive feedback (live progress UI, capturing the frame image alongside the VF result), implement it. If not, leave the delegate alone — the method is optional. If the user is not using the Validation Flow, this section does not apply.

## 4. v8.3 → v8.4 — `LabelDateResult` numeric components became `Int?` (breaking for callers that read them)

In v8.4 the Swift bridge for `LabelDateResult.day`, `LabelDateResult.month`, and `LabelDateResult.year` changed from non-optional `Int` (with `-1` as the "not parsed" sentinel) to `Int?` (where `nil` is "not parsed"). The `dayString` / `monthString` / `yearString` properties are unchanged — non-optional `String` in every version.

This is breaking for any code that reads the numeric components directly. Old code that compiled on v8.3 will not compile on v8.4 (and vice versa).

### Before (v8.0–v8.3) — non-optional `Int`, `-1` sentinel

```swift
extension LabelDateResult {
    func toDate(calendar: Calendar = .current) -> Date? {
        guard day != -1, month != -1, year != -1 else { return nil }
        return calendar.date(from: DateComponents(year: year, month: month, day: day))
    }
}
```

### After (v8.4+) — `Int?`, `nil` sentinel

```swift
extension LabelDateResult {
    func toDate(calendar: Calendar = .current) -> Date? {
        guard let day, let month, let year else { return nil }
        return calendar.date(from: DateComponents(year: year, month: month, day: day))
    }
}
```

When migrating, replace every `value != -1` sentinel check with `if let` / `guard let`, and remove any `String.init` or arithmetic that assumed the components were non-optional `Int`. Conversely, if the agent emits an `if let day = result.day` on a pre-v8.4 SDK, the compile error will be `Initializer for conditional binding must have Optional type, not 'Int'`. The reverse error on v8.4+ is `Value of type 'Int?' has no member ...` or `Value of type 'Int' has no member 'map'` if the code used `.map` after force-promoting through `?? 0`.

If the user is not reading the numeric components — i.e. they only use `dayString` / `monthString` / `yearString`, or they never call `asDate()` — this section does not apply.

## 5. ARE — Adaptive Recognition Engine (opt-in, no version migration)

ARE is an additive feature, not a migration. Enable it only if the user explicitly asks for better OCR on difficult labels, and only after confirming they understand the constraints:

- Overlay-agnostic — set via `.adaptiveRecognition(.auto)` on the `LabelDefinition`; works with the Basic, Advanced, or Validation Flow overlay alike. The inline modifier requires iOS SDK 8.0+ (the always-on `.on` mode, 8.4+); on an older SDK it will not compile.
- Enabled by Scandit on your subscription, not self-served — the Adaptive Recognition Engine entitlement is provisioned server-side and rides in your license key (trial keys available for evaluation; for production contact <support@scandit.com>). A standard key does not carry it; there is no flag for the user to toggle themselves.
- Currently in Beta.

Enable via `.adaptiveRecognition(.auto)` on the `LabelDefinition` — see the integration guide for details. Do not enable this as part of a routine SDK upgrade.
