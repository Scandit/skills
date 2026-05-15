# MatrixScan Batch Web Migration Guide

## Step 1: Detect the installed SDK version

Before making any changes, find out which version of the Scandit SDK the project currently has installed.

Check in this order:

1. **package.json** — look for `@scandit/web-datacapture-core` or `@scandit/web-datacapture-barcode` (v7+), or `scandit-web-datacapture-core` / `scandit-web-datacapture-barcode` (v6).
2. **Lock files** — if package.json uses a version range, check the exact installed version in `package-lock.json`, `yarn.lock`, or `pnpm-lock.yaml`.

Once you know the installed version, determine which migration path applies:

| Installed version | Target version | Action |
|---|---|---|
| 6.x | 7.x | Apply the **6 → 7 migration** below |
| 7.x | 8.x | Apply the **7 → 8 migration** below |
| 6.x | 8.x | Apply **both migrations in order** (6→7 first, then 7→8) |

If you cannot find the version in package.json or lock files, ask the user which version they are migrating from.

---

## Step 2: Update the package version

Before touching source files, update the SDK version in the package manager:

- **npm**: `npm install @scandit/web-datacapture-core@latest @scandit/web-datacapture-barcode@latest`
- **yarn**: `yarn add @scandit/web-datacapture-core@latest @scandit/web-datacapture-barcode@latest`
- **pnpm**: `pnpm add @scandit/web-datacapture-core@latest @scandit/web-datacapture-barcode@latest`

> **Note:** v6 used unscoped package names (`scandit-web-datacapture-core`, `scandit-web-datacapture-barcode`). When migrating from v6, remove the old unscoped packages and install the new scoped ones (`@scandit/web-datacapture-core`, `@scandit/web-datacapture-barcode`). Update all import statements accordingly.

Ask the user which package manager they use if it's not clear from the project.

---

## Step 3: Apply source code changes

Find the files that use MatrixScan Batch (search for `BarcodeTracking`, `BarcodeBatch`, `BarcodeBatchSettings`, `BarcodeBatchBasicOverlay`, `BarcodeBatchListener`) and apply the relevant changes below directly to those files.

---

## Migration: 6 → 7

### Package and hosting changes

v7 introduces critical changes to how the Web SDK is installed and hosted:

| Change | Old (v6) | New (v7+) |
|---|---|---|
| NPM scope | `scandit-web-datacapture-core`, `scandit-web-datacapture-barcode` | `@scandit/web-datacapture-core`, `@scandit/web-datacapture-barcode` |
| Engine directory | `build/engine` | `sdc-lib` (v7) / `library/engine` (samples convention) |

Apply these changes:
1. Update all import statements to use the new scoped package names.
2. Update `libraryLocation` paths from `build/engine` to match your self-hosting path (e.g. `sdc-lib` or `library/engine/`).

### `BarcodeTracking` → `BarcodeBatch` rename

v7 renames the MatrixScan Batch API from `BarcodeTracking` to `BarcodeBatch` across all classes and interfaces.

Search for these old names and replace them:

| Old (v6) | New (v7+) |
|---|---|
| `BarcodeTracking` | `BarcodeBatch` |
| `BarcodeTrackingSettings` | `BarcodeBatchSettings` |
| `BarcodeTrackingBasicOverlay` | `BarcodeBatchBasicOverlay` |
| `BarcodeTrackingAdvancedOverlay` | `BarcodeBatchAdvancedOverlay` |
| `BarcodeTrackingListener` | `BarcodeBatchListener` / `IBarcodeBatchListener` |
| `BarcodeTrackingSession` | `BarcodeBatchSession` |
| `TrackedBarcode` | `TrackedBarcode` (unchanged) |
| `barcodeTrackingLoader` | `barcodeCaptureLoader` |

> **Note:** The underlying API behavior is unchanged — only the class names differ.

---

## Migration: 7 → 8

### DataCaptureContext initialization change

v8 replaces the two-step `configure()` + `DataCaptureContext.create()` pattern with a single `DataCaptureContext.forLicenseKey()` call.

**Old (v7):**
```typescript
import { configure, DataCaptureContext } from "@scandit/web-datacapture-core";
import { barcodeCaptureLoader } from "@scandit/web-datacapture-barcode";

await configure({
    libraryLocation: new URL("sdc-lib", document.baseURI).toString(),
    licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
    moduleLoaders: [barcodeCaptureLoader()],
});
const context = await DataCaptureContext.create();
```

**New (v8):**
```typescript
import { DataCaptureContext } from "@scandit/web-datacapture-core";
import { barcodeCaptureLoader } from "@scandit/web-datacapture-barcode";

const context = await DataCaptureContext.forLicenseKey(
  "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
  {
    libraryLocation: new URL("sdc-lib", document.baseURI).toString(),
    moduleLoaders: [barcodeCaptureLoader()],
  }
);
```

Apply this change:
1. Remove the `configure` import from `@scandit/web-datacapture-core`.
2. Replace the `configure({ ... })` call and `DataCaptureContext.create()` with `DataCaptureContext.forLicenseKey(licenseKey, { libraryLocation, moduleLoaders })`.
3. Replace any captured `context` variable references as needed — `forLicenseKey` returns the context and also sets `DataCaptureContext.sharedInstance`.

### No other breaking BarcodeBatch-specific changes in v8

`BarcodeBatch.forContext`, `BarcodeBatchSettings`, `BarcodeBatchBasicOverlay`, `BarcodeBatchAdvancedOverlay`, `TrackedBarcodeView`, and listener shapes are all unchanged in v8 for the native Web SDK.

---

## After applying changes

1. Build the project and fix any remaining type or build errors using the API reference (linked in `SKILL.md`).
2. Let the user know they can check the full list of SDK changes in the official migration guides:
   - 6 → 7: <https://docs.scandit.com/sdks/web/migrate-6-to-7/>
   - 7 → 8: <https://docs.scandit.com/sdks/web/migrate-7-to-8/>
3. Show the user a summary of only the changes actually made: which files were edited, which classes were renamed, and anything that required a judgment call. Do not list APIs that were already correct or unchanged.
4. If type or build errors persist after the changes above, fetch the [BarcodeBatch API reference](https://docs.scandit.com/data-capture-sdk/web/barcode-capture/api.html) to find the correct API before guessing.
