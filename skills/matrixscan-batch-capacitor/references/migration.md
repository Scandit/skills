# MatrixScan Batch Capacitor Migration Guide

## Migration principles

- **Authority.** When this guide and the API reference disagree, trust the API reference — and a runtime check in the user's project — over this guide. Say which source you followed and why in the summary.
- **Behaviour changes.** Never present a visual or behaviour change (new default, different overlay look, changed feedback, changed scan timing) as a 1:1 rename. List each one in the summary as a judgment call the user must confirm.
- **Compatibility layer.** When the scanning code sits behind a shared scanner library or wrapper that other code calls, keep that library's public API frozen (same types, method names, callbacks) and change only the Scandit calls underneath.
- **Dual-version code.** When code must run on both the old and the target version, branch at run time on a symbol this guide lists as removed in the target version — never on a version string, and never on the presence of the new API. A deprecated symbol that is still present proves nothing about the installed version. Example: `BarcodeBatch.forContext` exists in v7 and is removed in v8, so probing it tells v7 from v8; `DataCaptureContext.forLicenseKey` is deprecated but still present in v8, so probing it cannot.

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

The static factory method was removed in 8.0. Construct the mode directly and register it with the context via `setMode`.

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

## Migrating from a third-party scanner

Replacing `@capacitor-mlkit/barcode-scanning` (or another third-party scanner) is not a version upgrade — read [third-party-migration.md](third-party-migration.md) instead.

---

## After applying changes

1. Run `npm install && npx cap sync` again after any additional package changes triggered by the migration.
2. Build the iOS and Android apps and fix any remaining compile / runtime errors using the API reference (linked in `SKILL.md`).
3. Let the user know they can check the full list of SDK changes in the official migration guides:
   - 6 → 7: https://docs.scandit.com/sdks/capacitor/migrate-6-to-7/
   - 7 → 8: https://docs.scandit.com/sdks/capacitor/migrate-7-to-8/
4. Show the user a summary of only the changes actually made: which files were edited, which classes were renamed, and anything that required a judgment call. Do not list APIs that were already correct or unchanged.
5. If compile errors persist after the changes above, fetch the BarcodeBatch API reference (https://docs.scandit.com/data-capture-sdk/capacitor/barcode-capture/api.html) to find the correct API before guessing.
