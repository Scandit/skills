# SparkScan Web Integration Guide

SparkScan is a pre-built scanning UI for high-volume single-scanning workflows.
It overlays a trigger button on top of any screen so users can scan without leaving their workflow.

## Starting from zero? Use the pre-built sample

If the user has no existing app yet, always offer the official sample as the fastest path to a working integration — it already has the correct project structure, dependencies, and best practices in place.

Ask whether they are using React or plain web (TypeScript/JavaScript), then point them to the right sample:

- **Vanilla JS / TypeScript:** <https://github.com/Scandit/datacapture-web-samples/tree/master/01_Single_Scanning_Samples/01_Barcode_Scanning_with_Pre-built_UI/ListBuildingSample>
- **React:** <https://github.com/Scandit/datacapture-web-samples/tree/master/05_Framework_Integration_Samples/SparkScanReactSample>

Tell the user to clone the repo and open the relevant sample folder. Once they have it open, help them:

1. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key (see **Licence key** in `SKILL.md`).
2. Adjust the enabled symbologies to match their use case (remind them to only enable what they need — fewer symbologies means better performance and accuracy)
3. Run `npm install` (or their package manager of choice) and start the app

Only proceed to the manual integration steps below if the user already has an existing project they need to add SparkScan to.

---

## Adding SparkScan to an existing project

### Prerequisites

- Scandit Data Capture SDK for web — add via npm, pnpm or yarn:
  - `@scandit/web-datacapture-core`: <https://www.npmjs.com/package/@scandit/web-datacapture-core>
  - `@scandit/web-datacapture-barcode`: <https://www.npmjs.com/package/@scandit/web-datacapture-barcode>
  - A valid Scandit license key — see **Licence key** in this skill's `SKILL.md`.

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask which file or component they'd like to integrate SparkScan into. Then write the integration code directly into that file — do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**

1. Add `@scandit/web-datacapture-core` and `@scandit/web-datacapture-barcode` via your package manager: <https://www.npmjs.com/package/@scandit/web-datacapture-core> <https://www.npmjs.com/package/@scandit/web-datacapture-barcode>
2. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key (see **Licence key** in `SKILL.md`).
3. If the SDK comes from the CDN, pin one exact version in every URL (see [Loading the SDK from a CDN](#loading-the-sdk-from-a-cdn)).
4. Serve the page with `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp`, also when the SDK comes from the CDN (see [Loading the SDK from a CDN](#loading-the-sdk-from-a-cdn)).
5. Add the `multithreading-warning` helper module from [Loading the SDK from a CDN](#loading-the-sdk-from-a-cdn) (`multithreading-warning.js` on a plain-HTML page, `multithreading-warning.ts` in a bundled app) and import `showMultithreadingWarning` from it. The helper adds the dialog to the page itself, so the page needs no markup for it.

The code example below is a basic TypeScript v8 implementation. It starts the multithreading check in parallel with `forLicenseKey()`: import `showMultithreadingWarning` from the `multithreading-warning` helper module in [Loading the SDK from a CDN](#loading-the-sdk-from-a-cdn), which adds the dialog to the page itself, so the page needs no markup for it.
If the user is using React, use the React get-started guide and SparkScanReactSample instead (see References).

> **Mount point requirement:** The SparkScan view needs a container with a resolved, non-zero width and height. If the container has zero or unresolved dimensions, the SparkScan UI will not display. The container's `position` does not matter to SparkScan itself — `<spark-scan-view>` sets `position: relative` on itself internally (that's what its trigger button and mini preview actually position against), independent of whatever `position` its parent has. A plain, normal-flow (`position: static`, i.e. no `position` at all) block-level container with a real height works fine; you don't need `position: fixed`/`absolute`/`relative` on the container unless you specifically want it to float over the rest of the page (see below) rather than take up its own space in your layout. The container also does not have to cover the full viewport — SparkScan sizes itself from its own parent element, so scoping it to part of the page works too (see "Scoping to part of the page" below).
>
> **Pointer events:** when the container covers a large area of the page (e.g. the full viewport), most of that area is still empty space — SparkScan itself only ever renders a small trigger button (and, when opened, a mini preview). Left at the default `pointer-events: auto`, that empty space silently blocks clicks, keystrokes, and dropdowns on the rest of your page, even where nothing is visibly rendered. Set `pointer-events: none` on the container and `pointer-events: auto` back on `<spark-scan-view>` (or the element passed to `SparkScanView.forElement`), so only SparkScan's own controls stay clickable and everything else passes through to your app.
> - **Vanilla JS:** create a dedicated overlay element for `SparkScanView.forElement` — don't mount into `document.body` itself, since setting `pointer-events: none` there would block your entire page, not just the empty overlay space. `position: fixed` here is a deliberate layout choice (float over the whole page without taking up flow space), not something SparkScan requires:
>   ```js
>   const sparkScanContainer = document.createElement("div");
>   sparkScanContainer.style.cssText =
>     "position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;";
>   document.body.appendChild(sparkScanContainer);
>   ```
>   Pass `sparkScanContainer` (not `document.body`) to `SparkScanView.forElement`, then set `pointer-events: auto` on the returned view.
> - **React:** wrap `<spark-scan-view>` in a container `<div>` with `position: fixed; inset: 0; pointer-events: none`, and set `pointer-events: auto` on `<spark-scan-view>` itself — e.g. `<div style={{ position: 'fixed', inset: 0, pointerEvents: 'none' }}><spark-scan-view style={{ pointerEvents: 'auto' }} ... /></div>`.
>
> **Scoping to part of the page:** the container doesn't have to be a full-viewport overlay, and it doesn't need `position: fixed`/`absolute` either — a normal-flow container with a resolved height works. SparkScan sizes itself from its own parent element's `clientWidth`/`clientHeight`, so mounting it inside a smaller region — e.g. a `<main>` between a `<header>` and `<footer>` in a plain flex layout — confines the trigger button and mini preview to that region. They have no way to render over the header/footer, since those elements live outside the container's box entirely:
>   ```html
>   <body style="display: flex; flex-direction: column; height: 100vh; margin: 0">
>     <header style="flex: none">...</header>
>     <main style="flex: 1; min-height: 0">
>       <!-- mount SparkScanView here, e.g. via SparkScanView.forElement(mainElement, ...) -->
>     </main>
>     <footer style="flex: none">...</footer>
>   </body>
>   ```
>   Set the element passed to `SparkScanView.forElement` to `display: block; width: 100%; height: 100%` so it fills `<main>`. (`position: relative` on `<main>` is only needed if you plan to absolutely-position something else of your own inside it — SparkScan doesn't require it.)
>
>   **236px caveat:** if the container's width *or* height ever drops below 236px (`triggerButtonExpandedSize`, 220px, + `miniPreviewPadding`, 16px), SparkScan automatically switches to its "unconstrained" sizing mode: the trigger button and mini preview switch to `position: fixed` and position themselves against the actual browser viewport instead of the container, so they can escape the container's bounds — e.g. render over your header/footer — even though the container itself stayed put. This is an automatic SDK fallback so an expanded 220px control never gets clipped by a too-small container, not something you configure. A typical header+main+footer layout stays well above 236px, but keep it in mind for narrow split-panes or embedded widgets.

```typescript
import {
  type Barcode,
  barcodeCaptureLoader,
  SparkScan,
  SparkScanBarcodeErrorFeedback,
  type SparkScanBarcodeFeedback,
  SparkScanBarcodeSuccessFeedback,
  type SparkScanFeedbackDelegate,
  type SparkScanSession,
  SparkScanSettings,
  SparkScanView,
  SparkScanViewSettings,
  Symbology,
} from "@scandit/web-datacapture-barcode";
import { BrowserHelper, DataCaptureContext } from "@scandit/web-datacapture-core";
import { showMultithreadingWarning } from "./multithreading-warning";

async function run() {
    BrowserHelper.checkMultithreadingSupport()
        .then((supported) => {
            if (!supported) {
                showMultithreadingWarning();
            }
        })
        .catch(console.error);

    await DataCaptureContext.forLicenseKey(
        "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
        {
         // or use the CDN, pinned to the exact version you import: https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-barcode@8.6.1/sdc-lib/
         libraryLocation: new URL("self-hosted-scandit-sdc-lib", document.baseURI).toString(),
         moduleLoaders: [barcodeCaptureLoader()],
        }
    );

    const settings: SparkScanSettings = new SparkScanSettings();
    settings.enableSymbologies([
        Symbology.EAN13UPCA,
        Symbology.Code128,
        Symbology.QR,
    ]);

    const sparkScan: SparkScan = SparkScan.forSettings(settings);

    const sparkScanListener = {
        didScan: (sparkScan: SparkScan, session: SparkScanSession) => {
            const barcode = session.newlyRecognizedBarcode;
            if (barcode) {
              console.log("Scanned", barcode.symbology, barcode.data);
            }
        },
    };
    sparkScan.addListener(sparkScanListener);

    const sparkScanViewSettings = new SparkScanViewSettings();

    // SparkScan requires a mount element with defined dimensions and positioning. Use a
    // dedicated overlay (not document.body) so the app's existing content keeps working.
    const sparkScanContainer = document.createElement("div");
    sparkScanContainer.style.cssText =
      "position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;";
    document.body.appendChild(sparkScanContainer);

    const sparkScanView = SparkScanView.forElement(
      sparkScanContainer,
      DataCaptureContext.sharedInstance,
      sparkScan,
      sparkScanViewSettings
    );
    // Most of the overlay is empty space; re-enable pointer events only on SparkScan's own
    // controls (trigger button, mini preview) so clicks elsewhere still reach your app.
    sparkScanView.style.pointerEvents = "auto";

    const feedbackDelegate: SparkScanFeedbackDelegate = {
      getFeedbackForBarcode(barcode: Barcode): SparkScanBarcodeFeedback | null {
          if (barcode.data === "5901234123457") {
            return new SparkScanBarcodeErrorFeedback("Invalid barcode.", 60_000);
          }
          return new SparkScanBarcodeSuccessFeedback();
      },
    };

    sparkScanView.feedbackDelegate = feedbackDelegate;

    async function mount() {
      await sparkScanView.prepareScanning();
    }

    async function unmount() {
      sparkScan.removeListener(sparkScanListener);
      await sparkScanView.stopScanning();
    }

    return mount().catch(async (error) => {
      console.error(error);
      await unmount();
    });
}

run();

```

`SparkScanView` already switches to its idle state when the page is hidden, so do not add a `visibilitychange` handler to pause scanning.

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

If those headers break other cross-origin images on the page, see `troubleshooting.md`.

## SparkScan feedback API

`feedbackDelegate.getFeedbackForBarcode` runs for every recognized barcode and decides the feedback the user gets: return `null` for the default, or a `SparkScanBarcodeSuccessFeedback` / `SparkScanBarcodeErrorFeedback`.

```typescript
import {
    type Barcode,
    SparkScanBarcodeErrorFeedback,
    type SparkScanBarcodeFeedback,
    SparkScanBarcodeSuccessFeedback,
    type SparkScanFeedbackDelegate,
} from "@scandit/web-datacapture-barcode";
import { Brush, Color } from "@scandit/web-datacapture-core";

// Your own validation rule — e.g. accept only barcodes that match your catalog.
function isValidBarcode(barcode: Barcode): boolean {
    return barcode.data != null && barcode.data.startsWith("PROD-");
}

// Optional visuals. Defined once and reused — not recreated on every scan.
const errorColor = Color.fromHex("#FA4446");
const successColor = Color.fromHex("#28D380");
const errorBrush = new Brush(errorColor, errorColor, 1); // fillColor, strokeColor, strokeWidth
const successBrush = new Brush(successColor, successColor, 1);

const feedbackDelegate: SparkScanFeedbackDelegate = {
    getFeedbackForBarcode(barcode: Barcode): SparkScanBarcodeFeedback | null {
        if (!isValidBarcode(barcode)) {
            const message = "Barcode not in catalog"; // shown to the user
            const resumeCapturingDelay = 2000;         // ms before scanning resumes
            return new SparkScanBarcodeErrorFeedback(message, resumeCapturingDelay, errorColor, errorBrush);
        }
        return new SparkScanBarcodeSuccessFeedback(successColor, successBrush);
    },
};
```

For the exact constructor parameters (including the optional trailing arguments), see the API reference:

- Error feedback: <https://docs.scandit.com/data-capture-sdk/web/barcode-capture/api/ui/spark-scan-barcode-feedback.html#class-scandit.datacapture.barcode.spark.feedback.Error>
- Success feedback: <https://docs.scandit.com/data-capture-sdk/web/barcode-capture/api/ui/spark-scan-barcode-feedback.html#class-scandit.datacapture.barcode.spark.feedback.Success>

## Capturing the scanned frame image

When users want to display or store the image of the frame that contained the barcode, use `frameData.toBlob()` inside `didScan`.

Two important constraints:
- **Do not `await` the blob conversion.** It can take tens of milliseconds; awaiting it blocks the scan pipeline and degrades throughput. Fire it with `.then()/.catch()` and update the UI when it resolves.
- **JPEG at low quality is the fastest option.** `"image/jpeg"` with quality `0.3` gives a usable thumbnail quickly. Use higher quality only if the image needs to be legible.

```typescript
function didScan(_sparkScan: SparkScan, session: SparkScanSession, frameData: FrameData): Promise<void> {
    const barcode = session.newlyRecognizedBarcode;
    if (!barcode) {
        return;
    }

    const data = barcode.data ?? "";
    const symbology = new SymbologyDescription(barcode.symbology).readableName;

    // JPEG is the fastest format to convert to blob — do not await, it may take a while
    frameData
        .toBlob("image/jpeg", 0.3)
        .then((blob) => {
            addScanResult(blob, data, symbology);
        })
        .catch((error) => {
            console.error(error);
            // Add scan result without image if conversion fails
            addScanResult(null, data, symbology);
        });
}
```

Adapt `addScanResult` to your app's data model — it receives a `Blob | null` image, the barcode data string, and the human-readable symbology name. Import `SymbologyDescription` from `@scandit/web-datacapture-barcode` if not already present.

---

## Custom trigger button

Hiding the built-in trigger and driving scanning from your own UI is fully supported. The subsections below cover the behaviors you need to handle when you take over the trigger.

### Driving the scanning lifecycle yourself

Hide the built-in trigger with `triggerButtonVisible = false`, then drive the view through its lifecycle yourself: `prepareScanning()` → `startScanning()` → `pauseScanning()` / `stopScanning()`. (`pauseScanning()` returns the view to idle but keeps it prepared; `stopScanning()` tears scanning down and un-prepares it.)

```typescript
sparkScanView.triggerButtonVisible = false;
await sparkScanView.prepareScanning(); // warm up before the first start
```

### When `prepareScanning()` is required

`prepareScanning()` warms up the engine, and its counterpart is `stopScanning()` (which un-prepares the view). You need to prepare in exactly two situations:

- **Once before the first `startScanning()`**, coming out of the Initial state.
- **Again after `stopScanning()`**, because stopping un-prepares the view.

You do **not** need to prepare again after `pauseScanning()` — pausing returns the view to idle but keeps it prepared, so you can call `startScanning()` directly. The light pause/start cycle stays within an already-prepared session.

If you call `startScanning()` while the view is un-prepared (from Initial, or after a `stopScanning()`), it throws:

```
prepare should be called before calling switchToActiveState
```

So pair every `stopScanning()` with a `prepareScanning()` before the next start:

```typescript
async function restartAfterStop() {
    await sparkScanView.prepareScanning(); // required: stopScanning() un-prepared the view
    await sparkScanView.startScanning();
}
```

### Overriding the click-outside behavior (only if needed)

SparkScan binds a **document-level `pointerup`** handler that acts as "click outside to dismiss," returning the view to idle. This default is usually what you want, so normally you don't need to do anything.

Only if you want to override it — for example, so a tap on your custom trigger doesn't also trigger that dismissal — call `stopPropagation()` on your button's `pointerup` so the event never reaches the document handler:

```typescript
button.addEventListener("pointerup", (event) => {
    event.stopPropagation(); // opt out of SparkScan's document-level click-outside dismissal
});
```

### Preview stacking / z-index

The camera preview is positioned within the stacking context of its mount element. If app chrome creates its own stacking context that out-ranks the mount, the preview can render *under* that chrome even with a high `z-index` on the preview. Make sure the mount element out-ranks the app chrome you want the preview to appear above. (For reference, the official ListBuildingSample mounts the view in a full-size `absolute` container layered over the rest of the page, while sibling controls underneath remain interactive — the view only intercepts pointer events on its own trigger and toolbar.)

### Keep the button in sync with the actual view state

When hiding the default trigger button and providing your own, a naive click-toggle approach breaks in practice:

1. User clicks → `startScanning()` → scanner starts ✓
2. Barcode is scanned → SparkScan **automatically** transitions back to idle
3. User clicks again → handler still thinks scanner is active → calls `pauseScanning()` on an already-idle engine → **nothing happens**
4. Another click is needed to restart, leaving the user stuck

**The fix:** always use `SparkScanViewUiListener.didChangeViewState` to keep the button in sync with the actual scanner state. Drive click behavior from the current state, not from a toggled local flag. The camera preview is only visible in the `Active` state (the default scanning mode is single-shot and non-persistent), so map your label/preview UI off `Active` specifically — keying off anything else makes the label lag a frame behind the preview.

```typescript
let currentViewState: SparkScanViewState = SparkScanViewState.Idle;

const uiListener = {
    didChangeViewState: (_view: SparkScanView, viewState: SparkScanViewState) => {
        currentViewState = viewState;
        button.textContent = viewState === SparkScanViewState.Active ? "STOP SCANNING" : "START SCANNING";
    },
};
sparkScanView.uiListener = uiListener;

const handleButtonClick = async () => {
    if (currentViewState === SparkScanViewState.Active) {
        await sparkScanView.pauseScanning();
    } else {
        await sparkScanView.startScanning();
    }
};
button.addEventListener("click", handleButtonClick);

// In the unmount/cleanup function:
async function unmount() {
    button.removeEventListener("click", handleButtonClick);
    sparkScanView.uiListener = null;
    await sparkScanView.stopScanning();
}
```

This ensures that after an automatic state change (e.g. scan completes and engine idles), the next button click does the right thing. Using named references for both the click handler and the UI listener means cleanup is clean and avoids memory leaks.
