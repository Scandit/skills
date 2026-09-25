# BarcodeCapture Flutter Migration Guide

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

If neither package is in `pubspec.yaml`, the project is not using BarcodeCapture on Flutter yet — fall back to `references/integration.md` instead of migrating.

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

Find the files that use BarcodeCapture (search the project for `BarcodeCapture`, `BarcodeCaptureSettings`, `BarcodeCaptureOverlay`, `BarcodeCaptureListener`) and apply the relevant changes below directly to those files.

---

## Migration: 6 → 7

The v6→v7 step on Flutter is small for BarcodeCapture itself — most of the surface (settings, listener, session, overlay) is unchanged. The two behavioural deltas are scan intention and composite codes.

### Scan intention default change

The default scan intention is now `ScanIntention.smart` from v7. Most projects need no action.

- If the project already explicitly sets `ScanIntention.manual` or another value on `BarcodeCaptureSettings`, leave it as is.
- If the project relies on a single-image frame source, you must set `scanIntention = ScanIntention.manual` — Smart is incompatible with single-frame sources.
- If the project did not set the property at all, scanning now uses the Smart Scan algorithm by default. This is generally desirable; mention it to the user but do not change the code.

### Composite codes default change

Default support for Composite Codes was removed when Smart Scan is enabled. If the project scans composite codes (CC-A, CC-B, CC-C), explicitly enable them in the capture settings:

```dart
settings.enableSymbologiesForCompositeTypes({CompositeType.a, CompositeType.b});
settings.enabledCompositeTypes = {CompositeType.a, CompositeType.b};
```

If the project does not use composite codes, no action is needed.

### BarcodeTracking → BarcodeBatch rename

If the project uses `BarcodeTracking` (MatrixScan) alongside BarcodeCapture, rename all occurrences to `BarcodeBatch`. Imports from `scandit_flutter_datacapture_barcode` need updating. The API is otherwise unchanged.

### `BarcodeCapture.forContext` is still valid in v7 (deprecated form)

`BarcodeCapture.forContext(context, settings)` continues to work in v7 but is the legacy form. The recommended v7 form is `BarcodeCapture(settings)` followed by `dataCaptureContext.addMode(barcodeCapture)`. You do not have to migrate this in the 6→7 step — it is mandatory in 7→8 (see below).

### New v7 APIs (optional, no action required unless the user wants them)

- `BarcodeCapture.createRecommendedCameraSettings()` — static helper returning the recommended `CameraSettings` for BarcodeCapture.
- `BarcodeCapture(settings)` constructor — replaces the `BarcodeCapture.forContext(...)` factory.
- `BarcodeCaptureOverlay(barcodeCapture)` constructor — pair with `view.addOverlay(overlay)` for explicit wiring.

---

## Migration: 7 → 8

### Capture mode constructor: `BarcodeCapture.forContext(...)` → `BarcodeCapture(settings)` + `addMode`

The deprecated-in-v7 factory is removed in v8. Construct the mode directly and add it to the context.

**v7 (deprecated):**
```dart
final barcodeCapture = BarcodeCapture.forContext(dataCaptureContext, settings);
```

**v8:**
```dart
final barcodeCapture = BarcodeCapture(settings);
dataCaptureContext.addMode(barcodeCapture);
```

If the project only uses one mode at a time, `dataCaptureContext.setMode(barcodeCapture)` is also acceptable — it removes any other modes already attached and adds the new one in a single call.

### Overlay constructor: `BarcodeCaptureOverlay.withBarcodeCaptureForView(mode, view)` removed

The `BarcodeCaptureOverlay.withBarcodeCaptureForView(mode, view)` factory was removed in v8. Construct the overlay with the standalone `BarcodeCaptureOverlay(mode)` constructor and attach it to the view explicitly:

**v7 (removed in v8):**
```dart
final overlay = BarcodeCaptureOverlay.withBarcodeCaptureForView(barcodeCapture, captureView);
```

**v8:**
```dart
final overlay = BarcodeCaptureOverlay(barcodeCapture);
captureView.addOverlay(overlay);
```

### Camera resolution: `VideoResolution.auto` deprecated

`VideoResolution.auto` is deprecated. If the project uses it, switch to the recommended preset:

```dart
await camera.applySettings(BarcodeCapture.createRecommendedCameraSettings());
```

If the project already uses `BarcodeCapture.createRecommendedCameraSettings()`, no action is needed.

### `DataCaptureContext.forLicenseKey` — still valid

Unlike Capacitor / Cordova / React Native, the Flutter SDK keeps `DataCaptureContext.forLicenseKey(licenseKey)` as a factory in v8 (it forwards to `DataCaptureContext.initialize(licenseKey)`). **No rename is required for this call.** Either form works in both v7 and v8.

### New v8 APIs (optional, no action required unless the user wants them)

- `dataCaptureContext.setMode(mode)` — replaces all attached modes with the provided one in a single call.
- `SelectionMode` on `BarcodeCaptureSettings` — replaces the v7 `ScanIntention.smartSelection` value with explicit `SelectionMode.off / on / auto` semantics.

---

## After applying changes

1. Run `flutter pub get` again after any additional package changes triggered by the migration.
2. Run `flutter analyze` to catch lingering references to renamed or removed APIs.
3. Build the iOS and Android apps (`flutter run` on both) and fix any remaining compile / runtime errors using the API reference (linked in `SKILL.md`).
4. Let the user know they can check the full list of SDK changes in the official migration guides:
   - 6 → 7: https://docs.scandit.com/sdks/flutter/migrate-6-to-7/
   - 7 → 8: https://docs.scandit.com/sdks/flutter/migrate-7-to-8/
5. Show the user a summary of only the changes actually made: which files were edited, which factories / properties were renamed/removed, and anything that required a judgment call (e.g. how `BarcodeCapture.forContext` was rewritten as `BarcodeCapture(settings) + addMode`, or whether composite-code defaults needed re-enabling). Do not list APIs that were already correct or unchanged.
6. If compile errors persist after the changes above, fetch the BarcodeCapture API reference (https://docs.scandit.com/data-capture-sdk/flutter/barcode-capture/api.html) to find the correct API before guessing.
