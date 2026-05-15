# MatrixScan Batch Web Integration Guide

MatrixScan Batch (API name: `BarcodeBatch*`) is a multi-barcode tracking mode that continuously tracks all barcodes visible in the camera feed simultaneously, reporting additions, updates, and removals on every frame. On web it renders through a `DataCaptureView` with one or more overlays — `BarcodeBatchBasicOverlay` for simple per-barcode highlights, and `BarcodeBatchAdvancedOverlay` for fully custom AR views built from HTML elements.

> **Language note**: Examples below use TypeScript (v8 API). For plain JavaScript projects, remove the type annotations and keep the same imports and structure.

> **Multithreading note**: BarcodeBatch requires browser multithreading. Before writing any code, confirm that the server sends the correct cross-origin isolation headers — see the [COOP/COEP section](#cross-origin-isolation-coop--coep) below.

## Starting from zero? Use the pre-built sample

If the user has no existing app yet, always offer the official sample as the fastest path to a working integration.

- **Simple (vanilla TS):** <https://github.com/Scandit/datacapture-web-samples/tree/master/03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanSimpleSample>
- **AR Bubbles (advanced overlay):** <https://github.com/Scandit/datacapture-web-samples/tree/master/03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanBubblesSample>

Tell the user to clone the repo and open the relevant sample folder. Once they have it open, help them:

1. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with their key from <https://ssl.scandit.com>
2. Adjust the enabled symbologies to match their use case
3. Run `npm install` and start the app

Only proceed to the manual integration steps below if the user already has an existing project.

---

## Prerequisites

- Scandit Data Capture SDK for web via npm, pnpm, or yarn:
  - `@scandit/web-datacapture-core`: <https://www.npmjs.com/package/@scandit/web-datacapture-core>
  - `@scandit/web-datacapture-barcode`: <https://www.npmjs.com/package/@scandit/web-datacapture-barcode>
- A valid Scandit license key — sign in at <https://ssl.scandit.com> (no account? sign up at <https://ssl.scandit.com/dashboard/sign-up?p=test>)
- Cross-origin isolation headers configured on the server (required — see below)

### Cross-origin isolation (COOP / COEP)

**BarcodeBatch requires browser multithreading via `SharedArrayBuffer`.** Without these headers the SDK degrades to single-threaded mode, which is too slow for batch tracking.

Always set:
```
Cross-Origin-Opener-Policy: same-origin
```

For `Cross-Origin-Embedder-Policy`, the value depends on how you host the SDK:

| Hosting | COEP value |
|---------|-----------|
| Self-hosted SDK files | `require-corp` |
| CDN (`cdn.jsdelivr.net`) | `credentialless` (Chrome/Edge 96+) |

> **Heads up:** COEP blocks cross-origin resources (images, fonts, iframes, third-party scripts) that do not include `Cross-Origin-Resource-Policy` or `Access-Control-Allow-Origin`. Audit your page's cross-origin dependencies before enabling COEP in production. After changing headers, clear your browser cache and restart the dev server.

For the complete Vite setup — COOP/COEP middleware, `library/engine` self-hosting with `vite-plugin-static-copy`, and license key injection — use the official sample `vite.config.ts` as the source of truth:
<https://github.com/Scandit/datacapture-web-samples/blob/master/03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanSimpleSample/vite.config.ts>

You can also verify multithreading is active at runtime:

```typescript
import { BrowserHelper } from "@scandit/web-datacapture-core";

const ok = await BrowserHelper.checkMultithreadingSupport();
if (!ok) {
  console.warn("Multithreading unavailable. Check COOP/COEP headers.");
}
```

## Integration flow

Ask the user which barcode symbologies they need to scan. Only enable the symbologies actually required — each extra symbology adds processing time.

Once the user responds, ask which file or component they'd like to integrate MatrixScan Batch into. Then write the integration code directly into that file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Install packages: `npm install @scandit/web-datacapture-core @scandit/web-datacapture-barcode`
2. Set cross-origin headers (`COOP: same-origin` + `COEP: require-corp` or `credentialless`) on the server
3. If self-hosting the SDK engine, configure `libraryLocation` to point to the correct path; or use the CDN path: `https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-barcode@8/sdc-lib/`
4. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with your key from <https://ssl.scandit.com>
5. Add a `<div id="data-capture-view">` (or similar) to your HTML with defined dimensions and `position: fixed` or `absolute`

---

## Step 1 — Initialize DataCaptureContext

Create the `DataCaptureView` first so a loading indicator can be shown during SDK initialization, then initialize the context:

```typescript
import {
  Camera,
  DataCaptureContext,
  DataCaptureView,
  FrameSourceState,
} from "@scandit/web-datacapture-core";
import {
  BarcodeBatch,
  BarcodeBatchSettings,
  barcodeCaptureLoader,
  Symbology,
} from "@scandit/web-datacapture-barcode";

async function run(): Promise<void> {
  // Create the view before context init so a progress bar can be shown.
  const view = new DataCaptureView();
  view.connectToElement(document.getElementById("data-capture-view")!);
  view.showProgressBar();

  // Initialize context — must be awaited.
  const context = await DataCaptureContext.forLicenseKey(
    "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
    {
      // Self-hosted path. Use CDN if not self-hosting:
      // https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-barcode@8/sdc-lib/
      libraryLocation: new URL("library/engine/", document.baseURI).toString(),
      moduleLoaders: [barcodeCaptureLoader()],
    }
  );

  // Attach the view to the context (required after context init).
  await view.setContext(context);
  view.hideProgressBar();
}
```

- `DataCaptureContext.forLicenseKey()` is async — always `await` it.
- Use `DataCaptureContext.sharedInstance` or the captured `context` variable throughout.
- The module loader for BarcodeBatch is `barcodeCaptureLoader()` — there is no separate `barcodeBatchLoader`.

## Step 2 — Configure BarcodeBatchSettings and create BarcodeBatch

```typescript
const settings = new BarcodeBatchSettings();

// Enable only the symbologies your app actually needs.
settings.enableSymbologies([
  Symbology.EAN13UPCA,
  Symbology.EAN8,
  Symbology.UPCE,
  Symbology.Code39,
  Symbology.Code128,
]);

// Create the mode — async on web.
const barcodeBatch = await BarcodeBatch.forContext(context, settings);
```

### BarcodeBatchSettings members

| Member | Description |
|--------|-------------|
| `new BarcodeBatchSettings()` | All symbologies disabled by default. |
| `enableSymbologies(symbologies)` | Enable multiple symbologies at once. |
| `enableSymbology(symbology, enabled)` | Enable or disable a single symbology. |
| `settingsForSymbology(symbology)` | Per-symbology settings (e.g. `activeSymbolCounts`). |

### BarcodeBatch members

| Member | Description |
|--------|-------------|
| `BarcodeBatch.forContext(context, settings)` | Async factory — always `await`. |
| `BarcodeBatch.recommendedCameraSettings` | Static property (not a method). |
| `barcodeBatch.setEnabled(enabled)` | Async — `await` before and after scanning windows. |
| `barcodeBatch.addListener(listener)` | Register an `IBarcodeBatchListener`. |
| `barcodeBatch.removeListener(listener)` | Unregister. Call during cleanup. |
| `barcodeBatch.applySettings(settings)` | Update settings at runtime (async). |

## Step 3 — Set up the camera

```typescript
const camera = Camera.pickBestGuess();
const cameraSettings = BarcodeBatch.recommendedCameraSettings; // static property
await camera.applySettings(cameraSettings);
await context.setFrameSource(camera);

// Turn the camera on.
await context.frameSource?.switchToDesiredState(FrameSourceState.On);
await barcodeBatch.setEnabled(true);
```

## Step 4 — Add BarcodeBatchBasicOverlay

`BarcodeBatchBasicOverlay` renders a highlight frame or dot over each tracked barcode. The overlay is added to the view via an async factory — there is no implicit overlay.

```typescript
import {
  BarcodeBatchBasicOverlay,
  BarcodeBatchBasicOverlayStyle,
} from "@scandit/web-datacapture-barcode";
import { Brush, Color } from "@scandit/web-datacapture-core";

// Style variant (recommended):
const overlay = await BarcodeBatchBasicOverlay.withBarcodeBatchForViewWithStyle(
  barcodeBatch,
  view,
  BarcodeBatchBasicOverlayStyle.Frame // or .Dot
);

// Optional: per-barcode brush listener.
// brushForTrackedBarcode is called whenever a new tracked barcode appears.
overlay.listener = {
  brushForTrackedBarcode: (_overlay, trackedBarcode) => {
    if (trackedBarcode.barcode.symbology === Symbology.EAN13UPCA) {
      return new Brush(Color.fromRGBA(0, 200, 0, 0.3), Color.fromHex("#00C800"), 2);
    }
    return new Brush(Color.fromRGBA(0, 100, 255, 0.3), Color.fromHex("#0064FF"), 2);
    // Return null to hide the highlight for this barcode.
  },

  didTapTrackedBarcode: (_overlay, trackedBarcode) => {
    console.log("Tapped:", trackedBarcode.barcode.data);
  },
};
```

### BarcodeBatchBasicOverlay members

| Member | Description |
|--------|-------------|
| `withBarcodeBatchForView(mode, view)` | Async factory without explicit style. |
| `withBarcodeBatchForViewWithStyle(mode, view, style)` | Async factory with explicit style. |
| `overlay.listener` | Set a `BarcodeBatchBasicOverlayListener`. |
| `overlay.brush` | **Read-only getter** — returns the current default brush. Use `setBrush(brush)` to change it. |
| `setBrush(brush)` | `Promise<void>` — set the default brush for all tracked barcodes (no listener). |
| `setBrushForTrackedBarcode(brush, trackedBarcode)` | `Promise<void>` — override brush for a specific barcode imperatively. |
| `clearTrackedBarcodeBrushes()` | `Promise<void>` — clear all per-barcode brush overrides. |
| `overlay.style` | Read-only — `Frame` or `Dot`. |
| `shouldShowScanAreaGuides()` | Getter method — returns `boolean`. Debug: show the active scan area. |
| `setShouldShowScanAreaGuides(enabled)` | `Promise<void>` — enable/disable scan area guide rendering. |

### IBarcodeBatchBasicOverlayListener callbacks

| Callback | Description |
|----------|-------------|
| `brushForTrackedBarcode(overlay, trackedBarcode)` | Return a `Brush` (or `null` to hide) for a newly tracked barcode. |
| `didTapTrackedBarcode(overlay, trackedBarcode)` | Called when the user taps a tracked barcode highlight. |

## Step 5 — Listen to BarcodeBatchSession

`IBarcodeBatchListener.didUpdateSession` is called after every frame where the tracked barcode state changes.

```typescript
barcodeBatch.addListener({
  didUpdateSession: (_barcodeBatch, session) => {
    // All currently tracked barcodes.
    for (const trackedBarcode of Object.values(session.trackedBarcodes)) {
      const { data, symbology } = trackedBarcode.barcode;
      console.log(`Tracking [${symbology}]: ${data}`);
    }

    // Newly appeared barcodes this frame.
    for (const trackedBarcode of session.addedTrackedBarcodes) {
      console.log("Added:", trackedBarcode.barcode.data);
    }

    // Barcodes that left the frame (identifiers as strings).
    for (const id of session.removedTrackedBarcodes) {
      // id is a string — convert to number when needed:
      const identifier = Number.parseInt(id, 10);
      console.log("Removed identifier:", identifier);
    }
  },
});
```

### BarcodeBatchSession properties

| Property | Type | Description |
|----------|------|-------------|
| `trackedBarcodes` | `Record<string, TrackedBarcode>` | All currently tracked barcodes. |
| `addedTrackedBarcodes` | `TrackedBarcode[]` | Barcodes newly tracked this frame. |
| `updatedTrackedBarcodes` | `TrackedBarcode[]` | Barcodes with updated location this frame. |
| `removedTrackedBarcodes` | `string[]` | Identifiers (as strings) of barcodes that were lost. |

### TrackedBarcode properties

| Property | Type | Description |
|----------|------|-------------|
| `barcode` | `Barcode` | The barcode associated with this track. |
| `identifier` | `number` | Unique identifier for this track. |
| `location` | `Quadrilateral` | Location in image-space (frame coordinates). |

## Step 6 — BarcodeBatchAdvancedOverlay: AR views from HTML elements

`BarcodeBatchAdvancedOverlay` lets you anchor a custom HTML element to each tracked barcode. Wrap the element with `TrackedBarcodeView.withHTMLElement()` — no subclassing required.

```typescript
import {
  BarcodeBatchAdvancedOverlay,
  TrackedBarcodeView,
} from "@scandit/web-datacapture-barcode";
import {
  Anchor,
  MeasureUnit,
  NumberWithUnit,
  PointWithUnit,
} from "@scandit/web-datacapture-core";

const advancedOverlay = await BarcodeBatchAdvancedOverlay.withBarcodeBatchForView(
  barcodeBatch,
  view
);

// Option A — listener-based (called per new tracked barcode):
// viewForTrackedBarcode must return Promise<TrackedBarcodeView | null>.
// TrackedBarcodeView.withHTMLElement() returns a Promise, so returning it directly is correct.
advancedOverlay.listener = {
  viewForTrackedBarcode: (_overlay, trackedBarcode) => {
    const el = document.createElement("div");
    el.textContent = trackedBarcode.barcode.data ?? "";
    el.style.cssText = "background:#2196F3;color:#fff;padding:4px 8px;border-radius:4px;font-size:12px;";
    // Scale by device pixel ratio for crisp rendering.
    return TrackedBarcodeView.withHTMLElement(el, { scale: 1 / window.devicePixelRatio });
  },
  anchorForTrackedBarcode: () => Anchor.TopCenter,
  offsetForTrackedBarcode: () =>
    new PointWithUnit(
      new NumberWithUnit(0, MeasureUnit.Fraction),
      new NumberWithUnit(-1, MeasureUnit.Fraction) // 100% of own height above the barcode
    ),
  didTapViewForTrackedBarcode: (_overlay, trackedBarcode) => {
    console.log("AR view tapped:", trackedBarcode.barcode.data);
  },
};
```

### Option B — setter-based (from didUpdateSession):

Cache views in a `Map` keyed by `TrackedBarcode.identifier`. Create a view only when a barcode first appears; do not recreate it every frame.

```typescript
// Cache Promise<TrackedBarcodeView> per barcode identifier (number).
const viewCache = new Map<number, Promise<TrackedBarcodeView>>();

barcodeBatch.addListener({
  didUpdateSession: (_barcodeBatch, session) => {
    // Clean up cache for barcodes that left the frame.
    // removedTrackedBarcodes are strings — convert to number to match Map keys.
    for (const id of session.removedTrackedBarcodes) {
      viewCache.delete(Number.parseInt(id, 10));
    }

    // Only create views for newly appeared barcodes.
    for (const trackedBarcode of session.addedTrackedBarcodes) {
      const el = document.createElement("div");
      el.textContent = trackedBarcode.barcode.data ?? "";
      el.style.cssText = "background:#2196F3;color:#fff;padding:4px 8px;border-radius:4px;";
      // withHTMLElement returns Promise<TrackedBarcodeView> — cache and pass directly.
      const trackedView = TrackedBarcodeView.withHTMLElement(el, { scale: 1 / window.devicePixelRatio });
      viewCache.set(trackedBarcode.identifier, trackedView);
      void advancedOverlay.setViewForTrackedBarcode(trackedView, trackedBarcode);
      // setAnchorForTrackedBarcode and setOffsetForTrackedBarcode are synchronous (return void).
      advancedOverlay.setAnchorForTrackedBarcode(Anchor.TopCenter, trackedBarcode);
      advancedOverlay.setOffsetForTrackedBarcode(
        new PointWithUnit(
          new NumberWithUnit(0, MeasureUnit.Fraction),
          new NumberWithUnit(-1, MeasureUnit.Fraction)
        ),
        trackedBarcode
      );
    }
  },
});
```

> The setter approach (B) takes priority over listener callbacks (A) for the same barcode. If you call `setViewForTrackedBarcode` for a barcode, `viewForTrackedBarcode` will not be called for that barcode.

### TrackedBarcodeView factories

| Factory | Description |
|---------|-------------|
| `TrackedBarcodeView.withHTMLElement(element, options)` | Returns `Promise<TrackedBarcodeView>`. Pass the Promise directly to `setViewForTrackedBarcode` or return it from `viewForTrackedBarcode`. |
| `TrackedBarcodeView.withBase64EncodedData(data, options)` | Returns `Promise<TrackedBarcodeView>`. Alternative for image-based AR views encoded as base64. |

`TrackedBarcodeViewOptions` fields: `scale?: number` (compensate for device pixel ratio), `size?: Size` (explicit pixel dimensions).

### BarcodeBatchAdvancedOverlay members

| Member | Description |
|--------|-------------|
| `withBarcodeBatchForView(mode, view)` | Async factory — always `await`. |
| `overlay.listener` | Set a `BarcodeBatchAdvancedOverlayListener`. |
| `setViewForTrackedBarcode(view, trackedBarcode)` | Set/replace the AR view. Accepts `Promise<TrackedBarcodeView \| null> \| null` — pass the Promise returned by `withHTMLElement` directly. Returns `Promise<void>`. |
| `setAnchorForTrackedBarcode(anchor, trackedBarcode)` | Override anchor imperatively. **Sync — returns `void`.** |
| `setOffsetForTrackedBarcode(offset, trackedBarcode)` | Override offset imperatively. **Sync — returns `void`.** |
| `clearTrackedBarcodeViews()` | Remove all AR views. **Sync — returns `void`.** |
| `overlay.shouldShowScanAreaGuides` | Read/write `boolean` property. Debug: show the active scan area. |

### BarcodeBatchAdvancedOverlayListener callbacks

| Callback | Description |
|----------|-------------|
| `viewForTrackedBarcode(overlay, trackedBarcode)` | Return `Promise<TrackedBarcodeView \| null>` — return the Promise from `TrackedBarcodeView.withHTMLElement()` directly. |
| `anchorForTrackedBarcode(overlay, trackedBarcode)` | Return an `Anchor`. Sync. |
| `offsetForTrackedBarcode(overlay, trackedBarcode)` | Return a `PointWithUnit` offset. Sync. |
| `didTapViewForTrackedBarcode(overlay, trackedBarcode)` | Called when the user taps an AR view. Sync. |

### Coordinate mapping (frame → view)

To position custom DOM elements based on barcode location, convert frame coordinates to view coordinates:

```typescript
const viewQuad = view.viewQuadrilateralForFrameQuadrilateral(trackedBarcode.location);
const width = Math.max(
  viewQuad.topRight.x - viewQuad.topLeft.x,
  viewQuad.bottomRight.x - viewQuad.bottomLeft.x,
);
// E.g., only show AR view when barcode occupies >20% of screen width:
if (width > window.innerWidth * 0.2) {
  await advancedOverlay.setViewForTrackedBarcode(trackedView, trackedBarcode);
}
```

## Step 7 — Lifecycle: enable/disable and cleanup

For a **freeze/resume** workflow (pause to inspect results, then continue), use `Standby` instead of `Off`. `Standby` keeps the camera warm and resumes faster — important when users toggle scanning frequently:

```typescript
// Freeze scanning (user reviews results):
await barcodeBatch.setEnabled(false);
await context.frameSource?.switchToDesiredState(FrameSourceState.Standby);

// Resume scanning:
await context.frameSource?.switchToDesiredState(FrameSourceState.On);
await barcodeBatch.setEnabled(true);
```

Use `FrameSourceState.Off` for cleanup on unmount (fully stops the camera):

```typescript
await barcodeBatch.setEnabled(false);
await context.frameSource?.switchToDesiredState(FrameSourceState.Off);
```

Hook into `visibilitychange` to handle tab switching:

```typescript
document.addEventListener("visibilitychange", async () => {
  if (document.hidden) {
    await barcodeBatch.setEnabled(false);
    await context.frameSource?.switchToDesiredState(FrameSourceState.Off);
  } else {
    await context.frameSource?.switchToDesiredState(FrameSourceState.On);
    await barcodeBatch.setEnabled(true);
  }
});
```

Cleanup when the scanning surface is unmounted:

```typescript
barcodeBatch.removeListener(listener);
await context.frameSource?.switchToDesiredState(FrameSourceState.Off);
view.detachFromElement();
```

## React integration

For React, initialize inside a `useEffect` and clean up in the returned function:

```tsx
import { useEffect, useRef } from "react";
import {
  Camera,
  DataCaptureContext,
  DataCaptureView,
  FrameSourceState,
} from "@scandit/web-datacapture-core";
import {
  BarcodeBatch,
  BarcodeBatchBasicOverlay,
  BarcodeBatchBasicOverlayStyle,
  BarcodeBatchSettings,
  barcodeCaptureLoader,
  Symbology,
} from "@scandit/web-datacapture-barcode";

export const MatrixScanComponent: React.FC = () => {
  const captureRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let barcodeBatch: BarcodeBatch | null = null;
    let view: DataCaptureView | null = null;

    const initialize = async () => {
      const context = await DataCaptureContext.forLicenseKey(
        "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
        {
          libraryLocation: new URL("library/engine/", document.baseURI).toString(),
          moduleLoaders: [barcodeCaptureLoader()],
        }
      );

      const settings = new BarcodeBatchSettings();
      settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.Code128]);

      barcodeBatch = await BarcodeBatch.forContext(context, settings);
      barcodeBatch.addListener({
        didUpdateSession: (_mode, session) => {
          for (const tracked of Object.values(session.trackedBarcodes)) {
            console.log("Tracking:", tracked.barcode.data);
          }
        },
      });

      const camera = Camera.pickBestGuess();
      await camera.applySettings(BarcodeBatch.recommendedCameraSettings);
      await context.setFrameSource(camera);

      view = await DataCaptureView.forContext(context);
      view.connectToElement(captureRef.current!);

      await BarcodeBatchBasicOverlay.withBarcodeBatchForViewWithStyle(
        barcodeBatch,
        view,
        BarcodeBatchBasicOverlayStyle.Frame
      );

      await context.frameSource?.switchToDesiredState(FrameSourceState.On);
      await barcodeBatch.setEnabled(true);
    };

    initialize().catch(console.error);

    return () => {
      barcodeBatch?.setEnabled(false).catch(console.error);
      DataCaptureContext.sharedInstance.frameSource
        ?.switchToDesiredState(FrameSourceState.Off)
        .catch(console.error);
      view?.detachFromElement();
    };
  }, []);

  return (
    <div
      ref={captureRef}
      style={{ position: "fixed", top: 0, left: 0, width: "100%", height: "100%" }}
    />
  );
};
```

## Key rules

1. **Await everything** — `DataCaptureContext.forLicenseKey`, `BarcodeBatch.forContext`, `barcodeBatch.setEnabled`, `DataCaptureView.forContext`, `view.setContext`, `BarcodeBatchBasicOverlay.withBarcodeBatchForView*`, `BarcodeBatchAdvancedOverlay.withBarcodeBatchForView`, `setViewForTrackedBarcode`, `camera.applySettings`, `setFrameSource`, `switchToDesiredState` are all async.
2. **But NOT these** — `setAnchorForTrackedBarcode`, `setOffsetForTrackedBarcode`, and `clearTrackedBarcodeViews()` on `BarcodeBatchAdvancedOverlay` are **synchronous** (return `void`). Do not use `await` or `void` with them.
3. **Multithreading is non-optional** — BarcodeBatch will not perform acceptably without COOP+COEP headers. Set them before anything else.
4. **Module loader** — use `barcodeCaptureLoader()`, not a separate `barcodeBatchLoader`.
5. **AR views return Promises** — `TrackedBarcodeView.withHTMLElement()` returns `Promise<TrackedBarcodeView>`. Pass the Promise directly to `setViewForTrackedBarcode` or return it from `viewForTrackedBarcode`. No subclassing needed.
6. **removedTrackedBarcodes are strings** — `session.removedTrackedBarcodes` returns `string[]`. Use `Number.parseInt(id, 10)` when comparing to `TrackedBarcode.identifier`.
7. **Mount point dimensions** — the element passed to `connectToElement()` must have non-zero width/height and a set `position`.
8. **Camera lifecycle** — turn the camera off with `FrameSourceState.Off` when scanning is not active. Hook `visibilitychange` to handle tab switching.
9. **recommendedCameraSettings** — it's a static property, not a method: `BarcodeBatch.recommendedCameraSettings`, not `BarcodeBatch.recommendedCameraSettings()`.
10. **TrackedBarcodeView scale** — use `{ scale: 1 / window.devicePixelRatio }` as options for crisp AR views on high-DPI screens.

## Common pitfalls

| Pitfall | Fix |
|---------|-----|
| Nothing tracks / very slow | COOP/COEP headers missing. BarcodeBatch requires multithreading. |
| Camera preview not visible | Container has zero size or no `position: fixed/absolute`. |
| `BarcodeBatch.forContext` not awaited | Always `await` — without it, `barcodeBatch` is a Promise, not a mode. |
| AR views not appearing | Advanced overlay not awaited, or `viewForTrackedBarcode` returns `undefined` instead of `null` (or a non-Promise value). |
| `setAnchorForTrackedBarcode` TypeScript error | Do not `await` it — it is synchronous (`void`). |
| AR view looks blurry on Retina | Pass `{ scale: 1 / window.devicePixelRatio }` to `TrackedBarcodeView.withHTMLElement`. |
| `removedTrackedBarcodes` ids don't match | Identifiers come back as `string[]`. Parse with `Number.parseInt(id, 10)`. |
| Duplicate scan events | Camera not paused. Call `setEnabled(false)` and/or `FrameSourceState.Off` when not scanning. |
| Overlay not rendering highlights | Basic overlay factory not awaited. |
| React StrictMode double-init | Wrap init in a guard (e.g. `if (DataCaptureContext.sharedInstance)`) or use a ref flag. |
