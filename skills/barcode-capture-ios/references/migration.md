# BarcodeCapture iOS Migration Guide

## Migration principles

- **Authority.** When this guide and the API reference disagree, trust the API reference — and a runtime check in the user's project — over this guide. Say which source you followed and why in the summary.
- **Behaviour changes.** Never present a visual or behaviour change (new default, different overlay look, changed feedback, changed scan timing) as a 1:1 rename. List each one in the summary as a judgment call the user must confirm.
- **Compatibility layer.** When the scanning code sits behind a shared scanner library or wrapper that other code calls, keep that library's public API frozen (same types, method names, callbacks) and change only the Scandit calls underneath.
- **Dual-version code.** Code that names a symbol removed in the target version does not compile against it, so this platform cannot probe for it at run time. Select the code path at build time instead — conditional compilation, a build flavor, or a version constant read from the dependency manifest — and never on the presence of the new API. A deprecated symbol that still compiles proves nothing about the installed version.

## Step 1: Detect the installed SDK version

Before making any changes, find out which version of the Scandit SDK the project currently has installed.

Check in this order:

1. **Swift Package Manager** — open `<ProjectRoot>/Package.resolved` (or `<ProjectRoot>/<App>.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved`) and look for the entry with `"identity": "datacapture-spm"`. The `"version"` field is the installed version.
2. **CocoaPods** — open `Podfile.lock` and look for `ScanditBarcodeCapture` or `ScanditCaptureCore`. The version number is on the same line.

Once you know the installed version, determine which migration path applies:

| Installed version | Target version | Action |
|---|---|---|
| 6.x | 7.x | Apply the **6 → 7 migration** below |
| 7.x | 8.x | Apply the **7 → 8 migration** below |
| 6.x | 8.x | Apply **both migrations in order** (6→7 first, then 7→8) |

If you cannot find `Package.resolved` or `Podfile.lock`, ask the user which version they are migrating from.

---

## Step 2: Update the dependency version

Before touching source files, update the SDK version in the dependency manager:

- **SPM**: In Xcode → Package Dependencies, update `datacapture-spm` to the target version.
- **CocoaPods**: Update the version constraint in `Podfile`, then run `pod update`.

Ask the user which dependency manager they use if it's not clear from the project.

---

## Step 3: Apply source code changes

Find the files that use BarcodeCapture (search for `BarcodeCapture`, `BarcodeCaptureSettings`, `BarcodeCaptureOverlay`, `BarcodeCaptureListener`) and apply the relevant changes below directly to those files.

---

## Migration: 6 → 7

The 6→7 step has three things to handle: a context-construction update, a camera setup update, and a scan intention behavioral change. Go through each section below and apply every change that matches the project — do not skip a section just because most of the API is unchanged.

### Context construction — update to the v7+ shared singleton pattern

In v7+ the recommended way to construct the context is `DataCaptureContext.initialize(licenseKey:)` followed by reading `DataCaptureContext.shared`. The bare `DataCaptureContext(licenseKey:)` constructor is deprecated.

**Before (v6 — replace this):**
```swift
let context = DataCaptureContext(licenseKey: "-- KEY --")
```

**After (v7+):**
```swift
DataCaptureContext.initialize(licenseKey: "-- KEY --")
let context = DataCaptureContext.shared
```

If `DataCaptureContext.shared` is already in use, skip this section.

### Camera setup — update to the v7+ recommended pattern

Look for any of these patterns in the project: an explicit `CameraSettings()` construction with no arguments, `preferredResolution = .auto` (or `VideoResolution.auto`), or `camera?.apply(cameraSettings)` where the settings were not obtained from `BarcodeCapture.recommendedCameraSettings`. If found, replace the block — `BarcodeCapture.recommendedCameraSettings` is the canonical API from v7 onwards, and updating during the v6→v7 migration avoids accumulating camera setup tech debt. Inform the user that `VideoResolution.auto` will be formally deprecated in v8.

**Before (v6 pattern — remove this):**
```swift
let cameraSettings = CameraSettings()
cameraSettings.preferredResolution = .auto
let camera = Camera.default
camera?.apply(cameraSettings)
```

**After (v7+ pattern — use this):**
```swift
let camera = Camera.default
camera?.apply(BarcodeCapture.recommendedCameraSettings)
```

If `BarcodeCapture.recommendedCameraSettings` is already in use, skip this section.

### Scan intention default change

The default scan intention is now `SMART` from v7. Most projects need no action.

- If the project already explicitly sets `ScanIntention.manual` or another value on `BarcodeCaptureSettings`, leave it as is.
- If the project uses a single-image frame source, you must set `scanIntention = .manual` — smart is incompatible with single-frame sources.
- If the project did not set the property at all, scanning now uses the smart-scan algorithm by default. This is generally desirable; inform the user but do not change the code.

### Composite codes default change

Default support for Composite Codes was removed when smart scan is enabled. If the project scans composite codes (CC-A, CC-B, CC-C), explicitly enable them. Fetch the [BarcodeCapture API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api.html) for the exact API — do not guess the method name.

If the project does not use composite codes, no action is needed.

---

## Migration: 7 → 8

The 7→8 step for native iOS BarcodeCapture has no breaking API changes. The factory-method deprecations listed in the official migration guide apply to cross-platform SDKs (React Native, Flutter, Capacitor) — **not to native Swift** where `BarcodeCapture(context:settings:)` remains the correct API.

### `VideoResolution.auto` deprecated

If the project creates a `CameraSettings` with `VideoResolution.auto`, replace it with the recommended camera settings:

**v7 (deprecated):**
```swift
let cameraSettings = CameraSettings()
cameraSettings.preferredResolution = .auto
camera?.apply(cameraSettings)
```

**v8:**
```swift
camera?.apply(BarcodeCapture.recommendedCameraSettings)
```

If the project already uses `BarcodeCapture.recommendedCameraSettings`, no action is needed.

### No other breaking BarcodeCapture changes

The `BarcodeCapture(context:settings:)` constructor, `BarcodeCaptureListener`, `BarcodeCaptureSession`, and `BarcodeCaptureOverlay(barcodeCapture:view:)` are all unchanged in v8 for native iOS.

---

## After applying changes

1. Build the project. Fix any remaining compile errors using the API reference (linked in `SKILL.md`).
2. Let the user know they can check the full list of SDK changes in the official migration guides:
   - 6 → 7: https://docs.scandit.com/sdks/ios/migrate-6-to-7/
   - 7 → 8: https://docs.scandit.com/sdks/ios/migrate-7-to-8/
3. Show the user a summary of only the changes actually made: which files were edited, which properties were renamed/removed, and anything that required a judgment call. Do not list APIs that were already correct or unchanged.
4. If compile errors persist after the changes above, fetch the BarcodeCapture API reference (`https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api.html`) to find the correct API before guessing.
