# SparkScan iOS Migration Guide

## Step 1: Detect the installed SDK version

Before making any changes, find out which version of the Scandit SDK the project currently has installed.

Check in this order:

1. **Swift Package Manager** — open `<ProjectRoot>/Package.resolved` and look for the entry with `"identity": "datacapture-spm"`. The `"version"` field is the installed version.
2. **CocoaPods** — open `Podfile.lock` and look for `ScanditBarcodeCapture` or `ScanditCaptureCore`. The version number is on the same line.

Once you know the installed version, determine which migration path applies:

| Installed version | Target version | Action |
|---|---|---|
| 6.x | 7.x | Apply the **6 → 7 migration** below |
| 7.x | 8.x | Apply the **7 → 8 migration** below |
| 6.x | 8.x | Apply **both migrations in order** (6→7 first, then 7→8) |

If you cannot find `Package.resolved` or `Podfile.lock`, ask the user which version they are migrating from.

---

## Step 2: Update the package version

Before touching source files, update the SDK version in the dependency manager:

- **SPM**: In Xcode → Package Dependencies, update `datacapture-spm` to the target version.
- **CocoaPods**: Update the version constraint in `Podfile`, then run `pod update`.

Ask the user which dependency manager they use if it's not clear from the project.

---

## Step 3: Apply source code changes

Find the files that use SparkScan (search for `SparkScan`, `SparkScanView`, `SparkScanViewSettings`) and apply the relevant changes below directly to those files.

---

## Migration: 6 → 7

### Where these properties live in v6

**On `SparkScanView`** (set on the view instance after it is created):
- All button visibility and color/text properties listed below

**On `SparkScanViewSettings`** (set before creating the view):
- `defaultHandMode` only

When searching the project for these properties, look for usages on both the view instance and the settings object.

### SparkScan API renames

Apply these renames everywhere they appear in the project. These are renames — always replace the old name with the new one, preserving the existing value, regardless of what that value is:

| Old (v6, on `SparkScanView`) | New (v7) |
|---|---|
| `isTorchButtonVisible` | `isTorchControlVisible` |
| `captureButtonBackgroundColor` | `triggerButtonCollapsedColor`, `triggerButtonExpandedColor`, `triggerButtonAnimationColor` (see note) |
| `captureButtonTintColor` | `triggerButtonTintColor` |
| `isFastFindButtonVisible` | `isBarcodeFindButtonVisible` |

> **Note on `captureButtonBackgroundColor`:** v7 splits this into three separate color properties for the collapsed state, expanded state, and animation. If the user set a single color, apply it to all three unless they indicate otherwise.

### SparkScan removed APIs

Remove any usage of these properties — they no longer exist in v7 and will cause compile errors:

- `captureButtonActiveBackgroundColor` (on `SparkScanView`)
- `stopCapturingText`, `startCapturingText`, `resumeCapturingText`, `scanningCapturingText` — the trigger button no longer displays text (on `SparkScanView`)
- `isHandModeButtonVisible` (on `SparkScanView`)
- `defaultHandMode` (on `SparkScanViewSettings`)
- `isSoundModeButtonVisible` (on `SparkScanView`)
- `isHapticModeButtonVisible` (on `SparkScanView`)
- `shouldShowScanAreaGuides` (on `SparkScanView`)

### `triggerButtonCollapseTimeout` default change

The default value changed from `-1` (never collapse) to `5` (collapse after 5 seconds).

- If the project **already sets** `triggerButtonCollapseTimeout` explicitly, leave it as is.
- If the project **does not set it**, do not add it automatically. Instead, inform the user that the button will now collapse after 5 seconds by default and they can set it to `-1` if they want the old behavior.

### New v7 APIs (optional, no action required unless the user wants them)

These are available in v7 — mention them only if the user asks:
- `SparkScanViewState` — sets the initial UI state of the SparkScan view
- `defaultMiniPreviewSize` — configures mini preview dimensions
- `miniPreviewCloseControlVisible` — shows or hides the mini preview close button

### BarcodeTracking → BarcodeBatch rename

If the project uses `BarcodeTracking` (MatrixScan) alongside SparkScan, rename all occurrences to `BarcodeBatch`. The API is otherwise unchanged.

### Scan intention

The default scan intention is now `SMART`. If the project explicitly set `.manual` or another value on `BarcodeCaptureSettings` or `SparkScanSettings`, leave it as is. If the project relied on an explicit `.smart` setting that is now the default, the code still compiles — no change needed.

---

## Migration: 7 → 8

### SparkScan text scanning (beta, opt-in)

v8 adds the ability to scan text alongside barcodes in SparkScan. This is purely additive and opt-in — no existing code breaks. Mention it only if the user asks about new features.

### No other breaking SparkScan changes

The 7→8 migration is light for SparkScan on iOS. The factory-method deprecations listed in the official guide apply to cross-platform SDKs (React Native, Flutter, Capacitor) — not to native Swift.

---

## After applying changes

1. Build the project and fix any remaining compile errors using the API reference (linked in SKILL.md).
2. Let the user know they can check the full list of SDK changes in the official migration guides:
   - 6 → 7: https://docs.scandit.com/sdks/ios/migrate-6-to-7/
   - 7 → 8: https://docs.scandit.com/sdks/ios/migrate-7-to-8/
3. Show the user a summary of only the changes actually made: which files were edited, which properties were renamed/removed, and anything that required a judgment call (e.g., how `captureButtonBackgroundColor` was split). Do not list APIs that were already correct or unchanged.
4. If compile errors persist after the changes above, fetch the [SparkScan API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api.html) to find the correct API before guessing.
