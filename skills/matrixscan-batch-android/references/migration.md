# MatrixScan Batch (BarcodeBatch) Android Migration Guide

## Migration principles

- **Authority.** When this guide and the API reference disagree, trust the API reference — and a runtime check in the user's project — over this guide. Say which source you followed and why in the summary.
- **Behaviour changes.** Never present a visual or behaviour change (new default, different overlay look, changed feedback, changed scan timing) as a 1:1 rename. List each one in the summary as a judgment call the user must confirm.
- **Compatibility layer.** When the scanning code sits behind a shared scanner library or wrapper that other code calls, keep that library's public API frozen (same types, method names, callbacks) and change only the Scandit calls underneath.
- **Dual-version code.** Code that names a symbol removed in the target version does not compile against it, so this platform cannot probe for it at run time. Select the code path at build time instead — conditional compilation, a build flavor, or a version constant read from the dependency manifest — and never on the presence of the new API. A deprecated symbol that still compiles proves nothing about the installed version.

## Step 1: Detect the installed SDK version

Before making any changes, find out which version of the Scandit SDK the project currently has installed.

Check in this order:

1. **Version catalog** — open `gradle/libs.versions.toml` and look for a `scandit` version entry (e.g. `scandit = "7.x.y"`).
2. **build.gradle / build.gradle.kts** — search for `com.scandit.datacapture:barcode` and read the version on the same line.

A reliable signal for v6: the code uses `BarcodeTracking*` classes and the `com.scandit.datacapture.barcode.tracking.*` package. From v7 onward the mode is `BarcodeBatch*` in `com.scandit.datacapture.barcode.batch.*`.

Once you know the installed version, determine which migration path applies:

| Installed version | Target version | Action |
|---|---|---|
| 6.x | 7.x | Apply the **6 → 7 migration** below |
| 7.x | 8.x | Apply the **7 → 8 migration** below |
| 6.x | 8.x | Apply **both migrations in order** (6→7 first, then 7→8) |

If you cannot find the version, ask the user which version they are migrating from.

---

## Step 2: Update the dependency version

Before touching source files, update the SDK version in the Gradle dependency:

- In `build.gradle` / `build.gradle.kts`: update the version string in the `com.scandit.datacapture:barcode` and `com.scandit.datacapture:core` dependency lines.
- In `libs.versions.toml`: update the `scandit` version entry, then sync the project.

After updating, sync the project (Android Studio → "Sync Project with Gradle Files").

---

## Migration: 6 → 7

The headline change for MatrixScan is the **`BarcodeTracking` → `BarcodeBatch` rename**. This is a pure rename — the factory pattern, listener callbacks, session shape, and overlays are otherwise identical.

### Class rename

Rename every `BarcodeTracking*` type to its `BarcodeBatch*` equivalent:

| v6 (BarcodeTracking) | v7+ (BarcodeBatch) |
|---|---|
| `BarcodeTracking` | `BarcodeBatch` |
| `BarcodeTrackingSettings` | `BarcodeBatchSettings` |
| `BarcodeTrackingListener` | `BarcodeBatchListener` |
| `BarcodeTrackingSession` | `BarcodeBatchSession` |
| `BarcodeTrackingBasicOverlay` | `BarcodeBatchBasicOverlay` |
| `BarcodeTrackingBasicOverlayListener` | `BarcodeBatchBasicOverlayListener` |
| `BarcodeTrackingBasicOverlayStyle` | `BarcodeBatchBasicOverlayStyle` |
| `BarcodeTrackingAdvancedOverlay` | `BarcodeBatchAdvancedOverlay` |
| `BarcodeTrackingAdvancedOverlayListener` | `BarcodeBatchAdvancedOverlayListener` |

### Package path rename

The package segment `tracking` becomes `batch`:

| v6 package | v7+ package |
|---|---|
| `com.scandit.datacapture.barcode.tracking.capture` | `com.scandit.datacapture.barcode.batch.capture` |
| `com.scandit.datacapture.barcode.tracking.data` | `com.scandit.datacapture.barcode.batch.data` |
| `com.scandit.datacapture.barcode.tracking.ui.overlay` | `com.scandit.datacapture.barcode.batch.ui.overlay` |

`TrackedBarcode` keeps its name (only its package moves to `...barcode.batch.data`).

### Unchanged

- The factory `BarcodeBatch.forDataCaptureContext(dataCaptureContext, settings)` keeps the same shape (only the class name changed).
- `BarcodeBatch.createRecommendedCameraSettings()` is unchanged.
- The `onSessionUpdated(mode, session, data)` callback signature is unchanged.
- `BarcodeBatchBasicOverlay.newInstance(mode, view)` / the style overload are unchanged.

After the rename, no `BarcodeTracking`-prefixed identifier and no `com.scandit.datacapture.barcode.tracking.` import should remain in the migrated code.

---

## Migration: 7 → 8

For native Android **BarcodeBatch there are no breaking API changes** from v7 to v8. The mode factory `BarcodeBatch.forDataCaptureContext(context, settings)`, the `BarcodeBatchListener` / `onSessionUpdated` callback, `BarcodeBatchSession`, the basic and advanced overlays, and the manual camera/lifecycle pattern are all unchanged.

The factory-method deprecations listed in the official migration guide apply to cross-platform SDKs (React Native, Flutter, Capacitor) — **not to native Kotlin/Java**, where `forDataCaptureContext` remains the correct factory. Do **not** rename `BarcodeBatch` back to `BarcodeTracking`; that rename already happened in v6→v7.

If the project still creates a hand-rolled `CameraSettings` with `VideoResolution.AUTO`, replace it with `Camera.getDefaultCamera(BarcodeBatch.createRecommendedCameraSettings())` (the same advice as BarcodeCapture). Otherwise no action is needed.

---

## After applying changes

1. Sync and build the project. Fix any remaining compile errors using the API reference (linked in `SKILL.md`).
2. Let the user know they can check the full list of SDK changes in the official migration guides:
   - 6 → 7: https://docs.scandit.com/sdks/android/migrate-6-to-7/
   - 7 → 8: https://docs.scandit.com/sdks/android/migrate-7-to-8/
3. Show the user a summary of only the changes actually made: which files were edited, which classes/packages were renamed. Do not list APIs that were already correct or unchanged.
