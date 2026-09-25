# BarcodeCapture Capacitor Migration Guide

## Step 1: Detect the installed SDK version

Before making any changes, find out which version of the Scandit Capacitor plugins the project currently has installed.

Check in this order:

1. **`package.json`** — look for the entries `scandit-capacitor-datacapture-core` and/or `scandit-capacitor-datacapture-barcode`. The value next to them is the installed version constraint (e.g. `"^6.28.0"`, `"~7.6.0"`, `"^8.0.0"`).
2. **`package-lock.json`** or **`yarn.lock`** — if `package.json` only has a range, check the lockfile for the exact resolved version.

Once you know the installed version, determine which migration path applies:

| Installed version | Target version | Action |
|---|---|---|
| 6.x | 7.x | Apply the **6 → 7 migration** below |
| 7.x | 8.x | Apply the **7 → 8 migration** below |
| 6.x | 8.x | Apply **both migrations in order** (6→7 first, then 7→8) |

If neither package is in `package.json`, the project is not using BarcodeCapture on Capacitor yet — fall back to `references/integration.md` instead of migrating.

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

`npx cap sync` is **required** after every plugin version change — it propagates the new native artifacts into the iOS (`ios/App/Podfile.lock`) and Android (`android/app/build.gradle`, Gradle caches) projects. Skipping it will leave the native layer on the old version and the app will fail at runtime with a version mismatch.

---

## Step 3: Apply source code changes

Find the files that use BarcodeCapture (search the project for `BarcodeCapture`, `BarcodeCaptureSettings`, `BarcodeCaptureOverlay`, `BarcodeCaptureListener`) and apply the relevant changes below directly to those files.

---

## Migration: 6 → 7

### Scan intention default change

The default `ScanIntention` is now `Smart` (from 7.0). If the project explicitly set `ScanIntention.Manual` or another value on `BarcodeCaptureSettings`, leave it as is. If the project relied on an explicit `Smart` setting that is now the default, the code still works — no change needed.

### `codeDuplicateFilter` default sentinel value

From SDK 7.1.0 the special value `-2` is the new default for `codeDuplicateFilter`. Its meaning depends on `scanIntention`:
- With `ScanIntention.Smart` (the new default): enables the Smart Duplicate Filter.
- With `ScanIntention.Manual`: behaves like a 1.5 s duplicate filter.

If the project does not set `codeDuplicateFilter` explicitly, do not add it — the new default applies. If it was set explicitly, leave the value untouched.

### BarcodeTracking → BarcodeBatch rename

If the project uses `BarcodeTracking` (MatrixScan) alongside BarcodeCapture, rename all occurrences to `BarcodeBatch`. Imports from `scandit-capacitor-datacapture-barcode` need updating. The API is otherwise unchanged.

### New v7 constructors and recommended camera settings (optional, no action required unless the user wants them)

These are available in v7 — mention them only if the user asks or if they request a migration to the modern style:

- `new BarcodeCapture(settings)` — direct constructor that does not bind the mode to a context. Add the mode with `context.setMode(barcodeCapture)`. Available from capacitor=7.6.
- `new BarcodeCaptureOverlay(mode)` — direct constructor for the overlay. Add it with `view.addOverlay(overlay)`. Available from capacitor=7.6.
- `BarcodeCapture.createRecommendedCameraSettings()` — replaces the legacy `BarcodeCapture.recommendedCameraSettings` getter pattern. Available from capacitor=7.6.

The legacy `BarcodeCapture.forContext(context, settings)` and `BarcodeCaptureOverlay.withBarcodeCaptureForView(mode, view)` factories still work in v7 — there is no breaking change. Keep them as-is unless the user explicitly wants the modern style.

---

## Migration: 7 → 8

### `DataCaptureContext.forLicenseKey` → `DataCaptureContext.initialize`

This is the **main breaking change** on Capacitor in v8. The context factory method was renamed and its semantics tightened.

**v7:**
```javascript
const context = DataCaptureContext.forLicenseKey('YOUR_LICENSE_KEY');
```

**v8:**
```javascript
const context = DataCaptureContext.initialize('YOUR_LICENSE_KEY');
```

Replace every call to `DataCaptureContext.forLicenseKey(...)` with `DataCaptureContext.initialize(...)`, preserving the argument. This call must still happen **after** `await ScanditCaptureCorePlugin.initializePlugins()`.

### Capture mode factory deprecation: `BarcodeCapture.forContext` → `new BarcodeCapture`

The static factory method is deprecated in v8. Construct the mode directly and add it to the context with `setMode`.

**v7:**
```javascript
const barcodeCapture = BarcodeCapture.forContext(context, settings);
```

**v8:**
```javascript
const barcodeCapture = new BarcodeCapture(settings);
context.setMode(barcodeCapture);
```

The same pattern applies to other capture modes the project may use alongside BarcodeCapture:
- `BarcodeBatch.forContext(context, settings)` → `new BarcodeBatch(settings)` + `context.setMode(barcodeBatch)`
- `BarcodeSelection.forContext(context, settings)` → `new BarcodeSelection(settings)` + `context.setMode(...)`

### Overlay factory deprecation: `BarcodeCaptureOverlay.withBarcodeCaptureForView` → `new BarcodeCaptureOverlay`

The static factory is deprecated in v8. Construct the overlay directly and add it to the view with `view.addOverlay`.

**v7:**
```javascript
const overlay = BarcodeCaptureOverlay.withBarcodeCaptureForView(barcodeCapture, view);
```

**v8:**
```javascript
const overlay = new BarcodeCaptureOverlay(barcodeCapture);
view.addOverlay(overlay);
```

### New v8 APIs (optional, no action required unless the user wants them)

Available in v8 on `BarcodeCaptureSettings` — mention only if the user asks:
- `selectionMode` — `SelectionMode.Off | .On | .Auto`. Controls whether barcodes are scanned automatically (`Off`, default), require an explicit tap (`On`), or are decided dynamically by the SDK (`Auto`). Available from 8.5.

---

## After applying changes

1. Run `npm install && npx cap sync` again after any additional package changes triggered by the migration (e.g. if TypeScript type errors surface additional version mismatches).
2. Build the iOS and Android apps and fix any remaining compile / runtime errors using the API reference (linked in `SKILL.md`).
3. Let the user know they can check the full list of SDK changes in the official migration guides:
   - 6 → 7: https://docs.scandit.com/sdks/capacitor/migrate-6-to-7/
   - 7 → 8: https://docs.scandit.com/sdks/capacitor/migrate-7-to-8/
4. Show the user a summary of only the changes actually made: which files were edited, which factories were replaced, and anything that required a judgment call. Do not list APIs that were already correct or unchanged.
5. If compile errors persist after the changes above, fetch the BarcodeCapture API reference (https://docs.scandit.com/data-capture-sdk/capacitor/barcode-capture/api.html) to find the correct API before guessing.
