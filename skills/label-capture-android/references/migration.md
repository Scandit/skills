# Label Capture Android Migration Guide

## Migration principles

- **Authority.** When this guide and the API reference disagree, trust the API reference — and a runtime check in the user's project — over this guide. Say which source you followed and why in the summary.
- **Behaviour changes.** Never present a visual or behaviour change (new default, different overlay look, changed feedback, changed scan timing) as a 1:1 rename. List each one in the summary as a judgment call the user must confirm.
- **Compatibility layer.** When the scanning code sits behind a shared scanner library or wrapper that other code calls, keep that library's public API frozen (same types, method names, callbacks) and change only the Scandit calls underneath.
- **Dual-version code.** Code that names a symbol removed in the target version does not compile against it, so this platform cannot probe for it at run time. Select the code path at build time instead — conditional compilation, a build flavor, or a version constant read from the dependency manifest — and never on the presence of the new API. A deprecated symbol that still compiles proves nothing about the installed version.

When a user asks to upgrade or migrate a Label Capture integration, identify which version boundary they're crossing. Prefer reading `app/build.gradle` or `app/build.gradle.kts` for the current `com.scandit.datacapture:label` version. Otherwise ask directly: "Which version are you on, and which version are you upgrading to?"

The sections below are cumulative — if the user is going from v7 to v8, apply §1. Walk through each applicable section in order.

## 1. v7 → v8 — `LabelFieldDefinition` regex builder renames (breaking)

At the v7 → v8 major version bump, the regex-configuration methods on every field builder were renamed. The old method names no longer exist from v8.0 onwards.

| Old (v7.x) | New (v8.0+) |
| --- | --- |
| `setPattern(pattern)` | `setValueRegex(regex)` |
| `setPatterns(patterns)` | `setValueRegexes(vararg regex)` |
| `setDataTypePattern(pattern)` | `setAnchorRegex(regex)` |
| `setDataTypePatterns(patterns)` | `setAnchorRegexes(vararg regex)` |

The same rename applies to the matching setter methods on every field builder (`CustomTextBuilder`, `ExpiryDateTextBuilder`, `TotalPriceTextBuilder`, `WeightTextBuilder`, etc.).

**Important — argument style change for the multi-value methods:** The old `setPatterns` and `setDataTypePatterns` accepted a `List<String>`. The new vararg equivalents accept individual string arguments. When migrating, unwrap any `listOf(...)` call:

```kotlin
// Before (v7.x) — List<String>
.setDataTypePatterns(listOf("LOT[:\\s]+", "Batch[:\\s]+"))
.setDataTypePattern(Regex("EXP[:\\s]+"))
.setPatterns(listOf("[A-Z0-9]{6,}"))
.setPattern(Regex("\\d{2}/\\d{2}/\\d{2,4}"))

// After (v8.0+) — vararg String
.setAnchorRegexes("LOT[:\\s]+", "Batch[:\\s]+")
.setAnchorRegex(Regex("EXP[:\\s]+"))
.setValueRegexes("[A-Z0-9]{6,}")
.setValueRegex(Regex("\\d{2}/\\d{2}/\\d{2,4}"))
```

If the patterns were stored in a variable (e.g. `val patterns: List<String>`), use the spread operator: `.setAnchorRegexes(*patterns.toTypedArray())`.

### Before (v7.x)

```kotlin
LabelCaptureSettings.builder()
    .addLabel()
        .addExpiryDateText()
            .setDataTypePattern("EXP[:\\s]+")
            .setPattern("\\d{2}/\\d{2}/\\d{2,4}")
        .buildFluent("expiry-date")
        .addCustomText()
            .setDataTypePatterns(listOf("LOT[:\\s]+", "Batch[:\\s]+"))
            .setPatterns(listOf("[A-Z0-9]{6,}"))
            .isOptional(true)
        .buildFluent("lot-number")
    .buildFluent("shipping-label")
    .build()
```

### After (v8.0+)

```kotlin
LabelCaptureSettings.builder()
    .addLabel()
        .addExpiryDateText()
            .setAnchorRegex("EXP[:\\s]+")
            .setValueRegex("\\d{2}/\\d{2}/\\d{2,4}")
        .buildFluent("expiry-date")
        .addCustomText()
            .setAnchorRegexes("LOT[:\\s]+", "Batch[:\\s]+")
            .setValueRegexes("[A-Z0-9]{6,}")
            .isOptional(true)
        .buildFluent("lot-number")
    .buildFluent("shipping-label")
    .build()
```

Apply the rename across every field builder in the user's codebase. No other logic changes. If the user is already on v8.0 or later, this section does not apply.

## 2. v8.1 → v8.2 — Validation Flow 2.0 keyboard inset handling

In SDK 8.2, the Validation Flow overlay gained a new property for keyboard (IME) inset management. This matters because Android 15 enforces edge-to-edge display, meaning apps are now responsible for handling the space the keyboard occupies when it appears — the system no longer adjusts layouts automatically.

**New property:** `LabelCaptureValidationFlowOverlay.shouldHandleKeyboardInsetsInternally: Boolean` (default: `false`)

### What this means in practice

- **Default (`false`):** The overlay does nothing special for keyboard insets. Your app is responsible for handling them in a parent view of `DataCaptureView`. Use any standard Android approach:
  - `android:fitsSystemWindows="true"` on a parent layout in XML
  - A `WindowInsetsListenerCompat` that applies padding
  - `Modifier.imePadding()` in Compose

- **Set to `true`:** The overlay handles keyboard insets internally. Use this if you're seeing the manual-entry input field appear behind the keyboard and you don't want to manage insets yourself.

### When to apply this migration

If after upgrading to SDK 8.2+ on an Android 15 device the keyboard covers the text input in the Validation Flow, add one of the following:

**Option A — let the overlay handle it (simplest):**

```kotlin
validationFlowOverlay.shouldHandleKeyboardInsetsInternally = true
```

Set this before or after calling `applySettings()` — order doesn't matter.

**Option B — handle insets in the layout (recommended for apps that already manage insets):**

```xml
<!-- In your layout XML, on a parent of the DataCaptureView container -->
<FrameLayout
    android:id="@+id/data_capture_container"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:fitsSystemWindows="true" />
```

Option B is preferred when your app already has an inset strategy, so the overlay doesn't interfere with it. Option A is the quick fix when you just want things to work.

If the user is not using the Validation Flow, or is not targeting Android 15, this section does not apply.
