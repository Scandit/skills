# BarcodeCapture React Native Migration Guide

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

### No source-level renames on `BarcodeCapture` itself

The `BarcodeCapture`, `BarcodeCaptureSettings`, `BarcodeCaptureOverlay`, and `BarcodeCaptureListener` surfaces are stable across 6 → 7. The `forContext` factory, the `didScan` / `didUpdateSession` listener signatures, and the overlay's `viewfinder`, `brush`, and `shouldShowScanAreaGuides` properties all remain valid.

If the v6 code looks structurally correct after the package bump and the points above, no further source edits are needed for 6 → 7 of `BarcodeCapture`.

---

## Migration: 7 → 8

### `DataCaptureContext.forLicenseKey` → `DataCaptureContext.initialize`

This is the **main breaking change** on React Native in v8. The context factory method was renamed and its semantics tightened — it no longer returns the instance directly; the singleton is read from `DataCaptureContext.sharedInstance`.

**v7:**
```typescript
const context = DataCaptureContext.forLicenseKey('YOUR_LICENSE_KEY');
```

**v8:**
```typescript
DataCaptureContext.initialize('YOUR_LICENSE_KEY');
const context = DataCaptureContext.sharedInstance;
```

Replace every call to `DataCaptureContext.forLicenseKey(...)` with `DataCaptureContext.initialize(...)` and replace subsequent references to the returned context with `DataCaptureContext.sharedInstance`. This call must still happen **before** any other Scandit API.

A common v8 idiom is to put both lines in a small `CaptureContext.ts` module and export `DataCaptureContext.sharedInstance` as the default export — see `references/integration.md` step 1.

### Capture mode factory deprecation: `BarcodeCapture.forContext` → `new BarcodeCapture` + `addMode`

The `BarcodeCapture.forContext(context, settings)` factory is deprecated in v8. The v8 idiom is to construct the mode directly and attach it to the context yourself.

**v7:**
```typescript
const barcodeCapture = BarcodeCapture.forContext(dataCaptureContext, settings);
```

**v8:**
```typescript
const barcodeCapture = new BarcodeCapture(settings);
dataCaptureContext.addMode(barcodeCapture);
```

The `forContext` form still works in v8 for backwards compatibility, but new code should use the constructor + `addMode` form.

The same pattern applies to other capture modes the project may use:
- `BarcodeBatch.forContext(context, settings)` → `new BarcodeBatch(settings)` + `context.addMode(...)`
- `BarcodeSelection.forContext(context, settings)` → `new BarcodeSelection(settings)` + `context.addMode(...)`

### `BarcodeCaptureOverlay.withBarcodeCaptureForView` → `new BarcodeCaptureOverlay` + `addOverlay`

The overlay has a v7.6+ constructor that mirrors the mode pattern.

**v7:**
```typescript
const overlay = BarcodeCaptureOverlay.withBarcodeCaptureForView(barcodeCapture, dataCaptureView);
```

**v8:**
```typescript
const overlay = new BarcodeCaptureOverlay(barcodeCapture);
dataCaptureView.addOverlay(overlay);
```

The legacy factory still works — passing a non-null view auto-attaches.

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
