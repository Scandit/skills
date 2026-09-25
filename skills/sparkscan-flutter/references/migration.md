# SparkScan Flutter Migration Guide

## Step 1: Detect the installed SDK version

Before making any changes, find out which version of the Scandit Flutter packages the project currently has installed.

Check in this order:

1. **`pubspec.yaml`** — look for `scandit_flutter_datacapture_core` and/or `scandit_flutter_datacapture_barcode` under `dependencies:`. The value next to them is the installed version constraint (e.g. `^6.28.0`, `^7.6.0`, `^8.0.0`).
2. **`pubspec.lock`** — if `pubspec.yaml` only has a range, check the lockfile for the exact resolved version.

Once you know the installed version, determine which migration path applies:

| Installed version | Target version | Action |
|---|---|---|
| 6.x | 7.x | Apply the **6 → 7 migration** below |
| 7.x | 8.x | Apply the **7 → 8 migration** below |
| 6.x | 8.x | Apply **both migrations in order** (6→7 first, then 7→8) |

If neither package is in `pubspec.yaml`, the project is not using SparkScan on Flutter yet — fall back to `references/integration.md` instead of migrating.

---

## Step 2: Update the package version

Before touching source files, update the Scandit package versions in `pubspec.yaml`:

```yaml
dependencies:
  scandit_flutter_datacapture_barcode: ^8.0.0
  # scandit_flutter_datacapture_core is pulled in transitively — declare it
  # explicitly only if the project already does.
```

Then install:

```bash
flutter pub get
```

On iOS, `flutter pub get` updates the generated `Generated.xcconfig` and the Podfile resolves transitively on the next build. If the project uses a custom iOS setup, run `cd ios && pod install` manually. On Android, Gradle resolves the new versions on the next `flutter build` or `flutter run`.

If any part of the app uses method channels directly against the Scandit native layer (rare), rebuild both platforms (`flutter clean && flutter pub get`) to purge stale artifacts.

---

## Step 3: Apply source code changes

Find the files that use SparkScan (search the project for `SparkScan`, `SparkScanView`, `SparkScanSettings`, `SparkScanViewSettings`) and apply the relevant changes below directly to those files.

---

## Migration: 6 → 7

### Where these properties live in v6

**On `SparkScanView`** (set on the view instance or via constructor named parameters):
- All button visibility, color, and text properties listed below.
- `brush` (deprecated in v7 — moved to `SparkScanBarcodeFeedback` via the feedback delegate).

**On `SparkScanViewSettings`** (passed to the view factory):
- `defaultHandMode` only.

When searching the project for these properties, look for usages on both the view instance and the settings object.

### SparkScanView property renames

Apply these renames everywhere they appear in the project. These are renames — always replace the old name with the new one, preserving the existing value, regardless of what that value is:

| Old (v6, on `SparkScanView`) | New (v7) |
|---|---|
| `torchButtonVisible` | `torchControlVisible` |
| `captureButtonBackgroundColor` | `triggerButtonCollapsedColor`, `triggerButtonExpandedColor`, `triggerButtonAnimationColor` (see note) |
| `captureButtonTintColor` | `triggerButtonTintColor` |
| `fastFindButtonVisible` | `barcodeFindButtonVisible` |

> **Note on `captureButtonBackgroundColor`:** v7 splits this single property into three separate color properties — one for the collapsed trigger-button state, one for the expanded state, and one for the animation. If the project set a single color, apply it to all three unless the user indicates otherwise.

### SparkScanViewUiListener rename

- `didTapFastFindButton(SparkScanView view)` → `didTapBarcodeFindButton(SparkScanView view)`

Rename the override in any class implementing `SparkScanViewUiListener`.

### SparkScanView removed APIs

Remove any usage of these properties — they no longer exist in v7 and will cause analyzer/runtime errors:

- `brush` (on `SparkScanView`) — the highlight brush is now specified per barcode via `SparkScanBarcodeFeedback` returned from `SparkScanFeedbackDelegate.feedbackForBarcode`.
- `captureButtonActiveBackgroundColor` (on `SparkScanView`)
- `stopCapturingText`, `startCapturingText`, `resumeCapturingText`, `scanningCapturingText` — the trigger button no longer displays text (on `SparkScanView`)
- `handModeButtonVisible` (on `SparkScanView`) — the trigger is now fully floating
- `defaultHandMode` (on `SparkScanViewSettings`)
- `soundModeButtonVisible` (on `SparkScanView`)
- `hapticModeButtonVisible` (on `SparkScanView`)
- `shouldShowScanAreaGuides` (on `SparkScanView`)

### `triggerButtonCollapseTimeout` default change

The default value changed from `-1` (never collapse) to `5` (collapse after 5 seconds).

- If the project **already sets** `triggerButtonCollapseTimeout` explicitly, leave it as is.
- If the project **does not set it**, do not add it automatically. Instead, tell the user that the trigger button will now collapse after 5 seconds by default and that they can set the property to `-1` to restore the old always-expanded behavior.

### New v7 APIs (optional, no action required unless the user wants them)

These are available in v7 — mention them only if the user asks:
- `triggerButtonVisible` — hide/show the trigger button entirely
- `triggerButtonImage` / `setTriggerButtonImage(Uint8List)` — custom trigger button artwork
- `SparkScanViewState` — controls the initial UI state of the view
- `defaultMiniPreviewSize` — configures mini-preview dimensions
- `miniPreviewCloseControlVisible` — shows/hides the mini-preview close button
- `SparkScanFeedbackDelegate` / `feedbackDelegate` on the view — per-barcode feedback customization (replaces the v6 `brush` / sound APIs)

### BarcodeTracking → BarcodeBatch rename

If the project uses `BarcodeTracking` (MatrixScan) alongside SparkScan, rename all occurrences to `BarcodeBatch`. Imports from `scandit_flutter_datacapture_barcode` need updating. The API is otherwise unchanged.

### Scan intention default change

The default scan intention is now `ScanIntention.smart`. If the project explicitly set `ScanIntention.manual` or another value on `BarcodeCaptureSettings` or `SparkScanSettings`, leave it as is. If the project relied on an explicit `smart` setting that is now the default, the code still works — no change needed.

---

## Migration: 7 → 8

The v7→v8 step on Flutter is much smaller than on the JavaScript-based frameworks (Capacitor, Cordova, React Native) because Flutter kept more of its v6 API surface as factory forwarders.

### Capture mode constructor: `SparkScan.withSettings` → `SparkScan(settings: ...)`

The deprecated-in-v7 factory is removed in v8. Construct the mode directly instead.

**v7 (deprecated):**
```dart
final sparkScan = SparkScan.withSettings(sparkScanSettings);
```

**v8:**
```dart
final sparkScan = SparkScan(settings: sparkScanSettings);
```

### `ExtendedSparkScanViewUiListener` → `SparkScanViewUiExtendedListener`

If any class extends or implements `ExtendedSparkScanViewUiListener` (introduced in v7 for the mode-change callback), rename it to `SparkScanViewUiExtendedListener`. The callback surface is otherwise the same.

### Async lifecycle

`SparkScanView.pauseScanning()` and `SparkScanView.stopScanning()` now return `Future<void>`. If the project calls them synchronously, they still work (fire-and-forget), but `await` them for deterministic ordering — especially in test helpers or lifecycle transitions that must complete before another scan starts.

```dart
await sparkScanView.pauseScanning();
await sparkScanView.stopScanning();
```

### `DataCaptureContext.forLicenseKey` — still valid

Unlike Capacitor / Cordova / React Native, the Flutter SDK keeps `DataCaptureContext.forLicenseKey(licenseKey)` as a factory in v8 (it forwards to `DataCaptureContext.initialize(licenseKey)`). **No rename is required for this call.** Either form works in both v7 and v8.

### New v8 APIs (optional, no action required unless the user wants them)

Available in v8 on `SparkScanView` — mention only if the user asks:
- `labelCaptureButtonVisible` — toggles the label-capture entry point in the toolbar
- `toolbarBackgroundColor`, `toolbarIconActiveTintColor`, `toolbarIconInactiveTintColor` — full toolbar color theming
- `previewCloseControlVisible` — shows/hides the mini-preview close control
- `zoomSwitchControlVisible` — shows/hides the zoom switch
- `cameraSwitchButtonVisible` — shows/hides the front/back camera switch
- `SparkScanFeedbackExtendedDelegate` — extends feedback to USI / item-based scanning
- Text scanning in SparkScan (beta, opt-in) — v8 adds the ability to scan text alongside barcodes; purely additive, no existing code breaks

---

## After applying changes

1. Run `flutter pub get` again after any additional package changes triggered by the migration.
2. Run `flutter analyze` to catch lingering references to renamed or removed APIs.
3. Build the iOS and Android apps (`flutter run` on both) and fix any remaining compile / runtime errors using the API reference (linked in `SKILL.md`).
4. Let the user know they can check the full list of SDK changes in the official migration guides:
   - 6 → 7: https://docs.scandit.com/sdks/flutter/migrate-6-to-7/
   - 7 → 8: https://docs.scandit.com/sdks/flutter/migrate-7-to-8/
5. Show the user a summary of only the changes actually made: which files were edited, which properties were renamed/removed, and anything that required a judgment call (e.g. how `captureButtonBackgroundColor` was split across three v7 properties, or whether the `brush` property was migrated to a `feedbackDelegate`). Do not list APIs that were already correct or unchanged.
6. If compile errors persist after the changes above, fetch the SparkScan API reference (https://docs.scandit.com/data-capture-sdk/flutter/barcode-capture/api.html) to find the correct API before guessing.
