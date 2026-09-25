# SparkScan Cordova Migration Guide

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

If neither plugin is declared anywhere, the project is not using SparkScan on Cordova yet — fall back to `references/integration.md` instead of migrating.

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

Find the files that use SparkScan (search the project for `SparkScan`, `SparkScanView`, `SparkScanSettings`, `SparkScanViewSettings`, `Scandit.`) and apply the relevant changes below directly to those files.

---

## Migration: 6 → 7

### Where these properties live in v6

**On `SparkScanView`** (set on the view instance after `Scandit.SparkScanView.forContext(...)`):
- All button visibility, color, and text properties listed below

**On `SparkScanViewSettings`** (passed to the view / configured before creating the view):
- `defaultHandMode` only

When searching the project for these properties, look for usages on both the view instance and the settings object.

### SparkScanView property renames

Apply these renames everywhere they appear. These are renames — always replace the old name with the new one, preserving the existing value:

| Old (v6, on `SparkScanView`) | New (v7) |
|---|---|
| `torchButtonVisible` | `torchControlVisible` |
| `captureButtonBackgroundColor` | `triggerButtonCollapsedColor`, `triggerButtonExpandedColor`, `triggerButtonAnimationColor` (see note) |
| `captureButtonTintColor` | `triggerButtonTintColor` |
| `fastFindButtonVisible` | `barcodeFindButtonVisible` |

> **Note on `captureButtonBackgroundColor`:** v7 splits this single property into three separate color properties — one for the collapsed trigger-button state, one for the expanded state, and one for the animation. If the project set a single color, apply it to all three unless the user indicates otherwise.

### SparkScanView removed APIs

Remove any usage of these properties — they no longer exist in v7 and will cause runtime errors:

- `captureButtonActiveBackgroundColor` (on `SparkScanView`)
- `stopCapturingText`, `startCapturingText`, `resumeCapturingText`, `scanningCapturingText` — the trigger button no longer displays text
- `handModeButtonVisible` (on `SparkScanView`) — the trigger is now fully floating
- `defaultHandMode` (on `SparkScanViewSettings`)
- `soundModeButtonVisible` (on `SparkScanView`)
- `hapticModeButtonVisible` (on `SparkScanView`)
- `shouldShowScanAreaGuides` (on `SparkScanView`)

### `triggerButtonCollapseTimeout` default change

The default value changed from `-1` (never collapse) to `5` (collapse after 5 seconds).

- If the project **already sets** `triggerButtonCollapseTimeout` explicitly, leave it as is.
- If the project **does not set it**, do not add it automatically. Instead, tell the user that the trigger button will now collapse after 5 seconds by default and that they can set the property to `-1` to restore the always-expanded behavior.

### New v7 APIs (optional, no action required unless the user wants them)

Mention only if the user asks:
- `triggerButtonVisible` — hide/show the trigger button entirely
- `triggerButtonImage` — custom trigger-button artwork
- `SparkScanViewState` — controls the initial UI state of the view
- `defaultMiniPreviewSize` — configures mini-preview dimensions
- `miniPreviewCloseControlVisible` — shows/hides the mini-preview close button

### BarcodeTracking → BarcodeBatch rename

If the project uses `BarcodeTracking` (MatrixScan) alongside SparkScan, rename all occurrences to `BarcodeBatch` (including `Scandit.BarcodeTracking` → `Scandit.BarcodeBatch`). The API is otherwise unchanged.

### Scan intention default change

The default scan intention is now `Smart`. If the project explicitly set `ScanIntention.Manual` or another value on `BarcodeCaptureSettings` or `SparkScanSettings`, leave it as is. If the project relied on an explicit `Smart` setting that is now the default, the code still works — no change needed.

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

### Capture mode factory deprecation: `SparkScan.forSettings` → `new SparkScan`

The static factory method is deprecated in v8. Construct the mode directly instead.

**v7:**
```javascript
const sparkScan = Scandit.SparkScan.forSettings(sparkScanSettings);
```

**v8:**
```javascript
const sparkScan = new Scandit.SparkScan(sparkScanSettings);
```

The same pattern applies to other capture modes the project may use alongside SparkScan:
- `BarcodeCapture.forContext(context, settings)` → `new Scandit.BarcodeCapture(settings)` + `context.addMode(barcodeCapture)` (or `context.setMode(...)`)
- `BarcodeBatch.forContext(context, settings)` → `new Scandit.BarcodeBatch(settings)` + `context.addMode(...)` / `context.setMode(...)`
- `BarcodeSelection.forContext(context, settings)` → `new Scandit.BarcodeSelection(settings)` + `context.addMode(...)` / `context.setMode(...)`

**Important:** `SparkScan` itself is **not** added to the context via `setMode`/`addMode`. It is bound to the context implicitly when you create the view with `Scandit.SparkScanView.forContext(context, sparkScan, ...)`. The `setMode`/`addMode` rule applies to other capture modes only.

### `SparkScanView.forContext` behavior

`Scandit.SparkScanView.forContext(context, sparkScan, settings)` still exists in v8 and remains the recommended way to create the view. The public constructor is now private — if any legacy code tries to call `new Scandit.SparkScanView(...)` directly, replace it with `Scandit.SparkScanView.forContext(...)`.

### `dispose()` is now async

`SparkScanView.dispose()` returns a `Promise<void>` in v8. If the project calls `dispose()` synchronously in a teardown handler, it will still work (the promise is fire-and-forget), but for deterministic teardown — especially in navigation handlers that need to await cleanup — `await` the call:

```javascript
await sparkScanView.dispose();
```

### New v8 APIs (optional, no action required unless the user wants them)

Available in v8 on `SparkScanView` — mention only if the user asks:
- `labelCaptureButtonVisible`
- `toolbarBackgroundColor`, `toolbarIconActiveTintColor`, `toolbarIconInactiveTintColor`
- `previewCloseControlVisible`, `zoomSwitchControlVisible`, `cameraSwitchButtonVisible`
- Text scanning in SparkScan (beta, opt-in) — additive, no existing code breaks

---

## After applying changes

1. Run `cordova prepare` after any additional plugin changes (e.g. if you re-added a platform during migration).
2. Build the iOS and Android apps and fix any remaining runtime errors using the API reference (linked in `SKILL.md`).
3. Let the user know they can check the full list of SDK changes in the official migration guides:
   - 6 → 7: https://docs.scandit.com/sdks/cordova/migrate-6-to-7/
   - 7 → 8: https://docs.scandit.com/sdks/cordova/migrate-7-to-8/
4. Show the user a summary of only the changes actually made: which files were edited, which properties were renamed/removed, and anything that required a judgment call (e.g. how `captureButtonBackgroundColor` was split across three v7 properties, or whether `dispose()` calls were converted to `await`). Do not list APIs that were already correct or unchanged.
5. If runtime errors persist, fetch the SparkScan API reference (https://docs.scandit.com/data-capture-sdk/cordova/barcode-capture/api.html) to find the correct API before guessing.
