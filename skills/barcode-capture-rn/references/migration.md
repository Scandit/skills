# BarcodeCapture React Native Migration Guide

## Migration principles

- **Authority.** When this guide and the API reference disagree, trust the API reference — and a runtime check in the user's project — over this guide. Say which source you followed and why in the summary.
- **Behaviour changes.** Never present a visual or behaviour change (new default, different overlay look, changed feedback, changed scan timing) as a 1:1 rename. List each one in the summary as a judgment call the user must confirm.
- **Compatibility layer.** When the scanning code sits behind a shared scanner library or wrapper that other code calls, keep that library's public API frozen (same types, method names, callbacks) and change only the Scandit calls underneath.
- **Dual-version code.** When code must run on both the old and the target version, branch at run time on a symbol this guide lists as removed in the target version — never on a version string, and never on the presence of the new API. A deprecated symbol that is still present proves nothing about the installed version. Example: `BarcodeCapture.forContext` is unchanged on Web but **removed** on React Native, Capacitor and Cordova v8, so probing for it does tell v7 from v8 on those platforms — a deprecated-but-still-present symbol would not.

## Step 1: Detect the installed SDK version

Before making any changes, find out which version of the Scandit React Native packages the project currently has installed.

Check in this order:

1. **`package.json`** — look for the entries `scandit-react-native-datacapture-core` and/or `scandit-react-native-datacapture-barcode`. The value next to them is the installed version constraint (e.g. `"^6.28.0"`, `"~7.6.0"`, `"^8.0.0"`).
2. **`package-lock.json`** or **`yarn.lock`** — if `package.json` only has a range, check the lockfile for the exact resolved version.

Once you know the installed version, determine which migration path applies:

| Installed version | Target version | Action |
|---|---|---|
| 6.x | 7.x | Apply the **6 → 7 migration** below |
| 7.x | 8.x | Apply the **7 → 8 migration** below |
| 6.x | 8.x | Apply **both migrations in order** (6→7 first, then 7→8) |

If neither package is in `package.json`, the project is not using BarcodeCapture on React Native yet — fall back to `references/integration.md` instead of migrating.

---

## Step 2: Update the package version

Before touching source files, update the Scandit package versions in `package.json`:

```json
{
  "dependencies": {
    "scandit-react-native-datacapture-core": "^8.0.0",
    "scandit-react-native-datacapture-barcode": "^8.0.0"
  }
}
```

Then install and re-link native projects:

```bash
npm install
npx pod-install     # iOS — required after every plugin version change
```

`npx pod-install` is **required** on iOS after every plugin version change — it resolves the new CocoaPods artifacts into `ios/Podfile.lock`. Android auto-links via Gradle; a regular `npx react-native run-android` picks up the new version.

If Metro is running, restart it with `--reset-cache` so the JavaScript bundle reflects the new package.

---

## Step 3: Apply source code changes

Find the files that use BarcodeCapture (search the project for `BarcodeCapture`, `BarcodeCaptureSettings`, `BarcodeCaptureOverlay`, `BarcodeCaptureListener`) and apply the relevant changes below directly to those files.

---

## Migration: 6 → 7

### Scan intention default change

The default scan intention for `BarcodeCaptureSettings` is now `ScanIntention.Smart` (as of v7). The Smart algorithm intelligently identifies and scans the barcode the user intends to capture when several are visible.

- If the project explicitly set `settings.scanIntention = ScanIntention.Manual` or another value, leave it as is.
- If the project relied on the v6 default (which was effectively `Manual`), the code still runs but behavior changes. Tell the user about the change and let them opt back into `ScanIntention.Manual` if they prefer the old behavior.

### `codeDuplicateFilter` default change

From SDK 7.1, the default `codeDuplicateFilter` value is the special `-2` sentinel — its behavior depends on `scanIntention`:

- With `ScanIntention.Smart` (default), it enables the Smart Duplicate Filter algorithm.
- With `ScanIntention.Manual`, it behaves as if `codeDuplicateFilter` were set to 1500 ms.

If the project explicitly set `codeDuplicateFilter` to a positive value, `0`, or `-1`, leave it. If it relied on the v6 default, mention the change to the user — no code change required.

### BarcodeTracking → BarcodeBatch rename

If the project uses `BarcodeTracking` (MatrixScan) alongside BarcodeCapture, rename all occurrences to `BarcodeBatch`. Imports from `scandit-react-native-datacapture-barcode` need updating. The API is otherwise unchanged.

### Mostly stable, with one exception: `recommendedCameraSettings`

The `BarcodeCapture`, `BarcodeCaptureSettings`, `BarcodeCaptureOverlay`, and `BarcodeCaptureListener` surfaces are otherwise stable across 6 → 7. The `forContext` factory, the `didScan` / `didUpdateSession` listener signatures, and the overlay's `viewfinder`, `brush`, and `shouldShowScanAreaGuides` properties all remain valid.

If v6 code uses the `BarcodeCapture.recommendedCameraSettings` getter to configure the camera, it keeps working through v7 (deprecated since 7.6) — no change required to reach v7. From 7.6 onward `BarcodeCapture.createRecommendedCameraSettings()` is also available and is the only form that survives into v8.

### Other v7 removals

- `LaserlineViewfinderStyle` is removed. `LaserlineViewfinder` never had a `color` property — use `enabledColor` / `disabledColor`.
- `RectangularViewfinderStyle.Legacy` is removed (`Rounded` and `Square` remain). **Judgment call:** the default `RectangularViewfinder` style also changed from `Legacy` to `Rounded` in v7 — flag this as a visual change for the user to confirm; there is no identical replacement for `Legacy`.
- `BarcodeCaptureOverlayStyle.Legacy` is removed (only `Frame` remains).
- The static `BarcodeCaptureOverlay.defaultBrush` is removed.
- Listener callbacks (`didScan`, `didUpdateSession`) are now typed to return `Promise<void>`.

If the v6 code looks structurally correct after the package bump and the points above, no further source edits are needed for 6 → 7 of `BarcodeCapture`.

---

## Migration: 7 → 8

### `DataCaptureContext.forLicenseKey` → `DataCaptureContext.initialize`

`forLicenseKey` still exists and works in v8 — this is not a breaking change. `initialize` (available since 7.2) is the preferred call going forward and returns the shared `DataCaptureContext` instance.

**v7:**
```typescript
const context = DataCaptureContext.forLicenseKey('YOUR_LICENSE_KEY');
```

**v8:**
```typescript
const context = DataCaptureContext.initialize('YOUR_LICENSE_KEY');
```

Replace every call to `DataCaptureContext.forLicenseKey(...)` with `DataCaptureContext.initialize(...)`, preserving the argument and the returned instance. This call must still happen **before** any other Scandit API.

A common v8 idiom is to put both lines in a small `CaptureContext.ts` module and export `DataCaptureContext.sharedInstance` as the default export — see `references/integration.md` step 1.

### `BarcodeCapture.forContext` removed → `new BarcodeCapture` + `addMode`

The `BarcodeCapture.forContext(context, settings)` factory is **removed in v8**; code that still calls it will fail to compile. Construct the mode directly and attach it to the context yourself. `addMode` now returns a `Promise`.

**v7:**
```typescript
const barcodeCapture = BarcodeCapture.forContext(dataCaptureContext, settings);
```

**v8:**
```typescript
const barcodeCapture = new BarcodeCapture(settings);
await dataCaptureContext.addMode(barcodeCapture);
```

The same pattern applies to other capture modes the project may use:
- `BarcodeBatch.forContext(context, settings)` → `new BarcodeBatch(settings)` + `context.addMode(...)`
- `BarcodeSelection.forContext(context, settings)` → `new BarcodeSelection(settings)` + `context.addMode(...)`

### `BarcodeCaptureOverlay.withBarcodeCaptureForView*` removed → `new BarcodeCaptureOverlay` + `addOverlay`

All `withBarcodeCapture*` static factories (including `withBarcodeCaptureForViewWithStyle`) are **removed in v8**. Use the v7.6+ constructor plus an explicit `addOverlay` call, which now returns a `Promise`.

**v7:**
```typescript
const overlay = BarcodeCaptureOverlay.withBarcodeCaptureForView(barcodeCapture, dataCaptureView);
```

**v8:**
```typescript
const overlay = new BarcodeCaptureOverlay(barcodeCapture);
await dataCaptureView.addOverlay(overlay);
```

### Other v8 removals and changes

- `BarcodeCapture.recommendedCameraSettings` getter is **removed**; use `BarcodeCapture.createRecommendedCameraSettings()` (available since 7.6).
- `BarcodeCaptureOverlayStyle` enum is **removed entirely**.
- `BarcodeCaptureSettings.batterySavingMode` → renamed `batterySaving`.
- `Camera.isTorchAvailable` changes from a `boolean` getter to a `Promise<boolean>` getter (also available as `getIsTorchAvailable()`).
- `context.addMode` / `context.setMode` / `context.removeMode`, and `view.addOverlay`, now return a `Promise`. (RN has no `connectToElement`.)

### Never valid in any version

- `SymbologySettings.extensions` is private in every version — use `setExtensionEnabled(symbology, true)` instead of assigning to `extensions`.
- A `BarcodeCaptureFeedback` object literal is a type error in every version — construct an instance and assign its properties.
- `Vibration` has no public constructor in any version — use its static getters (e.g. `Vibration.defaultVibration`).
- `LaserlineViewfinder.color` never existed — use `enabledColor` / `disabledColor`.

### Cleanup: `dataCaptureContext.dispose()` → `dataCaptureContext.removeMode(barcodeCapture)`

In v7, a common pattern was calling `dataCaptureContext.dispose()` in the `useEffect` cleanup. In v8, the context is a process-wide singleton (`DataCaptureContext.sharedInstance`) and **should not** be disposed when a single screen unmounts — doing so would break any other Scandit screen mounted in the same app.

Replace:

```typescript
// v7
return () => {
  dataCaptureContext.dispose();
};
```

with:

```typescript
// v8
return () => {
  dataCaptureView.removeOverlay(overlay);
  barcodeCapture.removeListener(listener);
  dataCaptureContext.removeMode(barcodeCapture);
};
```

This unbinds the BarcodeCapture mode from the shared context without tearing the context itself down.

### New v8 APIs (optional, no action required unless the user wants them)

Available in v8 — mention only if the user asks:
- `BarcodeCaptureSettings.selectionMode` (`SelectionMode.Off | On | Auto`) — explicit tap-to-confirm selection on top of barcode capture.
- `useFocusEffect` lifecycle pattern combined with `Camera.switchToDesiredState(FrameSourceState.On / Off)` is the v8 recommended way to drive the camera on RN.

---

## After applying changes

1. Run `npm install && npx pod-install` again after any additional package changes triggered by the migration (e.g. if TypeScript type errors surface additional version mismatches).
2. Restart Metro with `npm start -- --reset-cache` so the bundle picks up the new package code.
3. Build the iOS and Android apps and fix any remaining compile / runtime errors using the API reference (linked in `SKILL.md`).
4. Let the user know they can check the full list of SDK changes in the official migration guides:
   - 6 → 7: https://docs.scandit.com/sdks/react-native/migrate-6-to-7/
   - 7 → 8: https://docs.scandit.com/sdks/react-native/migrate-7-to-8/
5. Show the user a summary of only the changes actually made: which files were edited, which calls were replaced, and anything that required a judgment call (e.g. whether a `dataCaptureContext.dispose()` call was converted to `removeMode`, whether `forContext` was rewritten to `new BarcodeCapture` + `addMode`). Do not list APIs that were already correct or unchanged.
6. If compile errors persist after the changes above, fetch the BarcodeCapture API reference (https://docs.scandit.com/data-capture-sdk/react-native/barcode-capture/api.html) to find the correct API before guessing.
