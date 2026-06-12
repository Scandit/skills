# MatrixScan Batch (BarcodeBatch) iOS Migration Guide

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

Find the files that use MatrixScan Batch (search for `BarcodeTracking`, `BarcodeBatch`, `BarcodeTrackingSettings`, `BarcodeTrackingBasicOverlay`, `BarcodeTrackingListener`) and apply the relevant changes below directly to those files.

---

## Migration: 6 → 7

The 6→7 step for MatrixScan Batch has three things to handle: the **BarcodeTracking → BarcodeBatch rename** (the headline change), a context-construction update, and a camera setup update. Go through every section below and apply each change that matches the project.

### BarcodeTracking → BarcodeBatch rename

In SDK 7 the entire MatrixScan tracking API was renamed from `BarcodeTracking*` to `BarcodeBatch*`. Rename every occurrence:

| v6 (BarcodeTracking) | v7+ (BarcodeBatch) |
|---|---|
| `BarcodeTracking` | `BarcodeBatch` |
| `BarcodeTrackingSettings` | `BarcodeBatchSettings` |
| `BarcodeTrackingListener` | `BarcodeBatchListener` |
| `BarcodeTrackingSession` | `BarcodeBatchSession` |
| `BarcodeTrackingBasicOverlay` | `BarcodeBatchBasicOverlay` |
| `BarcodeTrackingBasicOverlayDelegate` | `BarcodeBatchBasicOverlayDelegate` |
| `BarcodeTrackingAdvancedOverlay` | `BarcodeBatchAdvancedOverlay` |
| `BarcodeTrackingAdvancedOverlayDelegate` | `BarcodeBatchAdvancedOverlayDelegate` |

The delegate method names follow the rename too:

**Before (v6):**
```swift
func barcodeTracking(_ barcodeTracking: BarcodeTracking,
                     didUpdate session: BarcodeTrackingSession,
                     frameData: FrameData) { }
```

**After (v7+):**
```swift
func barcodeBatch(_ barcodeBatch: BarcodeBatch,
                  didUpdate session: BarcodeBatchSession,
                  frameData: FrameData) { }
```

Apply the same first-label rename to the overlay delegate callbacks: `barcodeTrackingBasicOverlay(_:brushFor:)` → `barcodeBatchBasicOverlay(_:brushFor:)`, `barcodeTrackingBasicOverlay(_:didTap:)` → `barcodeBatchBasicOverlay(_:didTap:)`, and the advanced-overlay callbacks (`viewFor` / `anchorFor` / `offsetFor`) likewise. The overlay convenience initializers also rename their first argument label: `BarcodeTrackingBasicOverlay(barcodeTracking:view:)` → `BarcodeBatchBasicOverlay(barcodeBatch:view:)`.

The import stays `import ScanditBarcodeCapture` — only the symbol names change, not the framework.

When done, verify no `BarcodeTracking`-named identifier remains.

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

Look for an explicit `CameraSettings()` construction, `preferredResolution = .auto` (or `VideoResolution.auto`), or a `camera?.apply(cameraSettings)` whose settings were not obtained from the recommended settings. Replace the block with `BarcodeBatch.recommendedCameraSettings` — the canonical API from v7 onwards. Inform the user that `VideoResolution.auto` will be formally deprecated in v8.

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
camera?.apply(BarcodeBatch.recommendedCameraSettings, completionHandler: nil)
```

If `BarcodeBatch.recommendedCameraSettings` is already in use, skip this section.

### Initializer shape is unchanged

`BarcodeBatch(context:settings:)` is the convenience initializer in v7+ (the renamed equivalent of the v6 `BarcodeTracking(context:settings:)`). Do **not** swap it for a factory like `.forDataCaptureContext(...)` — that is the Android/cross-platform shape, not native Swift.

---

## Migration: 7 → 8

The 7→8 step for native iOS BarcodeBatch has **no breaking API changes**. The factory-method deprecations listed in the official migration guide apply to cross-platform SDKs (React Native, Flutter, Capacitor) — **not to native Swift**, where `BarcodeBatch(context:settings:)` remains the correct API.

### `VideoResolution.auto` deprecated

If the project creates a `CameraSettings` with `VideoResolution.auto`, replace it with the recommended camera settings:

**v7 (deprecated):**
```swift
let cameraSettings = CameraSettings()
cameraSettings.preferredResolution = .auto
camera?.apply(cameraSettings, completionHandler: nil)
```

**v8:**
```swift
camera?.apply(BarcodeBatch.recommendedCameraSettings, completionHandler: nil)
```

If the project already uses `BarcodeBatch.recommendedCameraSettings`, no action is needed.

### No other breaking BarcodeBatch changes

The `BarcodeBatch(context:settings:)` initializer, `BarcodeBatchListener`, `BarcodeBatchSession`, `BarcodeBatchBasicOverlay(barcodeBatch:view:)`, and `BarcodeBatchAdvancedOverlay(barcodeBatch:view:)` are all unchanged in v8 for native iOS.

---

## After applying changes

1. Build the project. Fix any remaining compile errors using the API reference (linked in `SKILL.md`).
2. Let the user know they can check the full list of SDK changes in the official migration guides:
   - 6 → 7: https://docs.scandit.com/sdks/ios/migrate-6-to-7/
   - 7 → 8: https://docs.scandit.com/sdks/ios/migrate-7-to-8/
3. Show the user a summary of only the changes actually made: which files were edited, which types were renamed, and anything that required a judgment call. Do not list APIs that were already correct or unchanged.
4. If compile errors persist after the changes above, fetch the BarcodeBatch API reference (`https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api.html`) to find the correct API before guessing.
