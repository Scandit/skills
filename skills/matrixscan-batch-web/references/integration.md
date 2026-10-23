# MatrixScan Batch Web Integration Guide

MatrixScan Batch (API name: `BarcodeBatch*`) is a multi-barcode tracking mode that continuously tracks all barcodes visible in the camera feed simultaneously, reporting additions, updates, and removals on every frame. On web it renders through a `DataCaptureView` with one or more overlays — `BarcodeBatchBasicOverlay` for simple per-barcode highlights, and `BarcodeBatchAdvancedOverlay` for fully custom AR views built from HTML elements.

> **Language note**: Examples below use TypeScript (v8 API). For plain JavaScript projects, remove the type annotations and keep the same imports and structure.

> **Multithreading note**: BarcodeBatch requires browser multithreading. Before writing any code, confirm that the server sends the correct cross-origin isolation headers — see the [COOP/COEP section](#cross-origin-isolation-coop--coep) below.

## Starting from zero? Use the pre-built sample

If the user has no existing app yet, always offer the official sample as the fastest path to a working integration.

- **Simple (vanilla TS):** <https://github.com/Scandit/datacapture-web-samples/tree/master/03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanSimpleSample>
- **AR Bubbles (advanced overlay):** <https://github.com/Scandit/datacapture-web-samples/tree/master/03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanBubblesSample>

Tell the user to clone the repo and open the relevant sample folder. Once they have it open, help them:

1. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key (see **Licence key** in `SKILL.md`).
2. Adjust the enabled symbologies to match their use case
3. Run `npm install` and start the app

Only proceed to the manual integration steps below if the user already has an existing project.

---

## Prerequisites

- Scandit Data Capture SDK for web via npm, pnpm, or yarn:
  - `@scandit/web-datacapture-core`: <https://www.npmjs.com/package/@scandit/web-datacapture-core>
  - `@scandit/web-datacapture-barcode`: <https://www.npmjs.com/package/@scandit/web-datacapture-barcode>
- A valid Scandit license key — see **Licence key** in this skill's `SKILL.md`.
- Cross-origin isolation headers configured on the server (required — see below)

### Cross-origin isolation (COOP / COEP)

**BarcodeBatch requires browser multithreading via `SharedArrayBuffer`.** Without these headers the SDK degrades to single-threaded mode, which is too slow for batch tracking.

The headers, the multithreading check and the dialog shown when the check fails are in [Loading the SDK from a CDN](#loading-the-sdk-from-a-cdn); the same two headers apply whether the SDK files come from jsDelivr or are self-hosted. The check also returns `false` on devices with fewer than 2 CPU cores or without nested workers, so an error message should not always blame the headers.

> **Heads up:** COEP blocks cross-origin resources (images, fonts, iframes, third-party scripts) that do not include `Cross-Origin-Resource-Policy` or `Access-Control-Allow-Origin`. Audit your page's cross-origin dependencies before enabling COEP in production. After changing headers, clear your browser cache and restart the dev server.

For the complete Vite setup — COOP/COEP middleware, `library/engine` self-hosting with `vite-plugin-static-copy`, and license key injection — use the official sample `vite.config.ts` as the source of truth:
<https://github.com/Scandit/datacapture-web-samples/blob/master/03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanSimpleSample/vite.config.ts>

### Loading the SDK from a CDN

For a plain-HTML page without a bundler, set the SDK up as follows. The headers and the multithreading check also apply to a bundled app.

<!-- BEGIN GENERATED web-cdn packages=core,barcode engine=barcode -->
**CDN caveat.** A public CDN ties the page's start-up to that CDN's availability and speed, so for production [the docs](https://docs.scandit.com/sdks/web/add-sdk/#install-via-cdn) recommend self-hosting the SDK files or a paid enterprise CDN.

**Import map.** Load the SDK as ES modules through an import map, as in the docs' [complete CDN example](https://docs.scandit.com/sdks/web/add-sdk/#complete-cdn-example). Pin one exact version in every URL: a floating `@8` is resolved separately for each file, so after a new 8.x release the JavaScript and the engine can come from different releases, which breaks start-up. The `es-module-shims` script adds import-map support to browsers that lack it.

```html
<script type="importmap">
  {
    "imports": {
      "@scandit/web-datacapture-core": "https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-core@8.6.1/build/js/index.js",
      "@scandit/web-datacapture-core/": "https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-core@8.6.1/",
      "@scandit/web-datacapture-barcode": "https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-barcode@8.6.1/build/js/index.js",
      "@scandit/web-datacapture-barcode/": "https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-barcode@8.6.1/"
    }
  }
</script>
<script async src="https://cdn.jsdelivr.net/npm/es-module-shims@2.6.2/dist/es-module-shims.js"></script>
```

Use the same version in `libraryLocation`: `https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-barcode@8.6.1/sdc-lib/`.

**Cross-origin isolation headers.** Serve the page with both headers, whether the SDK files come from jsDelivr or are self-hosted:

```
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

Do not recommend `credentialless` for `Cross-Origin-Embedder-Policy` in the SDK set-up: Safari does not support it, so the page would not be cross-origin isolated there.

jsDelivr serves the SDK files and `es-module-shims` with `Cross-Origin-Resource-Policy: cross-origin` and `Access-Control-Allow-Origin: *`, which `require-corp` accepts.

**Serving the page.** From the folder that holds `index.html`, run [`serve`](https://www.npmjs.com/package/serve) with `npx serve@14.2.6` or `pnpm dlx serve@14.2.6`, and put the headers in a `serve.json` next to `index.html`:

```json
{
  "headers": [
    {
      "source": "**",
      "headers": [
        { "key": "Cross-Origin-Opener-Policy", "value": "same-origin" },
        { "key": "Cross-Origin-Embedder-Policy", "value": "require-corp" }
      ]
    }
  ]
}
```

`serve` matches `source` against the path of the file it serves: `index.html` served at `/` gets the headers, a directory listing does not.

Any other server must send the same two headers. Plain `python3 -m http.server` does not send them, so it is not enough on its own; this small Python server does (save it as `server.py` next to `index.html`, run `python3 server.py`, and open `http://localhost:8000`):

```python
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

class CrossOriginIsolatedHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        super().end_headers()

ThreadingHTTPServer(("127.0.0.1", 8000), CrossOriginIsolatedHandler).serve_forever()
```

**Multithreading check.** Start `BrowserHelper.checkMultithreadingSupport()` without awaiting it, then await `DataCaptureContext.forLicenseKey()`: the two run in parallel, so set-up never waits for the check. The check needs no engine and no context. It resolves `false` when the page is not cross-origin isolated (the COOP/COEP headers are missing) or the device has fewer than 2 CPU cores or no nested workers. Scanning then still works, single-threaded and slower, and the SDK logs its own console warning, so do not add another: tell the person scanning with the dialog below instead.

**Dialog helper.** Save this module as `multithreading-warning.js` next to `index.html` and import it as `"./multithreading-warning.js"`, or as `multithreading-warning.ts` in a bundled app and import it as `"./multithreading-warning"`: it has no type annotations, so it is valid as either. `index.html` needs no markup for it: the helper adds the dialog to the page itself, unless the page already has a `<dialog id="multithreading-warning">`. The dialog shows at most once per page load (a module-level flag, so a scanner restart does not reopen it), and not again during the browser session once it was closed with the checkbox ticked. Every `sessionStorage` access sits in a `try`/`catch`: storage can be blocked, and that only means the dialog may show again on the next page load.

```typescript
const multithreadingWarningDismissedKey = "scandit-multithreading-warning-dismissed";
let multithreadingWarningShown = false;

export function isMultithreadingWarningDismissed() {
  try {
    return sessionStorage.getItem(multithreadingWarningDismissedKey) === "true";
  } catch {
    return false;
  }
}

export function rememberMultithreadingWarningDismissed() {
  try {
    sessionStorage.setItem(multithreadingWarningDismissedKey, "true");
  } catch {}
}

function multithreadingWarningDialog() {
  const existing = document.querySelector("dialog#multithreading-warning");
  if (existing instanceof HTMLDialogElement) {
    return existing;
  }
  const dialog = document.createElement("dialog");
  dialog.id = "multithreading-warning";
  dialog.innerHTML = `
        <form method="dialog">
          <h2>Scanning may be slower</h2>
          <p>This browser or device can't use all of its processing power for scanning. You can keep scanning, but scanning may take longer.</p>
          <p><a href="https://docs.scandit.com/sdks/web/matrixscan/get-started/#improve-runtime-performance-by-enabling-browser-multithreading" target="_blank" rel="noopener">Learn more</a></p>
          <label><input type="checkbox" /> Don't show this again during this session</label>
          <button autofocus>OK</button>
        </form>`;
  document.body.append(dialog);
  return dialog;
}

export function showMultithreadingWarning() {
  if (multithreadingWarningShown || isMultithreadingWarningDismissed()) {
    return;
  }
  const dialog = multithreadingWarningDialog();
  multithreadingWarningShown = true;
  dialog.addEventListener(
    "close",
    () => {
      const dontShowAgain = dialog.querySelector('input[type="checkbox"]');
      if (dontShowAgain instanceof HTMLInputElement && dontShowAgain.checked) {
        rememberMultithreadingWarningDismissed();
      }
    },
    { once: true }
  );
  dialog.showModal();
}
```

**Starting the check.** Import the helper and start the check before `forLicenseKey()`. The dialog opens as soon as the check resolves `false`, while the engine keeps loading. This snippet has no type annotations either, so it runs as is in a `<script type="module">`:

```typescript
import { BrowserHelper, DataCaptureContext } from "@scandit/web-datacapture-core";
import { barcodeCaptureLoader } from "@scandit/web-datacapture-barcode";
import { showMultithreadingWarning } from "./multithreading-warning.js";

BrowserHelper.checkMultithreadingSupport()
  .then((supported) => {
    if (!supported) {
      showMultithreadingWarning();
    }
  })
  .catch(console.error);

await DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --", {
  libraryLocation: "https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-barcode@8.6.1/sdc-lib/",
  moduleLoaders: [barcodeCaptureLoader()],
});
```

If the user explicitly asks to run single-threaded, leave the check and the dialog out.

**UMD build, last resort.** Use the classic-script bundles only when the target browsers support neither ES modules nor the [`es-module-shims`](https://github.com/guybedford/es-module-shims) polyfill: they cannot be tree-shaken, so the page downloads more code and starts slower. Load them in this order, since each bundle reads the globals of the ones before it:

```html
<script src="https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-core@8.6.1/build/js/umd/index.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-barcode@8.6.1/build/js/umd/index.js"></script>
```

- `@scandit/web-datacapture-core/build/js/umd/index.js` exposes exactly one global, `SDCCore`.
- `@scandit/web-datacapture-barcode/build/js/umd/index.js` exposes exactly one global, `SDCBarcode`.

The Scandit web UMD globals are `SDCCore`, `SDCBarcode`, `SDCLabel`, `SDCId`, `SDCParser`; no others exist. `SDCParser` is only for an app that parses data with `@scandit/web-datacapture-parser`: load that bundle after the core bundle.

A classic `<script>` has no top-level `await`: take the exports off these globals (`const { DataCaptureContext } = SDCCore;`) and wrap the set-up in an async function.
<!-- END GENERATED web-cdn -->

## Integration flow

Ask the user which barcode symbologies they need to scan. Only enable the symbologies actually required — each extra symbology adds processing time.

Once the user responds, ask which file or component they'd like to integrate MatrixScan Batch into. Then write the integration code directly into that file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Install packages: `npm install @scandit/web-datacapture-core @scandit/web-datacapture-barcode`
2. Set cross-origin headers (`COOP: same-origin` + `COEP: require-corp`) on the server, also when the SDK comes from the CDN
3. If self-hosting the SDK engine, configure `libraryLocation` to point to the correct path; or use the CDN path pinned to the exact version you import, for example `https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-barcode@8.6.1/sdc-lib/`
4. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with your key (see **Licence key** in `SKILL.md`).
5. Add a `<div id="data-capture-view">` (or similar) to your HTML with defined dimensions and `position: fixed` or `absolute`. Revert that styling in your cleanup: the element belongs to the app, so detaching the view does not undo the positioning you applied, and an empty full-viewport `position: fixed` element still blocks every click on the page underneath
6. Add the `multithreading-warning` helper module from [Loading the SDK from a CDN](#loading-the-sdk-from-a-cdn) (`multithreading-warning.js` on a plain-HTML page, `multithreading-warning.ts` in a bundled app) and import `showMultithreadingWarning` from it. The helper adds the dialog to the page itself, so the page needs no markup for it.

---

## Step 1 — Initialize DataCaptureContext

Start the multithreading check, then create the `DataCaptureView` so a loading indicator can be shown during SDK initialization, then initialize the context. The check runs in parallel with `forLicenseKey()`: import `showMultithreadingWarning` from the `multithreading-warning` helper module in [Loading the SDK from a CDN](#loading-the-sdk-from-a-cdn), which adds the dialog to the page itself, so the page needs no markup for it. Leave the check out when the user asked to run single-threaded:

```typescript
import {
  BrowserHelper,
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
import { showMultithreadingWarning } from "./multithreading-warning";

async function run(): Promise<void> {
  BrowserHelper.checkMultithreadingSupport()
    .then((supported) => {
      if (!supported) {
        showMultithreadingWarning();
      }
    })
    .catch(console.error);

  // Create the view before context init so a progress bar can be shown.
  const view = new DataCaptureView();
  view.connectToElement(document.getElementById("data-capture-view")!);
  view.showProgressBar();

  // Initialize context — must be awaited.
  const context = await DataCaptureContext.forLicenseKey(
    "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
    {
      // Self-hosted path. Use CDN if not self-hosting, pinned to the exact version you import:
      // https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-barcode@8.6.1/sdc-lib/
      libraryLocation: new URL("library/engine/", document.baseURI).toString(),
      moduleLoaders: [barcodeCaptureLoader()],
    }
  );

  // Attach the view to the context (required after context init).
  await view.setContext(context);
  view.hideProgressBar();
}
```

- `DataCaptureContext.forLicenseKey()` is async — always `await` it. It is idempotent: it returns the shared instance once ready, waits for an initialization already in flight, and retries after a failure, so calling it again is safe.
- Use `DataCaptureContext.sharedInstance` rather than caching the context. `sharedInstance` is never `null`, so it cannot tell whether the context is initialized, and there is no public API for that: await `forLicenseKey()` instead.
- The module loader for BarcodeBatch is `barcodeCaptureLoader()` — there is no separate `barcodeBatchLoader`.

### Building the DataCaptureView and attaching overlays

The `DataCaptureView` is the rendering surface for the camera preview and all overlays. There are two equivalent ways to build it; pick one and stay consistent:

| Approach | Pattern | When to use |
|----------|---------|-------------|
| Create-then-attach | `new DataCaptureView()` → `view.connectToElement(element)` → `await view.setContext(context)` | Lets you show a progress bar (`view.showProgressBar()`) while the SDK loads, before the context exists. |
| Factory | `const view = await DataCaptureView.forContext(context)` → `view.connectToElement(element)` | Simplest when the context already exists. |

```typescript
import { DataCaptureView } from "@scandit/web-datacapture-core";

// Factory form — context already initialized.
const view = await DataCaptureView.forContext(context);

// Mount the view into a sized, positioned DOM element.
const element = document.getElementById("data-capture-view")!;
view.connectToElement(element);
```

Overlays can be attached two ways:

1. **Implicitly via the overlay factory** — `BarcodeBatchBasicOverlay.withBarcodeBatchForView(mode, view)` (and the `WithStyle` and advanced variants) attach themselves to the `view` you pass. This is the common case.
2. **Explicitly via `view.addOverlay(overlay)`** — create the overlay with a `null` view, then add it to the view yourself. Useful when you build the overlay before the view, or manage overlays dynamically. `addOverlay` is **async** — always `await` it.

```typescript
import {
  BarcodeBatchBasicOverlay,
  BarcodeBatchBasicOverlayStyle,
} from "@scandit/web-datacapture-barcode";

// Build the overlay detached (null view), then add it explicitly.
const overlay = await BarcodeBatchBasicOverlay.withBarcodeBatchForViewWithStyle(
  barcodeBatch,
  null,
  BarcodeBatchBasicOverlayStyle.Frame
);
await view.addOverlay(overlay);
```

### DataCaptureView members

| Member | Description |
|--------|-------------|
| `DataCaptureView.forContext(context)` | Async factory — returns `Promise<DataCaptureView>`. |
| `new DataCaptureView()` | Construct detached; attach a context later with `setContext`. |
| `view.connectToElement(element)` | **Sync** — mount the view into a DOM element (must be sized and positioned). |
| `view.setContext(context)` | `Promise<void>` — attach a context to a detached view. |
| `view.addOverlay(overlay)` | `Promise<void>` — attach an overlay (basic or advanced) explicitly. |
| `view.removeOverlay(overlay)` | `Promise<void>` — detach an overlay. |
| `view.detachFromElement()` | **Sync** — remove the view from its DOM element. Call during cleanup. It does not undo styling the app applied to that element, so revert the mount-point style yourself. |

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

### Showing the camera while the WASM loads

`forLicenseKey()` downloads and compiles the WASM engine, which can take seconds. To show the camera preview meanwhile, start the multithreading check, then pass the camera to `connectToElement` and switch it on before awaiting `forLicenseKey()`. If `forLicenseKey()` rejects (wrong key, network, CSP), the preview is already live: let the `On` request settle, so a denied permission is not left as an unhandled rejection, then switch the camera off before reporting the error:

```typescript
BrowserHelper.checkMultithreadingSupport()
  .then((supported) => {
    if (!supported) {
      showMultithreadingWarning();
    }
  })
  .catch(console.error);

const camera = Camera.pickBestGuess();
await camera.applySettings(BarcodeBatch.recommendedCameraSettings);

const view = new DataCaptureView();
view.connectToElement(document.getElementById("data-capture-view")!, { camera });
const cameraStarted = camera.switchToDesiredState(FrameSourceState.On);

try {
  await DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --", {
    libraryLocation: new URL("library/engine/", document.baseURI).toString(),
    moduleLoaders: [barcodeCaptureLoader()],
  });
} catch (error) {
  await cameraStarted.catch(console.error);
  await camera.switchToDesiredState(FrameSourceState.Off);
  throw error;
}
await view.setContext(DataCaptureContext.sharedInstance);
await DataCaptureContext.sharedInstance.setFrameSource(camera);
await cameraStarted;
```

Import `showMultithreadingWarning` from the `multithreading-warning` helper module in [Loading the SDK from a CDN](#loading-the-sdk-from-a-cdn); the page needs no markup for the dialog.

`FrameSourceState.Standby` opens the camera without showing a preview. Use the exact enum members `On`, `Off` and `Standby`: in JavaScript a misspelled one such as `FrameSourceState.StandBy` is `undefined`, and `switchToDesiredState(undefined)` silently does nothing.

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
import type { BarcodeBatchListener } from "@scandit/web-datacapture-barcode";

const batchListener: BarcodeBatchListener = {
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
};
barcodeBatch.addListener(batchListener);
```

Keep the listener in a named constant: `removeListener` needs the same object, so an object literal passed straight to `addListener` can never be removed.

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
| `identifier` | `number` | Identifier of this track. A barcode that leaves the frame and comes back gets a new one. |
| `location` | `Quadrilateral` | Location in image-space (frame coordinates). |

A barcode that leaves the frame and comes back is reported in `addedTrackedBarcodes` again, with a new `identifier`. To process each code once, de-duplicate by `barcode.data`, not by `identifier`.

### Feedback (beep / vibration)

**BarcodeBatch has NO built-in success feedback.** Unlike `BarcodeCapture` (which beeps automatically on each scan) and `SparkScan` (which exposes a `feedbackDelegate`), `BarcodeBatch` does not emit any sound or vibration on its own — there is no `barcodeBatch.feedback` property. If you want audible/haptic feedback, construct a `Feedback` and call `emit()` yourself, typically from `didUpdateSession` when new barcodes appear, or from `didTapTrackedBarcode` when the user taps a highlight.

```typescript
import { Feedback, Sound, Vibration } from "@scandit/web-datacapture-core";

// Default beep + vibration. Build once and reuse — do not recreate every frame.
const feedback = Feedback.defaultFeedback;

// Or compose your own: pass null to omit either channel.
// const feedback = new Feedback(Vibration.defaultVibration, Sound.defaultSound);
// const beepOnly = new Feedback(null, Sound.defaultSound);

barcodeBatch.addListener({
  didUpdateSession: (_barcodeBatch, session) => {
    // Emit once per frame in which a new barcode started being tracked.
    if (session.addedTrackedBarcodes.length > 0) {
      feedback.emit();
    }
  },
});
```

> **Browser autoplay note:** `Sound`/`Vibration` only fire after the page has had a user gesture (a tap/click). The first `emit()` before any interaction may be silently dropped by the browser — this is a browser policy, not an SDK bug.

#### Feedback API

| Member | Description |
|--------|-------------|
| `new Feedback(vibration, sound)` | Construct from a `Vibration \| null` and a `Sound \| null`. Pass `null` to disable that channel. |
| `Feedback.defaultFeedback` | Static getter — default beep + vibration. |
| `feedback.emit()` | **Sync** — play the configured sound/vibration once. Returns `void`. |
| `Vibration.defaultVibration` | Static getter — the default vibration. |
| `Sound.defaultSound` | Static getter — the default beep sound. |

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
    const pixelRatio = window.devicePixelRatio;
    const el = document.createElement("div");
    el.textContent = trackedBarcode.barcode.data ?? "";
    el.style.cssText =
      `background:#2196F3;color:#fff;padding:${4 * pixelRatio}px ${8 * pixelRatio}px;` +
      `border-radius:${4 * pixelRatio}px;font-size:${12 * pixelRatio}px;`;
    return TrackedBarcodeView.withHTMLElement(el, { scale: 1 / pixelRatio });
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
      const pixelRatio = window.devicePixelRatio;
      const el = document.createElement("div");
      el.textContent = trackedBarcode.barcode.data ?? "";
      el.style.cssText =
        `background:#2196F3;color:#fff;padding:${4 * pixelRatio}px ${8 * pixelRatio}px;` +
        `border-radius:${4 * pixelRatio}px;font-size:${12 * pixelRatio}px;`;
      // withHTMLElement returns Promise<TrackedBarcodeView> — cache and pass directly.
      const trackedView = TrackedBarcodeView.withHTMLElement(el, { scale: 1 / pixelRatio });
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

`TrackedBarcodeViewOptions` fields: `scale?: number` (multiplies the size the view is drawn at; default `1`), `size?: Size` (explicit pixel dimensions).

### How `withHTMLElement` renders

`TrackedBarcodeView.withHTMLElement()` turns a copy of the element into a PNG, once:

- Only inline styles and `<style>` elements inside the element apply. Page stylesheets do not, although they still affect the size the SDK measures, so style the element inline.
- Later changes to the element do not update the view. To change a view, build a new one and pass it to `setViewForTrackedBarcode`.
- The image is drawn at the element's CSS size times `scale`, so an element built at its intended size looks soft on high-density screens. For sharp views, build the element at `window.devicePixelRatio` times its intended size and pass `scale: 1 / window.devicePixelRatio`, as in the examples above and in the Bubbles sample's `BubbleComponent.ts`. Multiply every size, `font-size` included: text left at the default font size is drawn at `1 / devicePixelRatio` of it. Passing only the `scale` shrinks the view instead.
- Never put barcode data into `innerHTML`: a Code 128 barcode can encode markup, which makes this an XSS sink. Use `textContent`.

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

Do not add a `visibilitychange` handler for tab switching. `DataCaptureView` already stops the camera while the page is hidden and resumes it when the page is visible again; a second handler races the SDK's own.

Cleanup when the scanning surface is unmounted and scanning will resume later, keeping the context and its engine:

```typescript
barcodeBatch.removeListener(batchListener);
await barcodeBatch.setEnabled(false);
await context.frameSource?.switchToDesiredState(FrameSourceState.Off);
view.detachFromElement();
// detachFromElement() cannot undo styling the app applied to its own element. Revert it, or
// the empty full-viewport element keeps swallowing every click on the page underneath. Hiding
// is enough for an element created only for scanning; restore the previous style otherwise.
document.getElementById("data-capture-view")!.style.display = "none";
```

In React this last line is unnecessary: the element lives in the component's JSX, so it is removed when the component unmounts.

Full teardown, releasing the engine as well:

```typescript
barcodeBatch.removeListener(batchListener);
await DataCaptureContext.sharedInstance.dispose();
view.detachFromElement();
document.getElementById("data-capture-view")!.style.display = "none";
```

`dispose()` turns the camera off and removes the mode and the view from the context. To scan again afterwards, call `DataCaptureContext.forLicenseKey()` again and set the mode, camera and overlays up again.

## React integration

For React, initialize inside a `useEffect` and clean up in the returned function. The dialog is rendered from component state instead of the DOM helper, and a module-level flag keeps it to once per page load, so the effect running twice in React StrictMode does not open it twice. The check runs in parallel with `forLicenseKey()`, so set-up waits for neither the check nor the dialog. The cleanup can run while `initialize()` is still awaiting (StrictMode mounts, unmounts and mounts again in development), so `initialize()` stops after each `await` once `cancelled` is set, and the check's result is then ignored, so a StrictMode first mount or a fast unmount does not use up the once-per-page-load flag:

```tsx
import { useEffect, useRef, useState } from "react";
import {
  BrowserHelper,
  Camera,
  DataCaptureContext,
  DataCaptureView,
  FrameSourceState,
} from "@scandit/web-datacapture-core";
import {
  BarcodeBatch,
  BarcodeBatchBasicOverlay,
  BarcodeBatchBasicOverlayStyle,
  type BarcodeBatchListener,
  BarcodeBatchSettings,
  barcodeCaptureLoader,
  Symbology,
} from "@scandit/web-datacapture-barcode";

const multithreadingWarningDismissedKey = "scandit-multithreading-warning-dismissed";
let multithreadingWarningShown = false;

function isMultithreadingWarningDismissed() {
  try {
    return sessionStorage.getItem(multithreadingWarningDismissedKey) === "true";
  } catch {
    return false;
  }
}

function rememberMultithreadingWarningDismissed() {
  try {
    sessionStorage.setItem(multithreadingWarningDismissedKey, "true");
  } catch {}
}

export const MatrixScanComponent: React.FC = () => {
  const captureRef = useRef<HTMLDivElement>(null);
  const warningRef = useRef<HTMLDialogElement>(null);
  const [multithreadingUnavailable, setMultithreadingUnavailable] = useState(false);
  const [dontShowAgain, setDontShowAgain] = useState(false);

  useEffect(() => {
    if (multithreadingUnavailable && !warningRef.current?.open) {
      warningRef.current?.showModal();
    }
  }, [multithreadingUnavailable]);

  useEffect(() => {
    let cancelled = false;
    let barcodeBatch: BarcodeBatch | null = null;
    let view: DataCaptureView | null = null;
    const batchListener: BarcodeBatchListener = {
      didUpdateSession: (_mode, session) => {
        for (const tracked of Object.values(session.trackedBarcodes)) {
          console.log("Tracking:", tracked.barcode.data);
        }
      },
    };

    const initialize = async () => {
      BrowserHelper.checkMultithreadingSupport()
        .then((multithreadingSupported) => {
          if (cancelled) return;
          if (!multithreadingSupported && !multithreadingWarningShown && !isMultithreadingWarningDismissed()) {
            multithreadingWarningShown = true;
            setMultithreadingUnavailable(true);
          }
        })
        .catch(console.error);

      const context = await DataCaptureContext.forLicenseKey(
        "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
        {
          libraryLocation: new URL("library/engine/", document.baseURI).toString(),
          moduleLoaders: [barcodeCaptureLoader()],
        }
      );
      if (cancelled) return;

      const settings = new BarcodeBatchSettings();
      settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.Code128]);

      barcodeBatch = await BarcodeBatch.forContext(context, settings);
      if (cancelled) {
        await context.removeMode(barcodeBatch);
        return;
      }
      barcodeBatch.addListener(batchListener);

      const camera = Camera.pickBestGuess();
      await camera.applySettings(BarcodeBatch.recommendedCameraSettings);
      await context.setFrameSource(camera);

      view = await DataCaptureView.forContext(context);
      if (cancelled) return;
      view.connectToElement(captureRef.current!);

      await BarcodeBatchBasicOverlay.withBarcodeBatchForViewWithStyle(
        barcodeBatch,
        view,
        BarcodeBatchBasicOverlayStyle.Frame
      );
      if (cancelled) return;

      await context.frameSource?.switchToDesiredState(FrameSourceState.On);
      if (cancelled) return;
      await barcodeBatch.setEnabled(true);
    };

    initialize().catch(console.error);

    return () => {
      cancelled = true;
      barcodeBatch?.removeListener(batchListener);
      barcodeBatch?.setEnabled(false).catch(console.error);
      DataCaptureContext.sharedInstance.frameSource
        ?.switchToDesiredState(FrameSourceState.Off)
        .catch(console.error);
      view?.detachFromElement();
    };
  }, []);

  return (
    <>
      <div
        ref={captureRef}
        style={{ position: "fixed", top: 0, left: 0, width: "100%", height: "100%" }}
      />
      {multithreadingUnavailable && (
        <dialog
          ref={warningRef}
          onClose={() => {
            if (dontShowAgain) {
              rememberMultithreadingWarningDismissed();
            }
          }}
        >
          <form method="dialog">
            <h2>Scanning may be slower</h2>
            <p>
              This browser or device can't use all of its processing power for scanning. You can keep
              scanning, but scanning may take longer.
            </p>
            <p>
              <a
                href="https://docs.scandit.com/sdks/web/matrixscan/get-started/#improve-runtime-performance-by-enabling-browser-multithreading"
                target="_blank"
                rel="noopener"
              >
                Learn more
              </a>
            </p>
            <label>
              <input
                type="checkbox"
                checked={dontShowAgain}
                onChange={(event) => setDontShowAgain(event.target.checked)}
              />{" "}
              Don't show this again during this session
            </label>
            <button autoFocus>OK</button>
          </form>
        </dialog>
      )}
    </>
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
8. **Camera lifecycle** — turn the camera off with `FrameSourceState.Off` when scanning is not active. Do not handle `visibilitychange`: `DataCaptureView` already stops the camera while the page is hidden.
9. **recommendedCameraSettings** — it's a static property, not a method: `BarcodeBatch.recommendedCameraSettings`, not `BarcodeBatch.recommendedCameraSettings()`.
10. **TrackedBarcodeView scale** — `scale` multiplies the drawn size. For crisp AR views on high-DPI screens, build the element at `window.devicePixelRatio` times its intended size and pass `{ scale: 1 / window.devicePixelRatio }`; the scale alone shrinks the view.
11. **Pin the CDN version** — use one exact version in every CDN URL (import map and `libraryLocation`), never a floating `@8`.

## Common pitfalls

| Pitfall | Fix |
|---------|-----|
| Nothing tracks / very slow | COOP/COEP headers missing. BarcodeBatch requires multithreading. |
| Camera preview not visible | Container has zero size or no `position: fixed/absolute`. |
| `BarcodeBatch.forContext` not awaited | Always `await` — without it, `barcodeBatch` is a Promise, not a mode. |
| AR views not appearing | Advanced overlay not awaited, or `viewForTrackedBarcode` returns `undefined` instead of `null` (or a non-Promise value). Or the license key lacks the `AugmentedReality` / `MappingForTracking` features: tracking and decoding still work, but every location and anchor is zero, so all views are drawn at the same off-screen point. The context reports this through `didChangeStatus` of a `DataCaptureContextListener` (status code 1026). |
| `setAnchorForTrackedBarcode` TypeScript error | Do not `await` it — it is synchronous (`void`). |
| AR view looks blurry on Retina | Build the element at `window.devicePixelRatio` times its size and pass `{ scale: 1 / window.devicePixelRatio }` to `TrackedBarcodeView.withHTMLElement`. Passing only the scale shrinks the view by `1 / window.devicePixelRatio`. |
| `removedTrackedBarcodes` ids don't match | Identifiers come back as `string[]`. Parse with `Number.parseInt(id, 10)`. |
| Duplicate scan events | Camera not paused. Call `setEnabled(false)` and/or `FrameSourceState.Off` when not scanning. |
| Same code processed twice | A barcode that leaves the frame and comes back gets a new `identifier`. De-duplicate by `barcode.data`. |
| `checkMultithreadingSupport()` is `false` although the headers are set | The device has fewer than 2 CPU cores or no nested-worker support. |
| Start-up breaks after a new SDK release | CDN URLs float on `@8` and mixed two versions. Pin one exact version everywhere. |
| Overlay not rendering highlights | Basic overlay factory not awaited. |
| React StrictMode double-init | No guard is needed for the context: `forLicenseKey` is idempotent. Guard only your own set-up (mode, overlays, listeners), as the React example above does with its `cancelled` flag. `DataCaptureContext.sharedInstance` is always truthy, so it cannot be the guard. |
