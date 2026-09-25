# BarcodeCapture Cordova Migration Guide

## Step 1: Detect the installed SDK version

Before making any changes, find out which version of the Scandit Cordova plugins the project currently has installed.

Check in this order:

1. **`config.xml`** — look for `<plugin name="scandit-cordova-datacapture-core" spec="..."/>` and `<plugin name="scandit-cordova-datacapture-barcode" spec="..."/>`. The `spec` value is the installed version (e.g. `6.28.1`, `7.6.0`, `^8.0.0`).
2. **`plugins/fetch.json`** — Cordova records the resolved version of each installed plugin here after `cordova plugin add`. Look up the Scandit plugin entries for their exact resolved versions.
3. **`package.json`** — if the project declares the plugins under `cordova.plugins`, the version constraint is there too.

Once you know the installed version, determine which migration path applies:

| Installed version | Target version | Action |
|---|---|---|
| 6.x | 7.x | Apply the **6 → 7 migration** below |
| 7.x | 8.x | Apply the **7 → 8 migration** below |
| 6.x | 8.x | Apply **both migrations in order** (6→7 first, then 7→8) |

If neither plugin is declared anywhere, the project is not using BarcodeCapture on Cordova yet — fall back to `references/integration.md` instead of migrating.

---

## Step 2: Update the plugin version

Cordova plugins are installed by `cordova plugin add` with a version spec. Update the spec in `config.xml` and reinstall:

```bash
cordova plugin remove scandit-cordova-datacapture-barcode
cordova plugin remove scandit-cordova-datacapture-core
cordova plugin add scandit-cordova-datacapture-core@^8.0.0
cordova plugin add scandit-cordova-datacapture-barcode@^8.0.0
cordova prepare
```

`cordova prepare` **is required** after every plugin version change — it propagates the new native artifacts into the iOS and Android platform projects. Skipping it leaves the native layer on the old version and the app will fail at runtime with a version mismatch.

If the project uses `package.json` and `cordova.plugins` to declare plugins (Cordova 9+ behavior), update the version in `package.json` as well so `cordova prepare` pins the same spec next time.

---

## Step 3: Apply source code changes

Find the files that use BarcodeCapture (search the project for `BarcodeCapture`, `BarcodeCaptureSettings`, `BarcodeCaptureOverlay`, `DataCaptureView`, `Scandit.`) and apply the relevant changes below directly to those files.

---

## Migration: 6 → 7

### `BarcodeTracking` → `BarcodeBatch` rename

If the project uses `BarcodeTracking` (MatrixScan) alongside BarcodeCapture, rename all occurrences to `BarcodeBatch` (including `Scandit.BarcodeTracking` → `Scandit.BarcodeBatch`). The API is otherwise unchanged. BarcodeCapture itself is **not** renamed — only BarcodeTracking is.

### Scan intention default change

The default scan intention is now `Scandit.ScanIntention.Smart`. If the project explicitly set `ScanIntention.Manual` on `BarcodeCaptureSettings`, leave it as is. If the project relied on the old default, the code still works — but the active behavior changes from `Manual` to `Smart`. Tell the user about the new default and let them choose to pin `Manual` explicitly.

### `newlyRecognizedBarcodes` → `newlyRecognizedBarcode`

In v6, `BarcodeCaptureSession` exposed `newlyRecognizedBarcodes` (an array). From v6.26 onward — and for all of v7 — there is a single property `newlyRecognizedBarcode` (a single `Barcode | null`). Replace any code that read `session.newlyRecognizedBarcodes[0]` with:

```javascript
const barcode = session.newlyRecognizedBarcode;
if (!barcode) return;
```

### `recommendedCameraSettings` is now a static accessor

If the project does not yet use `Scandit.BarcodeCapture.recommendedCameraSettings` to configure the camera, no action is needed. If it does, the property is unchanged in v7 — keep using it.

### New v7 APIs (optional, no action required unless the user wants them)

Mention only if the user asks:
- Direct `BarcodeCaptureOverlay` constructor: `new Scandit.BarcodeCaptureOverlay(barcodeCapture)` (v7.6+). The static factory `BarcodeCaptureOverlay.withBarcodeCaptureForView(...)` continues to work.
- `BarcodeCapture` constructor: `new Scandit.BarcodeCapture(settings)` (v7.6+) — the canonical pattern in v8 (see below).

---

## Migration: 7 → 8

### `DataCaptureContext.forLicenseKey` → `DataCaptureContext.initialize`

This is the **main breaking change** on Cordova in v8. The context factory method was renamed.

**v7:**
```javascript
const context = Scandit.DataCaptureContext.forLicenseKey('YOUR_LICENSE_KEY');
```

**v8:**
```javascript
const context = Scandit.DataCaptureContext.initialize('YOUR_LICENSE_KEY');
```

Replace every call to `Scandit.DataCaptureContext.forLicenseKey(...)` with `Scandit.DataCaptureContext.initialize(...)`, preserving the argument. Still call it inside the `deviceready` handler.

### Capture mode factory deprecation: `BarcodeCapture.forContext` → `new BarcodeCapture` + `context.setMode`

The static factory method is deprecated in v8. Construct the mode directly and add it to the context explicitly.

**v7:**
```javascript
const barcodeCapture = Scandit.BarcodeCapture.forContext(context, settings);
```

**v8:**
```javascript
const barcodeCapture = new Scandit.BarcodeCapture(settings);
context.setMode(barcodeCapture);
```

`forContext` automatically attached the mode to the context; the new constructor does not. You must call `context.setMode(barcodeCapture)` (or `context.addMode(barcodeCapture)`) yourself.

The same pattern applies to other capture modes the project may use alongside BarcodeCapture:
- `BarcodeBatch.forContext(context, settings)` → `new Scandit.BarcodeBatch(settings)` + `context.addMode(...)` / `context.setMode(...)`
- `BarcodeSelection.forContext(context, settings)` → `new Scandit.BarcodeSelection(settings)` + `context.addMode(...)` / `context.setMode(...)`

### `BarcodeCaptureOverlay.withBarcodeCaptureForView` → `new BarcodeCaptureOverlay` + `view.addOverlay`

The factory still works, but the canonical v8 pattern is the direct constructor plus an explicit `view.addOverlay` call.

**v7:**
```javascript
const overlay = Scandit.BarcodeCaptureOverlay.withBarcodeCaptureForView(barcodeCapture, view);
```

**v8:**
```javascript
const overlay = new Scandit.BarcodeCaptureOverlay(barcodeCapture);
view.addOverlay(overlay);
```

If the project already uses `withBarcodeCaptureForView`, leaving it as is will still compile and run — but new code should use the constructor form for symmetry with the other capture modes.

### New v8 APIs (optional, no action required unless the user wants them)

Mention only if the user asks:
- `BarcodeCaptureSettings.selectionMode` — confirm-on-tap scanning (`On`, `Off`, `Auto`).
- `BarcodeCaptureSettings.batterySaving` — `Auto` (default), `On`, `Off`.

---

## After applying changes

1. Run `cordova prepare` after any additional plugin changes (e.g. if you re-added a platform during migration).
2. Build the iOS and Android apps and fix any remaining runtime errors using the API reference (linked in `SKILL.md`).
3. Let the user know they can check the full list of SDK changes in the official migration guides:
   - 6 → 7: https://docs.scandit.com/sdks/cordova/migrate-6-to-7/
   - 7 → 8: https://docs.scandit.com/sdks/cordova/migrate-7-to-8/
4. Show the user a summary of only the changes actually made: which files were edited, which calls were replaced (`forLicenseKey` → `initialize`, `BarcodeCapture.forContext` → `new BarcodeCapture` + `setMode`, `withBarcodeCaptureForView` → `new BarcodeCaptureOverlay` + `addOverlay`), which session properties were updated (`newlyRecognizedBarcodes` → `newlyRecognizedBarcode`), and anything that required a judgment call. Do not list APIs that were already correct or unchanged.
5. If runtime errors persist, fetch the BarcodeCapture API reference (https://docs.scandit.com/data-capture-sdk/cordova/barcode-capture/api.html) to find the correct API before guessing.
