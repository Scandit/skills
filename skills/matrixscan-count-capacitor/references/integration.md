# MatrixScan Count Capacitor Integration Guide

MatrixScan Count (API class: `BarcodeCount`) is a data capture mode that implements an out-of-the-box scan and count solution. It simultaneously detects multiple barcodes in a single camera frame, tracks and counts them, and renders a full-screen native UI via `BarcodeCountView`. Typical use cases: receiving, inventory count, packing-slip verification, stock-taking.

> **Language note**: Examples below use JavaScript. The same API works identically with TypeScript — adapt imports and add type annotations to match the user's project.

## Prerequisites

- Scandit Capacitor packages installed:
  - `scandit-capacitor-datacapture-core`
  - `scandit-capacitor-datacapture-barcode`
- After installing, run `npx cap sync` to sync the native projects.
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test
- **Minimum Capacitor SDK version: 6.18** for BarcodeCount. Constructor `new BarcodeCount(settings)` requires **7.6**.
- Camera permissions configured by the app:
  - iOS: `NSCameraUsageDescription` in `Info.plist`
  - Android: handled automatically by the plugin
- BarcodeCount runs on iOS and Android only. Guard with `Capacitor.isNativePlatform()` if your app also targets web.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it is important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask them which file they would like to integrate MatrixScan Count into (typically the app entry point or a page module). Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Install packages: `npm install scandit-capacitor-datacapture-core scandit-capacitor-datacapture-barcode`
2. Run `npx cap sync` to apply native changes.
3. Add `NSCameraUsageDescription` to `ios/App/App/Info.plist`.
4. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with your key from https://ssl.scandit.com.
5. Add `<div id="data-capture-view">` to the scanning screen in your HTML and size it to fill the camera area.
6. Store references to `barcodeCount` and `barcodeCountView` on `window` or at module scope to prevent garbage collection.

## Step 1 — Initialize Plugins and Create DataCaptureContext

Plugin initialization **must** happen before any other Scandit API call.

```javascript
import {
  DataCaptureContext,
  ScanditCaptureCorePlugin,
} from 'scandit-capacitor-datacapture-core';

// Must be called first — sets up all Scandit plugins
await ScanditCaptureCorePlugin.initializePlugins();

const context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
```

> **Important**: Always call `ScanditCaptureCorePlugin.initializePlugins()` before `DataCaptureContext.initialize()` or any other Scandit API. Skipping this step causes undefined behavior.

## Step 2 — Set Up the Camera

```javascript
import {
  Camera,
  FrameSourceState,
} from 'scandit-capacitor-datacapture-core';

import { BarcodeCount } from 'scandit-capacitor-datacapture-barcode';

// Use the recommended camera settings for BarcodeCount
const camera = Camera.withSettings(BarcodeCount.recommendedCameraSettings);
await context.setFrameSource(camera);
```

> **Note**: `BarcodeCount.recommendedCameraSettings` is a static getter. On SDK ≥7.6 you can also call `BarcodeCount.createRecommendedCameraSettings()` (static method).

## Step 3 — Configure BarcodeCountSettings

Choose which barcode symbologies to scan. Only enable what you need.

```javascript
import {
  BarcodeCountSettings,
  Symbology,
} from 'scandit-capacitor-datacapture-barcode';

const settings = new BarcodeCountSettings();

settings.enableSymbologies([
  Symbology.EAN13UPCA,
  Symbology.EAN8,
  Symbology.UPCE,
  Symbology.Code39,
  Symbology.Code128,
  Symbology.QR,
  Symbology.DataMatrix,
]);

// Optional: adjust per-symbology settings
const code39Settings = settings.settingsForSymbology(Symbology.Code39);
code39Settings.activeSymbolCounts = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20];

// Optional: if you only expect unique barcodes (improves performance)
settings.expectsOnlyUniqueBarcodes = true;
```

### BarcodeCountSettings Key Properties and Methods

| API | Description |
|-----|-------------|
| `enableSymbologies(symbologies)` | Enable multiple symbologies at once. |
| `enableSymbology(symbology, enabled)` | Enable or disable a single symbology. |
| `settingsForSymbology(symbology)` | Get per-symbology settings (e.g. `activeSymbolCounts`). |
| `enabledSymbologies` | Read-only array of currently enabled symbologies. |
| `expectsOnlyUniqueBarcodes` | `boolean`. Set `true` if each barcode in a batch is unique — enables optimizations. Do not set if duplicates are expected. |
| `filterSettings` | `BarcodeFilterSettings`. Access or modify barcode filtering at the settings level. |
| `clusteringMode` | `ClusteringMode`. Controls barcode clustering. (Cap ≥8.3) |
| `setProperty(name, value)` / `getProperty(name)` | Advanced property access by name. |

### Filtering (Cap ≥6.18)

If several barcode types appear on the same label or package, you can scan only the ones you want and filter the rest out. Filtering is configured on `BarcodeCountSettings.filterSettings` (a `BarcodeFilterSettings`) by symbology, by symbol count, or by a regex on the decoded data.

Exclude specific symbologies — for example scan Code 128 but never PDF417:

```javascript
import {
  BarcodeCountSettings,
  Symbology,
} from 'scandit-capacitor-datacapture-barcode';

const settings = new BarcodeCountSettings();
settings.enableSymbologies([Symbology.Code128, Symbology.PDF417]);

const filterSettings = settings.filterSettings;
filterSettings.excludedSymbologies = [Symbology.PDF417];
```

Exclude barcodes whose data matches a regex — for example all codes starting with `1234`:

```javascript
const filterSettings = settings.filterSettings;
filterSettings.excludedCodesRegex = '^1234.*';
```

> **Note**: By default, filtered-out barcodes are highlighted transparently. Use `BarcodeFilterHighlightSettings` (assigned via `barcodeCountView.filterSettings`) to change the color and transparency of filtered highlights.

| API | Available | Description |
|-----|-----------|-------------|
| `filterSettings.excludedSymbologies` | Cap ≥6.18 | `Symbology[]`. Symbologies to exclude from counting. |
| `filterSettings.excludedCodesRegex` | Cap ≥6.18 | `string`. Regex; barcodes whose data matches are excluded. |
| `filterSettings.setExcludedSymbolCounts(counts, symbology)` | Cap ≥6.18 | Exclude specific symbol counts for a symbology. |

### Clustering (Cap ≥8.3)

Clustering groups multiple barcodes together — either automatically by visual context or manually by the operator on screen. It is configured via `BarcodeCountSettings.clusteringMode`. Clustering is disabled by default.

```javascript
import { ClusteringMode } from 'scandit-capacitor-datacapture-core';
import { BarcodeCountSettings } from 'scandit-capacitor-datacapture-barcode';

const settings = new BarcodeCountSettings();
settings.clusteringMode = ClusteringMode.AutoWithManualCorrection;
```

| `ClusteringMode` value | Description |
|------------------------|-------------|
| `ClusteringMode.Disabled` | No clustering is performed. Default. |
| `ClusteringMode.Manual` | Operator selects which barcodes to cluster using the on-screen UI. |
| `ClusteringMode.Auto` | Clustering is performed automatically and cannot be tuned manually. |
| `ClusteringMode.AutoWithManualCorrection` | Clustering is automatic but clusters can be formed or dissolved manually. |

> **Note**: When clustering is enabled, recognized clusters are exposed on the session. Set `textForClusteringGestureHint` to localize the on-screen clustering gesture hint.

## Step 4 — Create BarcodeCount Mode

```javascript
import { BarcodeCount } from 'scandit-capacitor-datacapture-barcode';

// SDK ≥7.6: context-less constructor; context wired via addMode or BarcodeCountView
window.barcodeCount = new BarcodeCount(settings);

// Then add to context (required when using the context-less constructor):
context.addMode(window.barcodeCount);
```

> **SDK <7.6 fallback**: If targeting earlier SDK versions, use:
> ```javascript
> window.barcodeCount = BarcodeCount.forDataCaptureContext(context, settings);
> ```
> The context-based factory automatically adds the mode to the context.

### BarcodeCount Key Methods and Properties

| API | Description |
|-----|-------------|
| `new BarcodeCount(settings)` | Constructor (≥7.6). No context argument. |
| `BarcodeCount.forDataCaptureContext(context, settings)` | Static factory (<7.6). Adds mode to context automatically. |
| `BarcodeCount.recommendedCameraSettings` | Static getter. Returns recommended `CameraSettings`. |
| `addListener(listener)` | Register a `BarcodeCountListener`. |
| `removeListener(listener)` | Remove a previously added listener. |
| `reset()` | Reset the session, clearing all tracked/scanned barcodes. |
| `startScanningPhase()` | Programmatically start the scanning phase (same as tapping shutter). |
| `endScanningPhase()` | Disable the mode and switch off the frame source. |
| `setBarcodeCountCaptureList(captureList)` | Enable "scan against a list" mode. Pass a `BarcodeCountCaptureList`. |
| `setAdditionalBarcodes(barcodes)` | Inject barcodes as partial results (for multi-session workflows). |
| `clearAdditionalBarcodes()` | Clear previously injected additional barcodes. |
| `isEnabled` | `boolean`. Enable or disable the mode without resetting state. |
| `feedback` | `BarcodeCountFeedback`. Configure sound and haptic feedback. |

## Step 5 — Add a BarcodeCountListener (optional)

The `didScan` callback is invoked once the scanning phase is complete (i.e. after the user taps the shutter button). Use it to access `session.recognizedBarcodes`.

```javascript
window.barcodeCount.addListener({
  didScan: async (barcodeCount, session) => {
    const recognized = session.recognizedBarcodes;
    // recognized is an array of Barcode objects
    for (const barcode of recognized) {
      console.log(`Scanned: ${barcode.data} (${barcode.symbology})`);
    }
  },
});
```

> **Note**: `onSessionUpdated` (≥8.3) is also available on Capacitor and is called on every frame update, not just after the shutter press.

### BarcodeCountListener Interface

| Callback | Signature | Description |
|----------|-----------|-------------|
| `didScan` | `(barcodeCount, session, getFrameData?) => Promise<void>` | Invoked once the scanning phase completes (shutter press). |
| `onSessionUpdated` | `(barcodeCount, session, getFrameData?) => Promise<void>` | Called on every frame update (≥8.3). |

### BarcodeCountSession Properties

| Property | Type | Available | Description |
|----------|------|-----------|-------------|
| `recognizedBarcodes` | `Barcode[]` | Cap ≥7.0 | All currently recognized barcodes. |
| `additionalBarcodes` | `Barcode[]` | Cap ≥6.18 | Barcodes injected via `setAdditionalBarcodes`. |
| `frameSequenceID` | `number` | Cap ≥6.18 | Current frame sequence identifier. |
| `reset()` | `Promise<void>` | Cap ≥6.18 | Reset the session inside the listener callback. |

## Step 6 — Create BarcodeCountView and Connect to DOM

`BarcodeCountView` provides the full-screen MatrixScan Count UI (shutter button, list button, exit button, hints, highlights). It must be connected to a DOM element to determine its position and size.

```javascript
import {
  BarcodeCountView,
  BarcodeCountViewStyle,
} from 'scandit-capacitor-datacapture-barcode';

// Create the view (object literal constructor — verified in sample)
window.barcodeCountView = new BarcodeCountView({
  context,
  barcodeCount: window.barcodeCount,
  style: BarcodeCountViewStyle.Icon, // or BarcodeCountViewStyle.Dot
});

// Connect to a DOM element
window.barcodeCountView.connectToElement(document.getElementById('data-capture-view'));
```

> **Alternative static factories** (also documented, pick one pattern and stick to it):
> ```javascript
> // Without style (defaults to Dot)
> const view = BarcodeCountView.forContextWithMode(context, barcodeCount);
> // With explicit style
> const view = BarcodeCountView.forContextWithModeAndStyle(context, barcodeCount, BarcodeCountViewStyle.Icon);
> ```

### BarcodeCountViewStyle Values

| Value | Description |
|-------|-------------|
| `BarcodeCountViewStyle.Icon` | Draws highlights as icons with an animation on first appearance. Default in the sample. |
| `BarcodeCountViewStyle.Dot` | Draws highlights as dots with an animation on first appearance. Required for brush customization (see below). |

### Enabling Scanning

After constructing the view and connecting it to the DOM element, enable the mode and start the camera:

```javascript
camera.switchToDesiredState(FrameSourceState.On);
barcodeCount.isEnabled = true;
```

### BarcodeCountView Lifecycle Methods

| Method | Available | Description |
|--------|-----------|-------------|
| `connectToElement(htmlElement)` | Cap ≥6.18 | Attach the view to a DOM element. The view mirrors its size and position. |
| `detachFromElement()` | Cap ≥6.18 | Detach from the DOM element and release resources. Call on cleanup. |
| `setFrame(rect, isUnderContent)` | Cap ≥6.18 | Alternative to `connectToElement`: manually set size and position. Do not use together with `connectToElement`. |
| `show()` | Cap ≥6.18 | Show the view (only when using `setFrame`). |
| `hide()` | Cap ≥6.18 | Hide the view (only when using `setFrame`). |
| `clearHighlights()` | Cap ≥6.18 | Clear all barcode highlight overlays from the screen. Does not affect the session. |
| `setToolbarSettings(settings)` | Cap ≥6.18 | Configure text and accessibility for the toolbar. Pass a `BarcodeCountToolbarSettings` instance. |
| `setStatusProvider(provider)` | Cap ≥8.3 | Set a `BarcodeCountStatusProvider` for status mode. |

## Step 7 — Wire UI Listeners

### BarcodeCountViewUiListener

Receives callbacks when the user taps the built-in UI buttons.

```javascript
window.barcodeCountView.uiListener = {
  didTapListButton: (view) => {
    // User tapped the list/check button — typically navigate to results
    console.log('List button tapped');
  },
  didTapExitButton: (view) => {
    // User tapped the exit button — typically end the session
    console.log('Exit button tapped');
  },
  didTapSingleScanButton: (view) => {
    // User tapped the single scan button (if shown)
    console.log('Single scan button tapped');
  },
};
```

### BarcodeCountViewListener

Receives callbacks when the user taps individual barcode highlights (requires MatrixScan AR add-on). Also provides per-barcode brush customization when using `BarcodeCountViewStyle.Dot`.

```javascript
window.barcodeCountView.listener = {
  didTapRecognizedBarcode: (view, trackedBarcode) => {
    console.log(`Tapped recognized: ${trackedBarcode.barcode.data}`);
  },
  didTapFilteredBarcode: (view, filteredBarcode) => {
    console.log(`Tapped filtered: ${filteredBarcode.barcode.data}`);
  },
  didTapRecognizedBarcodeNotInList: (view, trackedBarcode) => {
    console.log(`Tapped not-in-list: ${trackedBarcode.barcode.data}`);
  },
  didCompleteCaptureList: (view) => {
    console.log('All capture list items scanned!');
  },
  // Brush callbacks — called from rendering thread, only with Dot style:
  brushForRecognizedBarcode: (view, trackedBarcode) => {
    return new Brush(Color.fromHex('#00CC0066'), Color.fromHex('#00CC00'), 2.0);
  },
  brushForRecognizedBarcodeNotInList: (view, trackedBarcode) => {
    return new Brush(Color.fromHex('#FF000066'), Color.fromHex('#FF0000'), 2.0);
  },
};
```

> **Note**: The tap callbacks and `brushFor*` callbacks require the **MatrixScan AR add-on** on your Scandit license.

## Step 8 — Scanning Against a List (CaptureList)

> **Critical — read before writing any list-matching code**: The ONLY correct way to validate scanned barcodes against an expected list is `BarcodeCountCaptureList` + `TargetBarcode`. Do NOT compare `session.recognizedBarcodes` against a plain JavaScript array or a `Set`. A plain array gives you no matched/not-in-list breakdown, no `missingBarcodes`, and no `didCompleteCaptureList` callback. The CaptureList API is the only path that produces all three session states described below.

### 8.1 — Model the target list from a packing slip or backend API

Your backend typically returns an array of items like this:

```javascript
// JSON from a packing slip or warehouse API
const packingSlip = [
  { symbology: 'ean13UPCA', data: '9781234567897', quantity: 2 },
  { symbology: 'ean13UPCA', data: '4012345678901', quantity: 1 },
  { symbology: 'code128',   data: 'WH-A491-BOX',  quantity: 3 },
  { symbology: 'qr',        data: 'SERIAL-00042',  quantity: 1 },
];
```

Convert each item to a `TargetBarcode` and bundle into a `BarcodeCountCaptureList`:

```javascript
import {
  BarcodeCountCaptureList,
  TargetBarcode,
} from 'scandit-capacitor-datacapture-barcode';

// 1. Convert packing-slip rows to TargetBarcode objects.
//    quantity must be ≥ 1.
const targetBarcodes = packingSlip.map(item =>
  TargetBarcode.create(item.data, item.quantity)
);

// 2. Define the capture-list listener (wired below).
const captureListListener = {
  // Called after every frame in which the list state changes.
  didUpdateSession: (captureList, session) => {
    // session.correctBarcodes  — TrackedBarcode[] matched to a target
    // session.wrongBarcodes    — TrackedBarcode[] scanned but not in the list
    // session.missingBarcodes  — TargetBarcode[]  targets not yet scanned
    const matched  = session.correctBarcodes.length;
    const extra    = session.wrongBarcodes.length;
    const missing  = session.missingBarcodes.length;
    const total    = targetBarcodes.length;

    console.log(`${matched}/${total} matched, ${extra} extra, ${missing} still missing`);

    // Surface progress in the app UI:
    updateProgressUI(matched, total, extra);
  },

  // Called (Cap ≥8.3) when every target barcode has been scanned.
  didCompleteCaptureList: (captureList, session) => {
    console.log('All list items scanned — packing slip complete!');
    showResultsScreen(session);
  },
};

// 3. Create the capture list (listener first, then targets).
const captureList = BarcodeCountCaptureList.create(
  captureListListener,
  targetBarcodes,
);
```

### 8.2 — Wire the capture list to BarcodeCount

```javascript
// Must be called after BarcodeCount is constructed and before scanning starts.
// Without this call, no list-matching occurs and the session properties
// correctBarcodes / wrongBarcodes / missingBarcodes are never populated.
window.barcodeCount.setBarcodeCountCaptureList(captureList);
```

> **Important**: `setBarcodeCountCaptureList` must be called before the scanning phase begins. If you call it after `startScanningPhase()` the first frame may be processed without the list attached.

### 8.3 — Brushes for the three visual states (Dot style only)

When using `BarcodeCountViewStyle.Dot`, you can assign distinct brushes to each matching state so operators immediately understand scan status:

```javascript
import { Brush, Color } from 'scandit-capacitor-datacapture-core';
import { BarcodeCountViewStyle } from 'scandit-capacitor-datacapture-barcode';

// Must be created with Dot style to use brush customization:
window.barcodeCountView = new BarcodeCountView({
  context,
  barcodeCount: window.barcodeCount,
  style: BarcodeCountViewStyle.Dot,
});

// Green  — barcode matched a target in the list.
// Available: Cap ≥6.18
window.barcodeCountView.recognizedBrush = new Brush(
  Color.fromHex('#00CC0066'),  // semi-transparent green fill
  Color.fromHex('#00CC00'),    // solid green stroke
  2.0,
);

// Orange — barcode was accepted by the operator via the not-in-list action
//          (requires BarcodeCountNotInListActionSettings.enabled = true).
// Available: Cap ≥7.1
window.barcodeCountView.acceptedBrush = new Brush(
  Color.fromHex('#FF880066'),
  Color.fromHex('#FF8800'),
  2.0,
);

// Red    — barcode scanned but not present in the capture list.
// Available: Cap ≥6.18
window.barcodeCountView.notInListBrush = new Brush(
  Color.fromHex('#FF000066'),
  Color.fromHex('#FF0000'),
  2.0,
);
```

### 8.4 — Wire `BarcodeCountCaptureListListener.didUpdateSession`

The `didUpdateSession` callback (shown in full above) is the place to read matching results. Key session properties:

| Property | Type | Available | Description |
|----------|------|-----------|-------------|
| `session.correctBarcodes` | `TrackedBarcode[]` | Cap ≥6.18 | Barcodes that matched a target in the list. |
| `session.wrongBarcodes` | `TrackedBarcode[]` | Cap ≥6.18 | Barcodes scanned but not in the target list. |
| `session.missingBarcodes` | `TargetBarcode[]` | Cap ≥6.18 | Targets that have not yet been scanned. |
| `session.acceptedBarcodes` | `TrackedBarcode[]` | Cap ≥7.1 | Barcodes the operator explicitly accepted. |
| `session.rejectedBarcodes` | `TrackedBarcode[]` | Cap ≥7.1 | Barcodes the operator explicitly rejected. |

> **Note**: This listener fires alongside (not instead of) `BarcodeCountListener.didScan`. Both are active at the same time; `didScan` fires at the end of the scanning phase, `didUpdateSession` fires on every frame that changes list state.

### 8.5 — Progress UI

```javascript
// Enable the built-in progress bar (requires a capture list to be set).
// Available: Cap ≥6.25
window.barcodeCountView.shouldShowListProgressBar = true;

// Update a custom progress banner from didUpdateSession:
function updateProgressUI(matched, total, extra) {
  const pct = total > 0 ? Math.round((matched / total) * 100) : 0;
  document.getElementById('progress-label').textContent =
    `${matched} of ${total} items scanned (${pct}%)` +
    (extra > 0 ? ` — ${extra} extra item(s) found` : '');
}
```

### 8.6 — Results screen

When the operator taps the list button (or after `didCompleteCaptureList` fires), show a results screen with three sections derived from the final session:

```javascript
function showResultsScreen(session) {
  // 1. Matched — targets found on the packing slip
  const matched = session.correctBarcodes.map(tb => ({
    data: tb.barcode.data,
    symbology: tb.barcode.symbology,
    status: 'found',
  }));

  // 2. Missing — targets that were never scanned
  const missing = session.missingBarcodes.map(tb => ({
    data: tb.data,
    quantity: tb.quantity,
    status: 'missing',
  }));

  // 3. Unexpected — scanned barcodes not in the list
  const unexpected = session.wrongBarcodes.map(tb => ({
    data: tb.barcode.data,
    symbology: tb.barcode.symbology,
    status: 'unexpected',
  }));

  renderResults({ matched, missing, unexpected });
}

// Wire to the UI button:
window.barcodeCountView.uiListener = {
  didTapListButton: (view) => {
    // Read the latest session from the BarcodeCountCaptureListListener
    // (store it in a module-level variable from didUpdateSession)
    showResultsScreen(window.latestCaptureListSession);
  },
};
```

Store the latest session in `didUpdateSession` so it is available when the list button is tapped:

```javascript
let latestCaptureListSession = null;

const captureListListener = {
  didUpdateSession: (captureList, session) => {
    window.latestCaptureListSession = session; // persist for results screen
    // ... progress update code ...
  },
};
```

### 8.7 — Exit and re-entry / swapping lists

The capture list persists across `prepareScanning` calls. To start a new packing slip without reconstructing the entire stack:

```javascript
// Swap in a new list (e.g. next packing slip):
async function swapList(newPackingSlip) {
  const newTargetBarcodes = newPackingSlip.map(item =>
    TargetBarcode.create(item.data, item.quantity)
  );
  const newCaptureList = BarcodeCountCaptureList.create(
    captureListListener,
    newTargetBarcodes,
  );

  window.barcodeCount.setBarcodeCountCaptureList(newCaptureList);

  // Clear visual highlights left over from the previous list.
  await window.barcodeCountView.clearHighlights();

  // Reset the BarcodeCount session so scanned-barcode counts start fresh.
  await window.barcodeCount.reset();
}
```

### 8.8 — Common pitfalls

> **Do NOT use a plain JS array for list matching.** A pattern like this is wrong:
> ```javascript
> // WRONG — do not do this
> const expected = new Set(['9781234567897', '4012345678901']);
> barcodeCount.addListener({
>   didScan: (bc, session) => {
>     for (const b of session.recognizedBarcodes) {
>       if (expected.has(b.data)) { /* ... */ }
>     }
>   }
> });
> ```
> This produces no `correctBarcodes`/`wrongBarcodes`/`missingBarcodes` breakdown, no per-barcode highlight differentiation, and no `didCompleteCaptureList` notification. `BarcodeCountCaptureList` is the ONLY correct approach.

Additional pitfalls:

- **`TargetBarcode.create(data, quantity)` — quantity must be ≥ 1.** Passing 0 or a negative number is invalid.
- **Symbology must be enabled.** Items in the target list are matched by data value only; ensure every symbology that appears in the list is enabled in `BarcodeCountSettings` via `enableSymbology` or `enableSymbologies`. A barcode that cannot be decoded will never match.
- **`didCompleteCaptureList` is Cap ≥8.3.** On earlier SDK versions use `didUpdateSession` with `session.missingBarcodes.length === 0` to detect completion.
- **The list listener fires alongside `BarcodeCountListener.didScan`.** Both are active simultaneously. `didScan` fires once at the end of the scanning phase; `didUpdateSession` fires on every frame that changes list state.

### TargetBarcode

| API | Available | Description |
|-----|-----------|-------------|
| `TargetBarcode.create(data, quantity)` | Cap ≥6.18 | Static factory. `data`: barcode string. `quantity`: expected scan count (≥1). |
| `.data` | Cap ≥6.18 | The barcode data string. |
| `.quantity` | Cap ≥6.18 | Expected number of occurrences. |

### BarcodeCountCaptureList

| API | Available | Description |
|-----|-----------|-------------|
| `BarcodeCountCaptureList.create(listener, targetBarcodes)` | Cap ≥6.18 | Static factory. `listener`: object implementing `didUpdateSession`. `targetBarcodes`: `TargetBarcode[]`. |
| `setBarcodeDataTransformer(transformer)` | Cap ≥8.3 | Transform barcode data before list matching (e.g. strip check digits). |

## Step 9 — BarcodeCountView Customization

`BarcodeCountView` exposes a large set of properties to control visibility, appearance, text, and accessibility. All properties below are available on Capacitor (minimum version noted where it differs from the base 6.18).

### Visibility Booleans

| Property | Default | Description |
|----------|---------|-------------|
| `shouldShowUserGuidanceView` | `true` | Show the user guidance/loading view (prompts to scan, move closer/further). |
| `shouldShowListProgressBar` | `true` | Show progress bar when a capture list is set. (Cap ≥6.25) |
| `shouldShowListButton` | `true` | Show the list button (bottom-left). Triggers `didTapListButton`. |
| `shouldShowExitButton` | `true` | Show the exit button (bottom-right). Triggers `didTapExitButton`. |
| `shouldShowShutterButton` | `true` | Show the centered shutter button. |
| `shouldShowHints` | `true` | Show scanning-progress hint messages. |
| `shouldShowClearHighlightsButton` | `false` | Show "clear highlights" button above the shutter button. |
| `shouldShowSingleScanButton` | `false` | Show the single-scan button (bottom-left). Triggers `didTapSingleScanButton`. |
| `shouldShowStatusModeButton` | `false` | Show the status-mode toggle button. Requires `setStatusProvider`. (Cap ≥8.3) |
| `shouldShowFloatingShutterButton` | `false` | Show a draggable floating shutter button. |
| `shouldShowToolbar` | `true` | Show the collapsible toolbar at the top. |
| `shouldShowScanAreaGuides` | `false` | Visualize the scan area (debugging only). |
| `shouldShowTorchControl` | `false` | Show the torch button. (Cap ≥6.26) |
| `shouldShowStatusIconsOnScan` | `false` | Immediately show status icons after scan without needing to activate status mode. When `true`, `shouldShowStatusModeButton` is ignored. (Cap ≥8.3) |
| `shouldDisableModeOnExitButtonTapped` | `true` | Automatically disable the mode when exit button is tapped. (Cap ≥7.0) |
| `tapToUncountEnabled` | `false` | Allow tapping a highlight to deselect/uncount that item. (Cap ≥7.0) |

Example — minimal UI (no toolbar, no exit button):
```javascript
window.barcodeCountView.shouldShowToolbar = false;
window.barcodeCountView.shouldShowExitButton = false;
```

### Brushes (Dot Style Only)

Brushes are only applied when the view uses `BarcodeCountViewStyle.Dot`. Setting a brush to `null` hides highlights for that barcode category.

| Property | Available | Description |
|----------|-----------|-------------|
| `recognizedBrush` | Cap ≥6.18 | Brush for recognized barcodes (or those in the capture list). |
| `notInListBrush` | Cap ≥6.18 | Brush for recognized barcodes not in the capture list. |
| `acceptedBrush` | Cap ≥7.1 | Brush for accepted barcodes (via not-in-list action). |
| `rejectedBrush` | Cap ≥7.1 | Brush for rejected barcodes (via not-in-list action). |

Static default brush accessors:
| API | Available | Description |
|-----|-----------|-------------|
| `BarcodeCountView.defaultRecognizedBrush` | Cap ≥6.18 | Default recognized brush. |
| `BarcodeCountView.defaultNotInListBrush` | Cap ≥6.18 | Default not-in-list brush. |
| `BarcodeCountView.defaultAcceptedBrush` | Cap ≥7.1 | Default accepted brush. |
| `BarcodeCountView.defaultRejectedBrush` | Cap ≥7.1 | Default rejected brush. |

Per-barcode brush overrides (override the property-level brush for a single barcode):
```javascript
// Call from inside didScan or from the viewListener brush callbacks
await view.setBrushForRecognizedBarcode(trackedBarcode, new Brush(...));   // Cap ≥7.1
await view.setBrushForRecognizedBarcodeNotInList(trackedBarcode, new Brush(...)); // Cap ≥7.1
await view.setBrushForAcceptedBarcode(trackedBarcode, new Brush(...));     // Cap ≥7.1
await view.setBrushForRejectedBarcode(trackedBarcode, new Brush(...));     // Cap ≥7.1
```

Example — custom brushes:
```javascript
import { Brush, Color } from 'scandit-capacitor-datacapture-core';

// Only effective with BarcodeCountViewStyle.Dot
window.barcodeCountView.recognizedBrush = new Brush(
  Color.fromHex('#00CC0066'),  // fill (semi-transparent green)
  Color.fromHex('#00CC00'),    // stroke (solid green)
  2.0,                         // stroke width
);
window.barcodeCountView.notInListBrush = new Brush(
  Color.fromHex('#FF000066'),
  Color.fromHex('#FF0000'),
  2.0,
);
```

### Customizable Button Text

| Property | Available | Description |
|----------|-----------|-------------|
| `exitButtonText` | Cap ≥6.18 | Text label for the exit button. |
| `clearHighlightsButtonText` | Cap ≥6.18 | Text label for the clear highlights button. |

### Hint Text Customization

All hint text properties are available on Capacitor ≥6.18 unless noted:

| Property | Available | Default hint |
|----------|-----------|-------------|
| `textForTapShutterToScanHint` | Cap ≥6.18 | "Tap shutter to scan" prompt |
| `textForScanningHint` | Cap ≥6.18 | In-progress scanning hint |
| `textForMoveCloserAndRescanHint` | Cap ≥6.18 | Move closer hint |
| `textForMoveFurtherAndRescanHint` | Cap ≥6.18 | Move further hint |
| `textForBarcodesNotInListDetectedHint` | Cap ≥8.3 | Hint when a not-in-list barcode is detected |
| `textForScreenCleanedUpHint` | Cap ≥8.3 | Hint after screen is cleaned |
| `textForTapToUncountHint` | Cap ≥7.0 | Hint when user uncounts an item |
| `textForClusteringGestureHint` | Cap ≥8.3 | Hint for clustering gesture |

### Localizing All Customer-Facing Text

> **Important**: When localizing the scanning UI, you must touch ALL of the following property groups — not just the hint strings. Missing any group leaves untranslated text visible to end users or screen-reader users.

**Group 1 — Button labels** (text visible on the buttons themselves):

| Property | Available | Description |
|----------|-----------|-------------|
| `exitButtonText` | Cap ≥6.18 | Label on the exit button. |
| `clearHighlightsButtonText` | Cap ≥6.18 | Label on the clear-highlights button. |

**Group 2 — Hint strings** (instructional overlays, listed above in the table).

**Group 3 — iOS VoiceOver accessibility labels and hints** (announced to screen-reader users; must be translated):

| Property | Available |
|----------|-----------|
| `listButtonAccessibilityLabel` / `listButtonAccessibilityHint` | Cap ≥6.18 |
| `exitButtonAccessibilityLabel` / `exitButtonAccessibilityHint` | Cap ≥6.18 |
| `shutterButtonAccessibilityLabel` / `shutterButtonAccessibilityHint` | Cap ≥6.18 |
| `floatingShutterButtonAccessibilityLabel` / `floatingShutterButtonAccessibilityHint` | Cap ≥6.18 |
| `singleScanButtonAccessibilityLabel` / `singleScanButtonAccessibilityHint` | Cap ≥6.18 |
| `clearHighlightsButtonAccessibilityLabel` / `clearHighlightsButtonAccessibilityHint` | Cap ≥6.18 |
| `statusModeButtonAccessibilityLabel` / `statusModeButtonAccessibilityHint` | Cap ≥8.3 |

**Group 4 — Android TalkBack content descriptions** (equivalent to VoiceOver labels for Android):

| Property | Available |
|----------|-----------|
| `listButtonContentDescription` | Cap ≥6.18 |
| `exitButtonContentDescription` | Cap ≥6.18 |
| `shutterButtonContentDescription` | Cap ≥6.18 |
| `floatingShutterButtonContentDescription` | Cap ≥6.18 |
| `singleScanButtonContentDescription` | Cap ≥6.18 |
| `clearHighlightsButtonContentDescription` | Cap ≥6.18 |
| `statusModeButtonContentDescription` | Cap ≥8.3 |

**Complete French-localization example** — all four groups:

```javascript
const view = window.barcodeCountView;

// Group 1 — Button labels
view.exitButtonText             = 'Quitter';
view.clearHighlightsButtonText  = 'Effacer les mises en évidence';

// Group 2 — Hint strings
view.textForTapShutterToScanHint        = 'Appuyez pour scanner';
view.textForScanningHint                = 'Scan en cours…';
view.textForMoveCloserAndRescanHint     = 'Rapprochez-vous et re-scannez';
view.textForMoveFurtherAndRescanHint    = 'Éloignez-vous et re-scannez';
view.textForTapToUncountHint            = 'Appuyez pour désélectionner';
view.textForBarcodesNotInListDetectedHint = 'Code-barres non listé détecté'; // Cap ≥8.3
view.textForScreenCleanedUpHint         = 'Écran nettoyé';                   // Cap ≥8.3
view.textForClusteringGestureHint       = 'Geste de regroupement';           // Cap ≥8.3

// Group 3 — iOS VoiceOver
view.listButtonAccessibilityLabel              = 'Liste des articles';
view.listButtonAccessibilityHint               = 'Affiche la liste des articles scannés';
view.exitButtonAccessibilityLabel              = 'Quitter';
view.exitButtonAccessibilityHint               = 'Termine la session de scan';
view.shutterButtonAccessibilityLabel           = 'Déclencheur';
view.shutterButtonAccessibilityHint            = 'Lance le scan';
view.floatingShutterButtonAccessibilityLabel   = 'Déclencheur flottant';
view.floatingShutterButtonAccessibilityHint    = 'Lance le scan (flottant)';
view.singleScanButtonAccessibilityLabel        = 'Scan individuel';
view.singleScanButtonAccessibilityHint         = 'Scanne un seul article';
view.clearHighlightsButtonAccessibilityLabel   = 'Effacer';
view.clearHighlightsButtonAccessibilityHint    = 'Efface toutes les mises en évidence';

// Group 4 — Android TalkBack
view.listButtonContentDescription              = 'Liste des articles';
view.exitButtonContentDescription              = 'Quitter';
view.shutterButtonContentDescription           = 'Déclencheur';
view.floatingShutterButtonContentDescription   = 'Déclencheur flottant';
view.singleScanButtonContentDescription        = 'Scan individuel';
view.clearHighlightsButtonContentDescription   = 'Effacer les mises en évidence';
```

### Hardware Trigger (Android, Cap ≥7.1)

```javascript
// Android: enable hardware trigger (volume-down key or XCover dedicated button)
if (BarcodeCountView.hardwareTriggerSupported) {
  await view.enableHardwareTrigger(null); // null = default key
}

// iOS: enable volume-button trigger (Cap ≥7.1, iOS only)
view.hardwareTriggerEnabled = true; // Cap ≥7.1, iOS only
```

- `BarcodeCountView.hardwareTriggerSupported` (static, Android only, Cap ≥7.1): `true` if device API ≥28.
- `view.enableHardwareTrigger(keyCode)` (Cap ≥7.1, Android only): Pass `null` for default key, or a specific keycode.
- `view.hardwareTriggerEnabled` (Cap ≥7.1, iOS only): Set `true` to enable volume-button trigger.

### Torch Control

```javascript
import { Anchor } from 'scandit-capacitor-datacapture-core';

view.shouldShowTorchControl = true;              // Cap ≥6.26
view.torchControlPosition = Anchor.TopRight;     // Cap ≥6.26
// Supported anchors: TopLeft, TopRight, BottomLeft, BottomRight
```

### Not-In-List Action Settings (Cap ≥7.1)

When a capture list is set, `BarcodeCountNotInListActionSettings` controls the action popup shown when users tap not-in-list barcodes.

```javascript
import { BarcodeCountNotInListActionSettings } from 'scandit-capacitor-datacapture-barcode';

const notInListSettings = window.barcodeCountView.barcodeNotInListActionSettings;
notInListSettings.enabled = true;
notInListSettings.acceptButtonText = 'Accept';
notInListSettings.rejectButtonText = 'Reject';
notInListSettings.cancelButtonText = 'Cancel';
notInListSettings.barcodeAcceptedHint = 'Barcode accepted';
notInListSettings.barcodeRejectedHint = 'Barcode rejected';
// Re-assign to apply changes
window.barcodeCountView.barcodeNotInListActionSettings = notInListSettings;
```

### Filter Settings

```javascript
// Access view-level filter settings
window.barcodeCountView.filterSettings = myBarcodeFilterHighlightSettings;
```

## Step 10 — Status Mode (Cap ≥8.3, Beta)

Status mode shows contextual stock-status icons on top of each scanned barcode. Provide a `BarcodeCountStatusProvider` implementation and call `setStatusProvider`.

```javascript
import {
  BarcodeCountStatus,
  BarcodeCountStatusItem,
  BarcodeCountStatusResultSuccess,
} from 'scandit-capacitor-datacapture-barcode';

// Enable status mode button (user activates status mode by tapping it)
window.barcodeCountView.shouldShowStatusModeButton = true;

// Or: auto-show status icons immediately after scan (recommended approach)
window.barcodeCountView.shouldShowStatusIconsOnScan = true;

// Provide a status provider
window.barcodeCountView.setStatusProvider({
  onStatusRequested: (barcodes, callback) => {
    const statusItems = barcodes.map(trackedBarcode => {
      // Look up the real status from your system
      const status = getStockStatus(trackedBarcode.barcode.data);
      return BarcodeCountStatusItem.create(trackedBarcode, status);
    });

    const result = BarcodeCountStatusResultSuccess.create(
      statusItems,
      'Status mode enabled',    // message shown when status mode activates
      'Status mode disabled',   // message shown when status mode exits
    );
    callback.onStatusReady(result);
  },
});

// Example status lookup (replace with real logic)
function getStockStatus(data) {
  if (data.startsWith('EXP')) return BarcodeCountStatus.Expired;
  if (data.startsWith('LOW')) return BarcodeCountStatus.LowStock;
  return BarcodeCountStatus.None;
}
```

### BarcodeCountStatus Values

| Value | Description |
|-------|-------------|
| `BarcodeCountStatus.None` | No status. |
| `BarcodeCountStatus.NotAvailable` | Error retrieving status. |
| `BarcodeCountStatus.Expired` | Item is expired. |
| `BarcodeCountStatus.Fragile` | Fragile item. |
| `BarcodeCountStatus.QualityCheck` | Quality check needed. |
| `BarcodeCountStatus.LowStock` | Low stock. |
| `BarcodeCountStatus.Wrong` | Wrong item. |
| `BarcodeCountStatus.ExpiringSoon` | Item will expire soon. (Cap ≥8.3) |

### Status Result Types

| Class | Description |
|-------|-------------|
| `BarcodeCountStatusResultSuccess.create(statusItems, enabledMsg, disabledMsg)` | Success — provides status list. |
| `BarcodeCountStatusResultError.create(statusItems, errorMsg, disabledMsg)` | Partial success with error message. |
| `BarcodeCountStatusResultAbort.create(errorMsg)` | Critical failure — aborts status mode. |

## Step 11 — Feedback

```javascript
import { BarcodeCountFeedback } from 'scandit-capacitor-datacapture-barcode';

// Use default feedback (sound + vibration for both success and failure)
window.barcodeCount.feedback = BarcodeCountFeedback.default;

// Silence all feedback
window.barcodeCount.feedback = BarcodeCountFeedback.emptyFeedback; // Cap ≥7.1
```

### BarcodeCountFeedback Properties

| Property | Type | Description |
|----------|------|-------------|
| `success` | `Feedback` | Feedback for a successful scan event. |
| `failure` | `Feedback` | Feedback for a failure event. |

## Step 12 — Teardown

```javascript
async function uninitialize() {
  if (camera) {
    await camera.switchToDesiredState(FrameSourceState.Off);
    camera = null;
  }
  if (window.barcodeCountView) {
    window.barcodeCountView.detachFromElement();
    window.barcodeCountView = null;
  }
  if (window.barcodeCount) {
    window.barcodeCount.isEnabled = false;
    window.barcodeCount = null;
  }
}
```

## Step 13 — HTML Setup

`BarcodeCountView` requires a DOM container element. The `<div id="data-capture-view">` must be present on the scanning screen and be sized to fill the camera area.

### Minimal HTML

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>MatrixScan Count</title>
  <meta name="viewport" content="viewport-fit=cover, width=device-width, initial-scale=1.0,
    minimum-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <style>
    html, body {
      margin: 0;
      padding: 0;
      width: 100vw;
      height: 100vh;
      overflow: hidden;
    }
    #data-capture-view {
      width: 100%;
      height: 100%;
    }
  </style>
</head>
<body>
  <div id="data-capture-view"></div>
  <script type="module" src="js/app.js"></script>
</body>
</html>
```

## Step 14 — Complete Example

A full working app with BarcodeCount, scan listener, and UI listeners.

```javascript
import {
  Camera,
  DataCaptureContext,
  FrameSourceState,
  ScanditCaptureCorePlugin,
} from 'scandit-capacitor-datacapture-core';

import {
  BarcodeCount,
  BarcodeCountSettings,
  BarcodeCountView,
  BarcodeCountViewStyle,
  Symbology,
} from 'scandit-capacitor-datacapture-barcode';

let context;
let camera;

async function initializeSDK() {
  if (!context) {
    context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
  }

  // Set up camera with recommended settings for BarcodeCount
  camera = Camera.withSettings(BarcodeCount.recommendedCameraSettings);
  await context.setFrameSource(camera);

  // Configure symbologies
  const settings = new BarcodeCountSettings();
  settings.enableSymbologies([
    Symbology.EAN13UPCA,
    Symbology.EAN8,
    Symbology.Code128,
    Symbology.QR,
  ]);

  // Create BarcodeCount mode
  window.barcodeCount = new BarcodeCount(settings);
  context.addMode(window.barcodeCount);

  // Register scan listener
  window.barcodeCount.addListener({
    didScan: async (barcodeCount, session) => {
      const barcodes = session.recognizedBarcodes;
      console.log(`Scanned ${barcodes.length} barcodes`);
      for (const b of barcodes) {
        console.log(`  ${b.data} (${b.symbology})`);
      }
    },
  });

  // Create and connect the view
  window.barcodeCountView = new BarcodeCountView({
    context,
    barcodeCount: window.barcodeCount,
    style: BarcodeCountViewStyle.Icon,
  });

  window.barcodeCountView.uiListener = {
    didTapListButton: (view) => {
      // Navigate to results page
      showResults();
    },
    didTapExitButton: (view) => {
      // Exit the scan screen
      uninitialize();
    },
  };

  window.barcodeCountView.connectToElement(document.getElementById('data-capture-view'));

  // Start camera and enable mode
  camera.switchToDesiredState(FrameSourceState.On);
  window.barcodeCount.isEnabled = true;
}

async function uninitialize() {
  if (camera) {
    await camera.switchToDesiredState(FrameSourceState.Off);
    camera = null;
  }
  if (window.barcodeCountView) {
    window.barcodeCountView.detachFromElement();
    window.barcodeCountView = null;
  }
  if (window.barcodeCount) {
    window.barcodeCount.isEnabled = false;
    window.barcodeCount = null;
  }
}

function showResults() {
  // App-specific navigation
}

window.addEventListener('load', async () => {
  await ScanditCaptureCorePlugin.initializePlugins();
  await initializeSDK();
});
```

## Key Rules

1. **Initialize plugins first** — `await ScanditCaptureCorePlugin.initializePlugins()` must be called before any other Scandit API. Capacitor-specific requirement.
2. **Minimum SDK 6.18** — BarcodeCount is not available on Capacitor before 6.18.
3. **Context-less constructor ≥7.6** — `new BarcodeCount(settings)` is available from 7.6. For earlier versions use `BarcodeCount.forDataCaptureContext(context, settings)`.
4. **Context wiring** — When using `new BarcodeCount(settings)`, you must separately call `context.addMode(barcodeCount)`.
5. **DOM container required** — `BarcodeCountView` must be connected to a DOM element via `connectToElement(element)`. Do not use together with `setFrame`.
6. **Enable the mode** — `barcodeCount.isEnabled = true` must be set after creating the view and connecting to the DOM element, or scanning will not start.
7. **Camera** — Use `BarcodeCount.recommendedCameraSettings`, attach via `Camera.withSettings(...)`, and switch on with `camera.switchToDesiredState(FrameSourceState.On)`.
8. **Teardown** — Call `barcodeCountView.detachFromElement()` and `camera.switchToDesiredState(FrameSourceState.Off)` when leaving the scanning screen.
9. **Brush customization** — The `recognizedBrush`, `notInListBrush`, `acceptedBrush`, `rejectedBrush` properties and per-barcode brush methods only apply when using `BarcodeCountViewStyle.Dot`.
10. **Status mode is beta** — `shouldShowStatusModeButton`, `setStatusProvider`, `shouldShowStatusIconsOnScan`, and related classes are available from Cap 8.3 and are explicitly marked beta.
11. **Imports** — Core types from `scandit-capacitor-datacapture-core`; barcode/count types from `scandit-capacitor-datacapture-barcode`. `Brush`, `Color`, `Anchor` come from core.
12. **Cap sync** — Run `npx cap sync` after installing or updating Scandit packages.
13. **Prevent garbage collection** — Store `barcodeCount` and `barcodeCountView` on `window` or at module scope.
14. **Camera permissions** — iOS requires `NSCameraUsageDescription` in `Info.plist`. Android handles it automatically.
15. **Native only** — BarcodeCount does not run in the browser. Guard with `Capacitor.isNativePlatform()` if needed.
16. **List scanning requires CaptureList** — Never compare `session.recognizedBarcodes` against a plain JS array or `Set` to validate a packing list. Use `BarcodeCountCaptureList.create(listener, targetBarcodes)` + `barcodeCount.setBarcodeCountCaptureList(captureList)`. Only then do `session.correctBarcodes`, `session.wrongBarcodes`, and `session.missingBarcodes` populate in `didUpdateSession`.
17. **Localize all text groups** — When localizing, set button labels (`exitButtonText`, `clearHighlightsButtonText`), all `textForXxxHint` properties, all `*AccessibilityLabel` / `*AccessibilityHint` pairs (iOS VoiceOver), and all `*ContentDescription` properties (Android TalkBack). Missing any group leaves untranslated text for end users or screen-reader users.
