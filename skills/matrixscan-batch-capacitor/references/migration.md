# MatrixScan Batch Capacitor Migration Guide

## Step 1: Detect the installed SDK version

Before making any changes, find out which version of the Scandit Capacitor plugins the project currently has installed.

Check in this order:

1. **`package.json`** — look for `scandit-capacitor-datacapture-core` and/or `scandit-capacitor-datacapture-barcode`. The value next to them is the installed version constraint (e.g. `"^6.28.0"`, `"~7.6.0"`, `"^8.0.0"`).
2. **`package-lock.json`** or **`yarn.lock`** — if `package.json` only has a range, check the lockfile for the exact resolved version.

Once you know the installed version, determine which migration path applies:

| Installed version | Target version | Action |
|---|---|---|
| 6.x | 7.x | Apply the **6 → 7 migration** below |
| 7.x | 8.x | Apply the **7 → 8 migration** below |
| 6.x | 8.x | Apply **both migrations in order** (6→7 first, then 7→8) |

If neither package is in `package.json`, the project is not using MatrixScan Batch on Capacitor yet — fall back to `references/integration.md` instead of migrating.

---

## Step 2: Update the package version

Before touching source files, update the Scandit plugin versions in `package.json`:

```json
{
  "dependencies": {
    "scandit-capacitor-datacapture-core": "^8.0.0",
    "scandit-capacitor-datacapture-barcode": "^8.0.0"
  }
}
```

Then install and sync:

```bash
npm install
npx cap sync
```

`npx cap sync` is **required** after every plugin version change — it propagates the new native artifacts into the iOS and Android projects. Skipping it leaves the native layer on the old version and the app fails at runtime with a version mismatch.

> **Note**: Unlike the Web SDK, the Capacitor package names do **not** change across v6 → v7 → v8 — they stay `scandit-capacitor-datacapture-core` and `scandit-capacitor-datacapture-barcode`. Only the version constraints and the source-code APIs change.

---

## Step 3: Apply source code changes

Find the files that use MatrixScan Batch (search the project for `BarcodeTracking`, `BarcodeBatch`, `BarcodeBatchSettings`, `BarcodeBatchBasicOverlay`, `BarcodeBatchAdvancedOverlay`, `BarcodeBatchListener`) and apply the relevant changes below directly to those files.

---

## Migration: 6 → 7

### `BarcodeTracking` → `BarcodeBatch` rename

v7 renames the MatrixScan Batch API from `BarcodeTracking` to `BarcodeBatch` across all classes and interfaces. This is the **main v6 → v7 change** for MatrixScan Batch. Search for the old names and replace them, updating both the imports and every usage:

| Old (v6) | New (v7+) |
|---|---|
| `BarcodeTracking` | `BarcodeBatch` |
| `BarcodeTrackingSettings` | `BarcodeBatchSettings` |
| `BarcodeTrackingBasicOverlay` | `BarcodeBatchBasicOverlay` |
| `BarcodeTrackingBasicOverlayStyle` | `BarcodeBatchBasicOverlayStyle` |
| `BarcodeTrackingAdvancedOverlay` | `BarcodeBatchAdvancedOverlay` |
| `BarcodeTrackingListener` | `BarcodeBatchListener` / `IBarcodeBatchListener` |
| `BarcodeTrackingSession` | `BarcodeBatchSession` |
| `TrackedBarcode` | `TrackedBarcode` (unchanged) |

The imports come from `scandit-capacitor-datacapture-barcode` in both versions — only the imported identifiers change:

```javascript
// v6
import {
  BarcodeTracking,
  BarcodeTrackingBasicOverlay,
  BarcodeTrackingBasicOverlayStyle,
  BarcodeTrackingSettings,
} from 'scandit-capacitor-datacapture-barcode';

// v7+
import {
  BarcodeBatch,
  BarcodeBatchBasicOverlay,
  BarcodeBatchBasicOverlayStyle,
  BarcodeBatchSettings,
} from 'scandit-capacitor-datacapture-barcode';
```

> **Note**: The underlying API behavior is unchanged — only the class names differ. The listener
> shape (`didUpdateSession`), the session properties (`trackedBarcodes`, `addedTrackedBarcodes`,
> `removedTrackedBarcodes`), and `TrackedBarcode` are all the same after the rename.

---

## Migration: 7 → 8

### `DataCaptureContext.forLicenseKey` → `DataCaptureContext.initialize`

This is the **main breaking change** on Capacitor in v8. The context factory method was renamed.

**v7:**
```javascript
const context = DataCaptureContext.forLicenseKey('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
```

**v8:**
```javascript
const context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
```

Replace every call to `DataCaptureContext.forLicenseKey(...)` with `DataCaptureContext.initialize(...)`, preserving the argument. This call must still happen **after** `await ScanditCaptureCorePlugin.initializePlugins()`.

### Capture mode factory: `BarcodeBatch.forContext` → `new BarcodeBatch`

The static factory method is deprecated in v8. Construct the mode directly and register it with the context via `setMode`.

**v7:**
```javascript
const barcodeBatch = BarcodeBatch.forContext(context, settings);
```

**v8:**
```javascript
const barcodeBatch = new BarcodeBatch(settings);
context.setMode(barcodeBatch);
```

The `new BarcodeBatch(settings)` constructor no longer takes the context — bind the mode by calling `context.setMode(barcodeBatch)` afterwards. (`BarcodeBatch.createRecommendedCameraSettings()` and the `new BarcodeBatchBasicOverlay(mode, style)` / `new BarcodeBatchAdvancedOverlay(mode)` constructors are also available from 7.6+, so projects already on 7.6 may have been using them; no further change is needed for those.)

### Overlay constructors and listeners are unchanged in v8

`BarcodeBatchBasicOverlay`, `BarcodeBatchAdvancedOverlay`, `TrackedBarcodeView`, the basic-overlay listener (`brushForTrackedBarcode`, `didTapTrackedBarcode`), and the advanced-overlay listener (`anchorForTrackedBarcode`, `offsetForTrackedBarcode`, `didTapViewForTrackedBarcode`) are all unchanged in v8.

---

## Migrating from a third-party scanner: `@capacitor-mlkit/barcode-scanning` (ML Kit) → MatrixScan Batch

When a project uses Capawesome's `@capacitor-mlkit/barcode-scanning` plugin for continuous
multi-barcode scanning and wants to move to Scandit MatrixScan Batch, this is a **replacement**, not
a property rename. ML Kit reports raw detections on a stream; BarcodeBatch tracks barcodes across
frames with stable identifiers. The migration removes the ML Kit surface and rebuilds the scanner
with the BarcodeBatch flow from `integration.md`.

### Remove the ML Kit surface

Delete these from the project:

- The `import { BarcodeScanner, BarcodeFormat } from '@capacitor-mlkit/barcode-scanning';` import.
- `BarcodeScanner.addListener('barcodesScanned', ...)` and the handle it returns.
- `BarcodeScanner.startScan(...)` / `BarcodeScanner.stopScan()`.
- Any use of the ML Kit `BarcodeFormat` enum (e.g. `BarcodeFormat.Ean13`).

Uninstall the plugin (`npm uninstall @capacitor-mlkit/barcode-scanning`) once nothing references it.

### Map ML Kit `BarcodeFormat` values to Scandit `Symbology`

Enable the equivalent Scandit symbologies in `BarcodeBatchSettings`. ML Kit's `BarcodeFormat`
members map to `Symbology` as follows:

| ML Kit `BarcodeFormat` | Scandit `Symbology` |
|---|---|
| `BarcodeFormat.Ean13` | `Symbology.EAN13UPCA` |
| `BarcodeFormat.Ean8` | `Symbology.EAN8` |
| `BarcodeFormat.UpcA` | `Symbology.EAN13UPCA` (UPC-A is decoded by the EAN-13/UPC-A symbology) |
| `BarcodeFormat.UpcE` | `Symbology.UPCE` |
| `BarcodeFormat.Code128` | `Symbology.Code128` |
| `BarcodeFormat.Code39` | `Symbology.Code39` |
| `BarcodeFormat.Code93` | `Symbology.Code93` |
| `BarcodeFormat.Codabar` | `Symbology.Codabar` |
| `BarcodeFormat.Itf` | `Symbology.InterleavedTwoOfFive` |
| `BarcodeFormat.QrCode` | `Symbology.QR` |
| `BarcodeFormat.DataMatrix` | `Symbology.DataMatrix` |
| `BarcodeFormat.Pdf417` | `Symbology.PDF417` |
| `BarcodeFormat.Aztec` | `Symbology.Aztec` |

> Enable only the symbologies the app actually used — each extra symbology adds processing cost.

### Preserve dedup and the summary

ML Kit code typically deduplicates on `barcode.rawValue` (a `Set`) and accumulates a list/summary
of unique codes. Keep that behavior. Two options:

- **Direct port**: keep deduping on the barcode data — read `trackedBarcode.barcode.data` in
  `didUpdateSession` and add to the existing `Set` / summary exactly as before.
- **Upgrade (recommended)**: BarcodeBatch already tracks each physical barcode with a stable
  `identifier`, so iterate `session.addedTrackedBarcodes` (new this frame) and dedupe on the tracking
  identifier — this avoids re-emitting the same physical barcode and is more robust than value
  dedupe. Prune your state with `session.removedTrackedBarcodes` when codes leave the frame.

Field mapping for the data your old code read off each ML Kit `Barcode`:

| ML Kit `Barcode` field | BarcodeBatch equivalent |
|---|---|
| `barcode.rawValue` | `trackedBarcode.barcode.data` |
| `barcode.format` | `trackedBarcode.barcode.symbology` |
| (none — no tracking) | `trackedBarcode.identifier` (stable per physical barcode) |

### Rebuild with the BarcodeBatch flow

Follow `integration.md`: `ScanditCaptureCorePlugin.initializePlugins()` first, then
`DataCaptureContext.initialize`, camera via `BarcodeBatch.createRecommendedCameraSettings()` +
`Camera.withSettings` + `context.setFrameSource`, `BarcodeBatchSettings` with the mapped
symbologies, `new BarcodeBatch(settings)` + `context.setMode`, a `didUpdateSession` listener that
runs your (preserved) dedup/summary logic, `DataCaptureView.forContext` + `connectToElement`, then
camera on and `barcodeBatch.isEnabled = true`. Show the setup checklist (install the two
`scandit-capacitor-datacapture-*` packages, `npx cap sync`, iOS `NSCameraUsageDescription`).

---

## After applying changes

1. Run `npm install && npx cap sync` again after any additional package changes triggered by the migration.
2. Build the iOS and Android apps and fix any remaining compile / runtime errors using the API reference (linked in `SKILL.md`).
3. Let the user know they can check the full list of SDK changes in the official migration guides:
   - 6 → 7: https://docs.scandit.com/sdks/capacitor/migrate-6-to-7/
   - 7 → 8: https://docs.scandit.com/sdks/capacitor/migrate-7-to-8/
4. Show the user a summary of only the changes actually made: which files were edited, which classes were renamed, and anything that required a judgment call. Do not list APIs that were already correct or unchanged.
5. If compile errors persist after the changes above, fetch the BarcodeBatch API reference (https://docs.scandit.com/data-capture-sdk/capacitor/barcode-capture/api.html) to find the correct API before guessing.
