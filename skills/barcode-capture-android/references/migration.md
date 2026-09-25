# BarcodeCapture Android Migration Guide

## Migration principles

- **Authority.** When this guide and the API reference disagree, trust the API reference — and a runtime check in the user's project — over this guide. Say which source you followed and why in the summary.
- **Behaviour changes.** Never present a visual or behaviour change (new default, different overlay look, changed feedback, changed scan timing) as a 1:1 rename. List each one in the summary as a judgment call the user must confirm.
- **Compatibility layer.** When the scanning code sits behind a shared scanner library or wrapper that other code calls, keep that library's public API frozen (same types, method names, callbacks) and change only the Scandit calls underneath.
- **Dual-version code.** When code must run on both the old and the target version, branch on a symbol this guide lists as removed in the target version — never on a version string, and never on the presence of the new API. A deprecated symbol that is still present proves nothing about the installed version. Example: `BarcodeCapture.forContext` is removed on Flutter and React Native 7→8, but still exists on Web and deprecated-but-present on Capacitor and Cordova.

## Step 1: Detect the installed SDK version

Before making any changes, find out which version of the Scandit SDK the project currently has installed.

Check in this order:

1. **Version catalog** — open `gradle/libs.versions.toml` and look for a `scandit` version entry (e.g. `scandit = "7.x.y"`).
2. **build.gradle / build.gradle.kts** — search for `com.scandit.datacapture:barcode` and read the version on the same line.

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

## Step 3: Apply source code changes

Search for files that use BarcodeCapture (search for `BarcodeCapture`, `BarcodeCaptureSettings`, `BarcodeCaptureOverlay`, `BarcodeCaptureListener`) and apply the relevant changes below directly to those files.

---

## Migration: 6 → 7

The 6→7 step has three things to handle: a camera setup update, a scan intention behavioral change, and a class rename. Go through each section below and apply every change that matches the project — do not skip a section just because most of the API is unchanged.

### Camera setup — update to the v7+ recommended pattern

Look for any of these patterns in the project: `CameraSettings()`, `VideoResolution.AUTO`, `camera?.applySettings(...)`. If found, replace the block — `createRecommendedCameraSettings()` is the canonical API from v7 onwards, and updating during the v6→v7 migration avoids accumulating camera setup tech debt. Inform the user that `VideoResolution.AUTO` will be formally deprecated in v8.

**Before (v6 pattern — remove this):**
```kotlin
val cameraSettings = CameraSettings()
cameraSettings.preferredResolution = VideoResolution.AUTO
camera = Camera.getDefaultCamera()
camera?.applySettings(cameraSettings)
```

**After (v7+ pattern — use this):**
```kotlin
val camera = Camera.getDefaultCamera(BarcodeCapture.createRecommendedCameraSettings())
```

Remove the `CameraSettings` and `VideoResolution` imports after making the change. If `createRecommendedCameraSettings()` is already in use, skip this section.

### Scan intention default change

The default scan intention is now `SMART` from v7. Most projects need no action.

- If the project already explicitly sets `ScanIntention.MANUAL` or another value on `BarcodeCaptureSettings`, leave it as is.
- If the project uses a single-image frame source, you must set `scanIntention = ScanIntention.MANUAL` — Smart is incompatible with single-frame sources.
- If the project did not set the property at all, scanning now uses the Smart Scan algorithm by default. This is generally desirable; inform the user but do not change the code.

### Composite codes default change

Default support for Composite Codes was removed when Smart Scan is enabled. If the project scans composite codes (CC-A, CC-B, CC-C), explicitly enable them. Fetch the [Advanced Configurations](https://docs.scandit.com/sdks/android/barcode-capture/advanced/) page for the exact API — do not guess the method name.

If the project does not use composite codes, no action is needed.

### `BarcodeTracking` → `BarcodeBatch` rename

If the project uses `BarcodeTracking` (MatrixScan) alongside BarcodeCapture, rename all occurrences to `BarcodeBatch`. The API is otherwise unchanged.

### New v7 APIs (optional, no action required unless the user wants them)

- `SparkScanViewState` — tracks the current UI state of the SparkScan view.

---

## Migration: 7 → 8

The 7→8 step for native Android BarcodeCapture has no breaking API changes. The factory-method deprecations listed in the official migration guide apply to cross-platform SDKs (React Native, Flutter, Capacitor) — **not to native Kotlin/Java** where `BarcodeCapture.forDataCaptureContext(context, settings)` remains the correct API.

### `VideoResolution.AUTO` deprecated

If the project creates a `CameraSettings` with `VideoResolution.AUTO`, replace it with the recommended camera settings:

**v7 (deprecated):**
```kotlin
val cameraSettings = CameraSettings()
cameraSettings.preferredResolution = VideoResolution.AUTO
camera?.applySettings(cameraSettings)
```

**v8:**
```kotlin
val camera = Camera.getDefaultCamera(BarcodeCapture.createRecommendedCameraSettings())
```

Or if the camera was already obtained:
```kotlin
camera?.applySettings(BarcodeCapture.createRecommendedCameraSettings())
```

If the project already uses `BarcodeCapture.createRecommendedCameraSettings()`, no action is needed.

### No other breaking BarcodeCapture changes

The `forDataCaptureContext` factory, `BarcodeCaptureListener`, `BarcodeCaptureSession`, and `BarcodeCaptureOverlay.newInstance` are all unchanged in v8 for native Android.

---

## After applying changes

1. Sync and build the project. Fix any remaining compile errors using the API reference (linked in `SKILL.md`).
2. Let the user know they can check the full list of SDK changes in the official migration guides:
   - 6 → 7: https://docs.scandit.com/sdks/android/migrate-6-to-7/
   - 7 → 8: https://docs.scandit.com/sdks/android/migrate-7-to-8/
3. Show the user a summary of only the changes actually made: which files were edited, which properties were renamed/removed, and anything that required a judgment call. Do not list APIs that were already correct or unchanged.
4. If compile errors persist after the changes above, fetch the BarcodeCapture API reference (`https://docs.scandit.com/data-capture-sdk/android/barcode-capture/api.html`) to find the correct API before guessing.
