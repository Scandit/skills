# MatrixScan Batch Flutter Migration Guide

This guide covers upgrading an existing MatrixScan / BarcodeBatch Flutter integration across Scandit SDK major versions. The headline change for this mode is the **`BarcodeTracking` → `BarcodeBatch` rename** in v7, followed by the **context-free constructor** change in v8.

## Step 1: Detect the installed SDK version

Before making any changes, find out which version of the Scandit Flutter packages the project currently has installed.

Check in this order:

1. **`pubspec.yaml`** — look for `scandit_flutter_datacapture_core` and/or `scandit_flutter_datacapture_barcode` under `dependencies:`. The value next to them is the installed version constraint (e.g. `^6.28.0`, `^7.6.0`, `^8.0.0`).
2. **`pubspec.lock`** — if `pubspec.yaml` only has a range, check the lockfile for the exact resolved version.

A strong signal of a **v6** integration is the legacy MatrixScan API: any `BarcodeTracking*` symbol, or an import of `scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_tracking.dart`.

Once you know the installed version, determine which migration path applies:

| Installed version | Target version | Action |
|---|---|---|
| 6.x | 7.x | Apply the **6 → 7 migration** below |
| 7.x | 8.x | Apply the **7 → 8 migration** below |
| 6.x | 8.x | Apply **both migrations in order** (6→7 first, then 7→8) |

If the project does not use `BarcodeTracking`/`BarcodeBatch` on Flutter yet, fall back to `references/integration.md` instead of migrating.

---

## Step 2: Update the package version

Before touching source files, update the Scandit package version in `pubspec.yaml`:

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

On iOS, `flutter pub get` updates the generated config and the Podfile resolves transitively on the next build (run `cd ios && pod install` manually for custom setups). On Android, Gradle resolves on the next `flutter build` / `flutter run`.

---

## Step 3: Apply source code changes

Find the files that use the MatrixScan mode (search the project for `BarcodeTracking`, `BarcodeBatch`, `*Settings`, `*BasicOverlay`, `*Listener`, `*Session`) and apply the relevant changes below directly to those files.

---

## Migration: 6 → 7

### BarcodeTracking → BarcodeBatch rename (the main change)

In v7 the MatrixScan mode was renamed from `BarcodeTracking` to `BarcodeBatch`. Rename **every** `BarcodeTracking*` symbol to its `BarcodeBatch*` equivalent:

| v6 symbol | v7 symbol |
|---|---|
| `BarcodeTracking` | `BarcodeBatch` |
| `BarcodeTrackingSettings` | `BarcodeBatchSettings` |
| `BarcodeTrackingSession` | `BarcodeBatchSession` |
| `BarcodeTrackingListener` | `BarcodeBatchListener` |
| `BarcodeTrackingBasicOverlay` | `BarcodeBatchBasicOverlay` |
| `BarcodeTrackingBasicOverlayListener` | `BarcodeBatchBasicOverlayListener` |
| `BarcodeTrackingBasicOverlayStyle` | `BarcodeBatchBasicOverlayStyle` |
| `BarcodeTrackingAdvancedOverlay` | `BarcodeBatchAdvancedOverlay` |
| `BarcodeTrackingAdvancedOverlayListener` | `BarcodeBatchAdvancedOverlayListener` |
| `BarcodeTrackingAdvancedOverlayWidget` | `BarcodeBatchAdvancedOverlayWidget` |
| `BarcodeTrackingAdvancedOverlayWidgetState` | `BarcodeBatchAdvancedOverlayWidgetState` |

Also update the **import barrel**:

**v6:**
```dart
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_tracking.dart';
```

**v7:**
```dart
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_batch.dart';
```

The listener method (`didUpdateSession`), session properties (`addedTrackedBarcodes`, `trackedBarcodes`, `removedTrackedBarcodes`), and overlay styles (`.frame` / `.dot`) keep the same shape — only the class-name prefix changes.

### `BarcodeBatch.forContext` is still valid in v7 (legacy form)

After the rename, `BarcodeBatch.forContext(context, settings)` continues to work in v7 but is the legacy form. The recommended v7 form is `BarcodeBatch(settings)` followed by `dataCaptureContext.setMode(barcodeBatch)`. You do **not** have to migrate this in the 6→7 step — it becomes mandatory in 7→8 (see below).

### New v7 APIs (optional, no action required unless the user wants them)

- `BarcodeBatch.createRecommendedCameraSettings()` — static **method** returning the recommended `CameraSettings` for BarcodeBatch (flutter ≥7.6). Note: it is a method with `()`, **not** a `recommendedCameraSettings` getter on Flutter.
- `BarcodeBatch(settings)` constructor (flutter ≥7.6) — replaces the `BarcodeBatch.forContext(...)` factory.

---

## Migration: 7 → 8

### Capture mode constructor: `BarcodeBatch.forContext(...)` → `BarcodeBatch(settings)` + `setMode`

The legacy factory is removed in v8. Construct the mode directly and register it with the context.

**v7 (legacy):**
```dart
final barcodeBatch = BarcodeBatch.forContext(dataCaptureContext, settings);
```

**v8:**
```dart
final barcodeBatch = BarcodeBatch(settings);
dataCaptureContext.setMode(barcodeBatch);
```

`dataCaptureContext.setMode(barcodeBatch)` removes any other modes already attached and adds the new one in a single call. `dataCaptureContext.addMode(barcodeBatch)` is the multi-mode equivalent.

### Camera settings: prefer `BarcodeBatch.createRecommendedCameraSettings()`

If the project hand-rolled `CameraSettings()` (for example `..preferredResolution = VideoResolution.uhd4k`), replace it with the recommended preset:

```dart
final cameraSettings = BarcodeBatch.createRecommendedCameraSettings();
camera?.applySettings(cameraSettings);
```

> **Flutter gotcha**: use the static **method** `BarcodeBatch.createRecommendedCameraSettings()`. There is no `recommendedCameraSettings` getter on Flutter — the getter form exists only on iOS / web / .NET.

### `DataCaptureContext.forLicenseKey` — still valid

Unlike Capacitor / Cordova / React Native, the Flutter SDK keeps `DataCaptureContext.forLicenseKey(licenseKey)` as a factory in v8 (it forwards to `DataCaptureContext.initialize(licenseKey)`). **No rename is required for this call.** Either form works in both v7 and v8.

### Advanced overlay method names (unchanged, but verify)

On Flutter the advanced-overlay imperative methods are `setWidgetForTrackedBarcode` (not `setViewForTrackedBarcode`) and `clearTrackedBarcodeWidgets` (not `clearTrackedBarcodeViews`). These names are stable across v7→v8 — if the project already uses them, no change is needed.

---

## After applying changes

1. Run `flutter pub get` again after any additional package changes triggered by the migration.
2. Run `flutter analyze` to catch lingering references to renamed or removed APIs (e.g. a stray `BarcodeTracking*` symbol or the old `..._barcode_tracking.dart` import).
3. Build the iOS and Android apps (`flutter run` on both) and fix any remaining compile / runtime errors using the API reference (linked in `SKILL.md`).
4. Let the user know they can check the full list of SDK changes in the official migration guides:
   - 6 → 7: https://docs.scandit.com/sdks/flutter/migrate-6-to-7/
   - 7 → 8: https://docs.scandit.com/sdks/flutter/migrate-7-to-8/
5. Show the user a summary of only the changes actually made: which files were edited, which symbols were renamed (`BarcodeTracking*` → `BarcodeBatch*`), how the constructor was rewritten (`forContext` → `BarcodeBatch(settings) + setMode`), and any judgment calls. Do not list APIs that were already correct or unchanged.
6. If compile errors persist, fetch the BarcodeBatch API reference (https://docs.scandit.com/data-capture-sdk/flutter/barcode-capture/api.html) to find the correct API before guessing.
