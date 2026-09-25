# SparkScan Web Migration Guide

## Step 1: Detect the installed SDK version

Before making any changes, find out which version of the Scandit SDK the project currently has installed.

Check in this order:

1. **package.json** — open `<ProjectRoot>/package.json` and look for `@scandit/web-datacapture-core` or `@scandit/web-datacapture-barcode` (v7+) or `scandit-web-datacapture-core` / `scandit-web-datacapture-barcode` (v6). The version number is in the value field.
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

Find the files that use SparkScan (search for `SparkScan`, `SparkScanView`, `SparkScanViewSettings`) and apply the relevant changes below directly to those files.

---

## Migration: 6 → 7

### Package and hosting changes

v7 introduces critical changes to how the Web SDK is installed and hosted:

| Change | Old (v6) | New (v7+) |
|---|---|---|
| NPM scope | `scandit-web-datacapture-core`, `scandit-web-datacapture-barcode` | `@scandit/web-datacapture-core`, `@scandit/web-datacapture-barcode` |
| Engine directory | `build/engine` | `sdc-lib` |

Apply these changes:
1. Update all import statements to use the new scoped package names
2. Update `libraryLocation` paths from `build/engine` to `sdc-lib` (or the project's equivalent self-hosted path)

### Where these properties live in v6

**On `SparkScanView`** (set on the view instance after it is created):

- All button visibility and color/text properties listed below

**On `SparkScanViewSettings`** (set before creating the view):

- `defaultHandMode` only

When searching the project for these properties, look for usages on both the view instance and the settings object.

### SparkScan API renames

Apply these renames everywhere they appear in the project. These are renames — always replace the old name with the new one, preserving the existing value, regardless of what that value is:

| Old (v6, on `SparkScanView`) | New (v7) |
|---|---|
| `isTorchButtonVisible` | `isTorchControlVisible` |
| `captureButtonBackgroundColor` | `triggerButtonCollapsedColor`, `triggerButtonExpandedColor`, `triggerButtonAnimationColor` (see note) |
| `captureButtonTintColor` | `triggerButtonTintColor` |
| `isFastFindButtonVisible` | `isBarcodeFindButtonVisible` |

> **Note on `captureButtonBackgroundColor`:** v7 splits this into three separate color properties for the collapsed state, expanded state, and animation. If the user set a single color, apply it to all three unless they indicate otherwise.

### SparkScan removed APIs

Remove any usage of these properties — they no longer exist in v7 and will cause type/build errors:

- `captureButtonActiveBackgroundColor` (on `SparkScanView`)
- `stopCapturingText`, `startCapturingText`, `resumeCapturingText`, `scanningCapturingText` — the trigger button no longer displays text (on `SparkScanView`)
- `isHandModeButtonVisible` (on `SparkScanView`)
- `defaultHandMode` (on `SparkScanViewSettings`)
- `isSoundModeButtonVisible` (on `SparkScanView`)
- `isHapticModeButtonVisible` (on `SparkScanView`)
- `shouldShowScanAreaGuides` (on `SparkScanView`)

### `triggerButtonCollapseTimeout` default change

The default value changed from `-1` (never collapse) to `5` (collapse after 5 seconds).

- If the project **already sets** `triggerButtonCollapseTimeout` explicitly, leave it as is.
- If the project **does not set it**, do not add it automatically. Instead, inform the user that the button will now collapse after 5 seconds by default and they can set it to `-1` if they want the old behavior.

### New v7 APIs (optional, no action required unless the user wants them)

These are available in v7 — mention them only if the user asks:

- `SparkScanViewState` — sets the initial UI state of the SparkScan view
- `defaultMiniPreviewSize` — configures mini preview dimensions
- `miniPreviewCloseControlVisible` — shows or hides the mini preview close button

### BarcodeTracking → BarcodeBatch rename

If the project uses `BarcodeTracking` (MatrixScan) alongside SparkScan, rename all occurrences to `BarcodeBatch`. The API is otherwise unchanged.

### Scan intention

The default scan intention is now `ScanIntention.Smart`. If the project explicitly set `ScanIntention.Manual` or another value on `BarcodeCaptureSettings` or `SparkScanSettings`, leave it as is. If the project relied on an explicit `ScanIntention.Smart` setting that is now the default, the code still works — no change needed.

> If the user wants to use `ScanIntention.Smart` or `ScanIntention.SmartSelection`, browser multithreading must be enabled. This requires the server to set the following HTTP headers on the HTML page and serving the sdc-lib files:
>
> - `Cross-Origin-Opener-Policy: same-origin`
> - `Cross-Origin-Embedder-Policy: require-corp` (self-hosted SDK) or `credentialless` (CDN-hosted SDK)
>
> See the [multithreading guide](https://docs.scandit.com/sdks/web/matrixscan/get-started/#improve-runtime-performance-by-enabling-browser-multithreading) and [cross-origin headers guide](https://docs.scandit.com/sdks/web/matrixscan/get-started/#configure-cross-origin-headers).

---

## Migration: 7 → 8

### DataCaptureContext initialization change

v8 replaces `configure()` + `DataCaptureContext.create()` with a single `DataCaptureContext.forLicenseKey()` call.

**Old (v7):**
```typescript
import { configure, DataCaptureContext } from "@scandit/web-datacapture-core";

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

await DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --", {
    libraryLocation: new URL("sdc-lib", document.baseURI).toString(),
    moduleLoaders: [barcodeCaptureLoader()],
});
```

Apply this change:
1. Remove the `configure` import from `@scandit/web-datacapture-core`
2. Replace the `configure({ ... })` call and `DataCaptureContext.create()` with `DataCaptureContext.forLicenseKey(licenseKey, { libraryLocation, moduleLoaders })`
3. If the code stored the result of `DataCaptureContext.create()` in a variable and passed it to `SparkScanView.forElement`, replace it with `DataCaptureContext.sharedInstance`

### SparkScan text scanning (beta, opt-in)

v8 adds the ability to scan text alongside barcodes in SparkScan. This is purely additive and opt-in — no existing code breaks. Mention it only if the user asks about new features.

---

## After applying changes

1. Build the project and fix any remaining type or build errors using the API reference (linked in SKILL.md).
2. Let the user know they can check the full list of SDK changes in the official migration guides:
   - 6 → 7: <https://docs.scandit.com/sdks/web/migrate-6-to-7/>
   - 7 → 8: <https://docs.scandit.com/sdks/web/migrate-7-to-8/>
3. Show the user a summary of only the changes actually made: which files were edited, which properties were renamed/removed, and anything that required a judgment call (e.g., how `captureButtonBackgroundColor` was split). Do not list APIs that were already correct or unchanged.
4. If type or build errors persist after the changes above, fetch the [SparkScan API reference](https://docs.scandit.com/data-capture-sdk/web/barcode-capture/api.html) to find the correct API before guessing.
