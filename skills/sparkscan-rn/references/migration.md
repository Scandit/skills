# SparkScan React Native Migration Guide

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

If neither package is in `package.json`, the project is not using SparkScan on React Native yet — fall back to `references/integration.md` instead of migrating.

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

Find the files that use SparkScan (search the project for `SparkScan`, `SparkScanView`, `SparkScanSettings`, `SparkScanViewSettings`) and apply the relevant changes below directly to those files.

---

## Migration: 6 → 7

### Where these properties live in v6

**On `SparkScanView`** (set imperatively on the view instance via the `ref` callback, or as component props in legacy class-component code):
- All button visibility, color, and text properties listed below.

**On `SparkScanViewSettings`** (passed to the view via the `sparkScanViewSettings` prop):
- `defaultHandMode` only.

When searching the project for these properties, look for usages on both the view instance and the settings object.

### SparkScanView property renames

Apply these renames everywhere they appear in the project. These are renames — always replace the old name with the new one, preserving the existing value, regardless of what that value is:

| Old (v6, on `SparkScanView`) | New (v7) |
|---|---|
| `torchButtonVisible` | `torchControlVisible` |
| `captureButtonBackgroundColor` | `triggerButtonCollapsedColor`, `triggerButtonExpandedColor`, `triggerButtonAnimationColor` (see note) |
| `captureButtonTintColor` | `triggerButtonTintColor` |
| `fastFindButtonVisible` | `barcodeFindButtonVisible` |

> **Note on `captureButtonBackgroundColor`:** v7 splits this single property into three separate color properties — one for the collapsed trigger-button state, one for the expanded state, and one for the animation. If the project set a single color, apply it to all three unless the user indicates otherwise.

### SparkScanViewUiListener callback rename

If any code registers a ui listener with the legacy v6 callback name, rename it:

| Old (v6, on `SparkScanViewUiListener`) | New (v7) |
|---|---|
| `onFastFindButtonTappedIn(view)` | `onBarcodeFindButtonTappedIn(view)` (still available in v7/v8 as a deprecated alias) / `didTapBarcodeFindButton(view)` (preferred) |

Prefer the `didTap...` form in new code; the `on...TappedIn` variants are kept as deprecated aliases for backwards compatibility.

### SparkScanView removed APIs

Remove any usage of these properties — they no longer exist in v7 and will cause TypeScript/runtime errors:

- `captureButtonActiveBackgroundColor` (on `SparkScanView`)
- `stopCapturingText`, `startCapturingText`, `resumeCapturingText`, `scanningCapturingText` — the trigger button no longer displays text (on `SparkScanView`)
- `handModeButtonVisible` (on `SparkScanView`) — the trigger is now fully floating
- `defaultHandMode` (on `SparkScanViewSettings`)
- `soundModeButtonVisible` (on `SparkScanView`)
- `hapticModeButtonVisible` (on `SparkScanView`)
- `shouldShowScanAreaGuides` (on `SparkScanView`)
- `brush` (on `SparkScanView`) — the highlight brush is now specified per barcode via `SparkScanBarcodeFeedback` returned from `SparkScanFeedbackDelegate.feedbackForBarcode`.

### `triggerButtonCollapseTimeout` default change

The default value changed from `-1` (never collapse) to `5` (collapse after 5 seconds).

- If the project **already sets** `triggerButtonCollapseTimeout` explicitly, leave it as is.
- If the project **does not set it**, do not add it automatically. Instead, tell the user that the trigger button will now collapse after 5 seconds by default and that they can set the property to `-1` to restore the old always-expanded behavior.

### New v7 APIs (optional, no action required unless the user wants them)

These are available in v7 — mention them only if the user asks:
- `triggerButtonVisible` — hide/show the trigger button entirely
- `triggerButtonImage` — custom trigger button artwork
- `SparkScanViewState` — controls the initial UI state of the view
- `defaultMiniPreviewSize` — configures mini-preview dimensions
- `miniPreviewCloseControlVisible` — shows/hides the mini-preview close button
- `SparkScanFeedbackDelegate` / `feedbackDelegate` on the view — per-barcode feedback customization (replaces the v6 `brush` / sound APIs)

### BarcodeTracking → BarcodeBatch rename

If the project uses `BarcodeTracking` (MatrixScan) alongside SparkScan, rename all occurrences to `BarcodeBatch`. Imports from `scandit-react-native-datacapture-barcode` need updating. The API is otherwise unchanged.

### Scan intention default change

The default scan intention is now `Smart`. If the project explicitly set `ScanIntention.Manual` or another value on `BarcodeCaptureSettings` or `SparkScanSettings`, leave it as is. If the project relied on an explicit `Smart` setting that is now the default, the code still works — no change needed.

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

### Capture mode factory deprecation: `SparkScan.forSettings` → `new SparkScan`

The static factory method is deprecated in v8. Construct the mode directly instead.

**v7:**
```typescript
const sparkScan = SparkScan.forSettings(sparkScanSettings);
```

**v8:**
```typescript
const sparkScan = new SparkScan(sparkScanSettings);
```

The same pattern applies to other capture modes the project may use alongside SparkScan:
- `BarcodeCapture.forContext(context, settings)` → `new BarcodeCapture(settings)` + `context.addMode(barcodeCapture)` (or `context.setMode(...)`)
- `BarcodeBatch.forContext(context, settings)` → `new BarcodeBatch(settings)` + `context.addMode(...)` / `context.setMode(...)`
- `BarcodeSelection.forContext(context, settings)` → `new BarcodeSelection(settings)` + `context.addMode(...)` / `context.setMode(...)`

**Important:** `SparkScan` itself is **not** added to the context via `setMode`/`addMode`. It is bound to the context implicitly when `<SparkScanView>` mounts and reads the `sparkScan` and `context` props. The `setMode`/`addMode` rule applies to other capture modes only.

### Cleanup: `dataCaptureContext.dispose()` → `dataCaptureContext.removeMode(sparkScan)`

In v7, a common pattern was calling `dataCaptureContext.dispose()` in the `useEffect` cleanup. In v8, the context is a process-wide singleton (`DataCaptureContext.sharedInstance`) and **should not** be disposed when a single screen unmounts — doing so would break any other SparkScan screen mounted in the same app.

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
  dataCaptureContext.removeMode(sparkScanMode.current);
};
```

This unbinds the SparkScan mode from the shared context without tearing the context itself down.

### New v8 APIs (optional, no action required unless the user wants them)

Available in v8 on `SparkScanView` — mention only if the user asks:
- `labelCaptureButtonVisible` — toggles the label-capture entry point in the toolbar
- `toolbarBackgroundColor`, `toolbarIconActiveTintColor`, `toolbarIconInactiveTintColor` — full toolbar color theming
- `previewCloseControlVisible` — shows/hides the mini-preview close control
- `zoomSwitchControlVisible` — shows/hides the zoom switch
- `cameraSwitchButtonVisible` — shows/hides the front/back camera switch
- Text scanning in SparkScan (beta, opt-in) — v8 adds the ability to scan text alongside barcodes; purely additive, no existing code breaks

---

## After applying changes

1. Run `npm install && npx pod-install` again after any additional package changes triggered by the migration (e.g. if TypeScript type errors surface additional version mismatches).
2. Restart Metro with `npm start -- --reset-cache` so the bundle picks up the new package code.
3. Build the iOS and Android apps and fix any remaining compile / runtime errors using the API reference (linked in `SKILL.md`).
4. Let the user know they can check the full list of SDK changes in the official migration guides:
   - 6 → 7: https://docs.scandit.com/sdks/react-native/migrate-6-to-7/
   - 7 → 8: https://docs.scandit.com/sdks/react-native/migrate-7-to-8/
5. Show the user a summary of only the changes actually made: which files were edited, which properties were renamed/removed, and anything that required a judgment call (e.g. how `captureButtonBackgroundColor` was split across three v7 properties, or whether a `dataCaptureContext.dispose()` call was converted to `removeMode`). Do not list APIs that were already correct or unchanged.
6. If compile errors persist after the changes above, fetch the SparkScan API reference (https://docs.scandit.com/data-capture-sdk/react-native/barcode-capture/api.html) to find the correct API before guessing.
