# BarcodeCapture Web Integration Guide

BarcodeCapture is the low-level single-barcode scanning mode. On web you wire it up by hand: a `DataCaptureContext`, a `Camera` as the frame source, the `BarcodeCapture` mode with a `BarcodeCaptureListener`, a `DataCaptureView` for the camera preview, and a `BarcodeCaptureOverlay` for the highlight. Unlike SparkScan, there is no pre-built scanning UI — the camera preview and highlight rectangle are the only visuals.

Examples below use TypeScript (v8). The same APIs work in plain JavaScript — just remove the type annotations.

## Starting from zero? Use the pre-built sample

If the user has no existing app yet, always offer the official sample as the fastest path to a working integration — it already has the correct project structure, dependencies, and best practices in place.

Ask whether they are using React or plain web (TypeScript/JavaScript), then point them to the right sample:

- **Vanilla JS / TypeScript:** <https://github.com/Scandit/datacapture-web-samples/tree/master/01_Single_Scanning_Samples/02_Barcode_Scanning_with_Low-level_API/BarcodeCaptureSimpleSample>
- **React:** <https://github.com/Scandit/datacapture-web-samples/tree/master/05_Framework_Integration_Samples/BarcodeCaptureReactSample>

Tell the user to clone the repo and open the relevant sample folder. Once they have it open, help them:

1. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with their key from <https://ssl.scandit.com>
2. Adjust the enabled symbologies to match their use case (remind them to only enable what they need — fewer symbologies means better performance and accuracy)
3. Run `npm install` (or their package manager of choice) and start the app

Only proceed to the manual integration steps below if the user already has an existing project they need to add BarcodeCapture to.

---

## Adding BarcodeCapture to an existing project

### Prerequisites

- Scandit Data Capture SDK for web — add via npm, pnpm or yarn:
  - `@scandit/web-datacapture-core`: <https://www.npmjs.com/package/@scandit/web-datacapture-core>
  - `@scandit/web-datacapture-barcode`: <https://www.npmjs.com/package/@scandit/web-datacapture-barcode>
  - A valid Scandit license key — sign in at <https://ssl.scandit.com> to generate one (no account? sign up at <https://ssl.scandit.com/dashboard/sign-up?p=test>)

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask which file or component they'd like to integrate BarcodeCapture into. Then write the integration code directly into that file — do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**

1. Add `@scandit/web-datacapture-core` and `@scandit/web-datacapture-barcode` via your package manager: <https://www.npmjs.com/package/@scandit/web-datacapture-core> <https://www.npmjs.com/package/@scandit/web-datacapture-barcode>
2. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from <https://ssl.scandit.com>
3. Add a `<div id="capture-element">` (or similar) to your HTML with defined dimensions and positioning (see mount point requirement below)
4. If self-hosting the SDK engine files, update `libraryLocation` to point to the correct path. Alternatively, use the CDN path: `https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-barcode@8/sdc-lib/`

The code example below is a basic TypeScript v8 implementation.
If the user is using React, see the React section below.

> **Mount point requirement:** The `DataCaptureView` needs a container with defined dimensions and positioning to render its camera preview correctly. If the container has zero or unresolved dimensions, the camera preview will not display.
> - Style the element before calling `view.connectToElement()` — e.g., `captureElement.style.cssText = "position: fixed; top: 0; left: 0; width: 100%; height: 100%;"`.
> - The element can be any block-level element (`<div>`, `<main>`, etc.) as long as it has non-zero width and height.

```typescript
import {
    BarcodeCapture,
    type BarcodeCaptureListener,
    BarcodeCaptureOverlay,
    type BarcodeCaptureSession,
    BarcodeCaptureSettings,
    barcodeCaptureLoader,
    Symbology,
} from "@scandit/web-datacapture-barcode";
import {
    Camera,
    DataCaptureContext,
    DataCaptureView,
    type FrameData,
    FrameSourceState,
} from "@scandit/web-datacapture-core";

async function run() {
    await DataCaptureContext.forLicenseKey(
        "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
        {
            // or use the CDN: https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-barcode@8/sdc-lib/
            libraryLocation: new URL("self-hosted-scandit-sdc-lib", document.baseURI).toString(),
            moduleLoaders: [barcodeCaptureLoader()],
        }
    );

    const settings = new BarcodeCaptureSettings();
    settings.enableSymbologies([
        Symbology.EAN13UPCA,
        Symbology.Code128,
        Symbology.QR,
    ]);

    const camera = Camera.pickBestGuess();
    await camera.applySettings(BarcodeCapture.recommendedCameraSettings);
    await DataCaptureContext.sharedInstance.setFrameSource(camera);

    const barcodeCapture = await BarcodeCapture.forContext(
        DataCaptureContext.sharedInstance,
        settings
    );

    const barcodeCaptureListener: BarcodeCaptureListener = {
        didScan: async (barcodeCapture: BarcodeCapture, session: BarcodeCaptureSession) => {
            const barcode = session.newlyRecognizedBarcode;
            if (!barcode) return;

            // Disable immediately to prevent duplicate scans while handling the result.
            await barcodeCapture.setEnabled(false);

            console.log("Scanned", barcode.symbology, barcode.data);

            // Re-enable when ready to scan again.
            await barcodeCapture.setEnabled(true);
        },
    };
    barcodeCapture.addListener(barcodeCaptureListener);

    // The capture element must have defined dimensions and positioning.
    const captureElement = document.getElementById("capture-element")!;
    captureElement.style.cssText = "position: fixed; top: 0; left: 0; width: 100%; height: 100%;";

    const view = await DataCaptureView.forContext(DataCaptureContext.sharedInstance);
    view.connectToElement(captureElement);

    await BarcodeCaptureOverlay.withBarcodeCaptureForView(barcodeCapture, view);

    async function mount() {
        await DataCaptureContext.sharedInstance.frameSource!.switchToDesiredState(FrameSourceState.On);
    }

    async function unmount() {
        barcodeCapture.removeListener(barcodeCaptureListener);
        await DataCaptureContext.sharedInstance.frameSource!.switchToDesiredState(FrameSourceState.Off);
        view.detachFromElement();
    }

    return mount().catch(async (error) => {
        console.error(error);
        await unmount();
    });
}

run();
```

---

## React integration

For React, use a `useRef` to attach `DataCaptureView` to a DOM element, and `useEffect` for initialization and cleanup.

```tsx
import { useEffect, useRef } from "react";
import {
    BarcodeCapture,
    type BarcodeCaptureListener,
    BarcodeCaptureOverlay,
    type BarcodeCaptureSession,
    BarcodeCaptureSettings,
    barcodeCaptureLoader,
    Symbology,
} from "@scandit/web-datacapture-barcode";
import {
    Camera,
    DataCaptureContext,
    DataCaptureView,
    type FrameData,
    FrameSourceState,
} from "@scandit/web-datacapture-core";

export const BarcodeScannerComponent: React.FC = () => {
    const captureRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        let barcodeCapture: BarcodeCapture | null = null;
        let view: DataCaptureView | null = null;
        let barcodeCaptureListener: BarcodeCaptureListener | null = null;

        async function initialize() {
            await DataCaptureContext.forLicenseKey(
                "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
                {
                    libraryLocation: new URL("self-hosted-scandit-sdc-lib", document.baseURI).toString(),
                    moduleLoaders: [barcodeCaptureLoader()],
                }
            );

            const settings = new BarcodeCaptureSettings();
            settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.Code128]);

            const camera = Camera.pickBestGuess();
            await camera.applySettings(BarcodeCapture.recommendedCameraSettings);
            await DataCaptureContext.sharedInstance.setFrameSource(camera);

            barcodeCapture = await BarcodeCapture.forContext(
                DataCaptureContext.sharedInstance,
                settings
            );

            barcodeCaptureListener = {
                didScan: async (bc: BarcodeCapture, session: BarcodeCaptureSession) => {
                    const barcode = session.newlyRecognizedBarcode;
                    if (!barcode) return;
                    await bc.setEnabled(false);
                    console.log("Scanned", barcode.symbology, barcode.data);
                    await bc.setEnabled(true);
                },
            };
            barcodeCapture.addListener(barcodeCaptureListener);

            view = await DataCaptureView.forContext(DataCaptureContext.sharedInstance);
            view.connectToElement(captureRef.current!);

            await BarcodeCaptureOverlay.withBarcodeCaptureForView(barcodeCapture, view);

            await DataCaptureContext.sharedInstance.frameSource!.switchToDesiredState(FrameSourceState.On);
        }

        initialize().catch(console.error);

        return () => {
            if (barcodeCaptureListener && barcodeCapture) {
                barcodeCapture.removeListener(barcodeCaptureListener);
            }
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

---

## Progressive Web App (PWA)

The official PWA sample is the recommended starting point:
<https://github.com/Scandit/datacapture-web-samples/tree/master/01_Single_Scanning_Samples/02_Barcode_Scanning_with_Low-level_API/BarcodeCaptureSimplePwaSample>

It includes a production-ready `vite.config.ts` that handles COOP/COEP, `sdc-lib` self-hosting, service worker generation, and manifest configuration. Reference it instead of writing a Workbox config from scratch.

### Why PWA needs special Workbox configuration

The Scandit SDK ships WASM files that can exceed 10 MB. Workbox's default `maximumFileSizeToCacheInBytes` is 2 MB — without raising this limit, the SDK's WASM files are silently excluded from the service worker cache and the app will fail to load offline.

Use the `vite.config.ts` from `BarcodeCaptureSimplePwaSample` as the authoritative reference for the complete Workbox setup — it handles the file size limit, `NetworkFirst` caching for WASM assets, version-aware cache keys, `skipWaiting`/`clientsClaim`, and the PWA manifest:
<https://github.com/Scandit/datacapture-web-samples/blob/master/01_Single_Scanning_Samples/02_Barcode_Scanning_with_Low-level_API/BarcodeCaptureSimplePwaSample/vite.config.ts>

> **Note:** The PWA sample uses `Cross-Origin-Embedder-Policy: credentialless` (CDN-hosted SDK). If you self-host the `sdc-lib`, use `require-corp` instead.

### iOS camera permissions in standalone PWA

Camera access in a PWA installed with `display: standalone` on iOS is unreliable in ways that do not affect Android or desktop. iOS runs standalone PWAs in a WKWebView context that is permission-sandboxed separately from Safari — meaning permission granted in one context does not automatically carry to another.

Common failure modes:
- `NotAllowedError` on `getUserMedia` even after the user previously granted camera access
- Camera permission prompt never appearing (silently denied)
- Permission lost after the app is backgrounded and resumed
- Any navigation that leaves the standalone context (e.g. `window.open()`, external links) spawns a Safari tab with its own separate permission state

**Mitigations:**

- **Stay in the standalone context.** Use client-side routing or full-page overlays instead of `window.open()` or links that break out of the PWA shell. This is the most reliable fix.

- **Keep `window.open()` calls synchronous inside a user gesture.**
  iOS invalidates the activation gesture if any `await` precedes the call:
  ```javascript
  // ❌ Gesture chain broken — NotAllowedError risk
  button.addEventListener("click", async () => {
      await somethingAsync();
      window.open(url);
  });

  // ✅ Open synchronously, then do async work
  button.addEventListener("click", () => {
      window.open(url);
      doAsyncStuff();
  });
  ```

- **Pre-warm the camera permission** before any navigation that leaves the PWA context:
  ```javascript
  const stream = await navigator.mediaDevices.getUserMedia({ video: true });
  stream.getTracks().forEach((t) => t.stop()); // release immediately
  // system-level permission is now granted before the new context opens
  ```

- **Declare a Permissions Policy** on the page and server to signal intent:
  ```html
  <meta http-equiv="Permissions-Policy" content="camera=*">
  ```
  ```
  Permissions-Policy: camera=*
  ```

> There is no fully reliable fix for camera access across separate iOS browser contexts. If the scanning flow must open a new tab or navigate cross-origin, expect users to be prompted again or denied — and design a fallback accordingly.

### PWA vs regular web: what changes

| Concern | Regular web | PWA |
|---------|-------------|-----|
| COEP header | `require-corp` (self-hosted) / `credentialless` (CDN) | Same |
| Service worker | None | Required; configure Workbox for WASM |
| WASM cache limit | N/A | Must raise to ≥ 10 MB |
| Camera permission | Per visit | Persists with `display: standalone` on most browsers |
| Offline support | None | Possible once SW caches SDK assets |

---

## Capturing the scanned frame image

When users want to display or store the image of the frame that contained the barcode, use `frameData.toBlob()` inside `didScan`. The `frameData` parameter is the third argument of the `didScan` callback — import `FrameData` from `@scandit/web-datacapture-core`.

Two important constraints:
- **Do not `await` the blob conversion.** It can take tens of milliseconds; awaiting it blocks the scan pipeline and degrades throughput. Fire it with `.then()/.catch()` and update the UI when it resolves.
- **JPEG at low quality is the fastest option.** `"image/jpeg"` with quality `0.3` gives a usable thumbnail quickly. Use higher quality only if the image needs to be legible.

```typescript
import {
    type BarcodeCaptureListener,
    type BarcodeCaptureSession,
    SymbologyDescription,
} from "@scandit/web-datacapture-barcode";
import { type FrameData } from "@scandit/web-datacapture-core";

const barcodeCaptureListener: BarcodeCaptureListener = {
    didScan: async (barcodeCapture, session: BarcodeCaptureSession, frameData: FrameData) => {
        const barcode = session.newlyRecognizedBarcode;
        if (!barcode) return;

        await barcodeCapture.setEnabled(false);

        const data = barcode.data ?? "";
        const symbology = new SymbologyDescription(barcode.symbology).readableName;

        // JPEG is the fastest format — do not await, conversion may take a while
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
    },
};
```

Adapt `addScanResult` to your app's data model — it receives a `Blob | null` image, the barcode data string, and the human-readable symbology name. Import `SymbologyDescription` from `@scandit/web-datacapture-barcode` if not already present.

---

## Optional configuration

### Duplicate filtering

Suppress repeated scans of the same barcode within a time window. Set `codeDuplicateFilter` (in milliseconds) on `BarcodeCaptureSettings` before creating the mode. `-1` reports each code only once until scanning stops; `0` reports every detection.

```typescript
settings.codeDuplicateFilter = 500; // suppress duplicates within 500 ms
```

To change at runtime, update `settings` and call `barcodeCapture.applySettings(settings)`.

### BarcodeCaptureFeedback

By default, BarcodeCapture plays a beep on success. To customize feedback, set `barcodeCapture.feedback` before the first scan. Fetch the [Advanced Configurations](https://docs.scandit.com/sdks/web/barcode-capture/advanced/) page for the exact `BarcodeCaptureFeedback` constructor arguments — do not guess.

### Viewfinder

Attach a viewfinder to the overlay to draw a guide on the preview. Fetch the [Advanced Configurations](https://docs.scandit.com/sdks/web/barcode-capture/advanced/) page for the `RectangularViewfinder` API and style options — do not guess the constructor arguments.

### Location selection

To restrict scanning to a sub-area of the preview, use `RectangularLocationSelection` on `BarcodeCaptureSettings`. Fetch the [Advanced Configurations](https://docs.scandit.com/sdks/web/barcode-capture/advanced/) page for the exact API.

### Composite codes

Composite codes (linear + 2D companion) require both symbologies and composite types to be enabled. Fetch the [Advanced Configurations](https://docs.scandit.com/sdks/web/barcode-capture/advanced/) page for the exact API.

### Active symbol counts

For variable-length symbologies (Code 39, ITF, Code 128, etc.) you can restrict which barcode lengths are accepted. This reduces false positives and can speed up scanning — especially useful when you know the exact length of the barcodes in your use case (e.g., ITF-14 is always 14 characters).

```typescript
// Accept only ITF (Interleaved 2 of 5) barcodes of length 14 (ITF-14)
const itfSettings = settings.getSymbologySettings(Symbology.InterleavedTwoOfFive);
itfSettings.activeSymbolCounts = new Set([14]);

// Accept Code 39 barcodes of 6, 7, or 8 characters
const code39Settings = settings.getSymbologySettings(Symbology.Code39);
code39Settings.activeSymbolCounts = new Set([6, 7, 8]);
```

Call `settings.getSymbologySettings(symbology)` to get the `SymbologySettings` for that symbology, then set `activeSymbolCounts` to a `Set<number>` containing the accepted lengths. For fixed-length symbologies (EAN-13, QR Code, DataMatrix) this property has no effect.

> **Note:** ITF-14 is `Symbology.InterleavedTwoOfFive` — there is no `Symbology.ITF` in the web SDK.

### Scan intention

`ScanIntention` controls how aggressively the engine decides that a barcode in the frame is intentionally targeted by the user. Import it from `@scandit/web-datacapture-barcode`.

```typescript
import { ScanIntention } from "@scandit/web-datacapture-barcode";

// Default — disables smart algorithms; scans barcodes as detected
settings.scanIntention = ScanIntention.Manual;

// On supported devices, identifies and scans the barcode the user intends to capture
settings.scanIntention = ScanIntention.Smart;

// Identifies multiple candidates and scans the one the user indicates (v8.1.0+)
settings.scanIntention = ScanIntention.SmartSelection;
```

- **`Manual`** (default): no smart algorithms. Scans any barcode detected in the frame. Use for explicit user-triggered flows or when you need predictable behaviour on low-end hardware.
- **`Smart`**: on supported devices, automatically identifies and scans the barcode the user intends to capture, reducing accidental scans in hand-held use.
- **`SmartSelection`** (v8.1.0+): identifies multiple barcode candidates in the frame and scans the one the user indicates. Reduces errors in dense barcode environments.

> `ScanIntention.Smart` and `ScanIntention.SmartSelection` use `SharedArrayBuffer` for multithreaded processing. If you enable either, set the cross-origin isolation headers on your server — see [Cross-origin isolation](#cross-origin-isolation-coop--coep) below.

### Battery saving

When scanning is paused (tab hidden, dialog open, user navigates away), stop the camera and disable the mode to avoid unnecessary CPU and power consumption:

```typescript
// Pause scanning
await barcodeCapture.setEnabled(false);
await DataCaptureContext.sharedInstance.frameSource?.switchToDesiredState(FrameSourceState.Off);

// Resume scanning
await DataCaptureContext.sharedInstance.frameSource?.switchToDesiredState(FrameSourceState.On);
await barcodeCapture.setEnabled(true);
```

The camera does not pause automatically when the page loses focus. Hook into `visibilitychange` to handle tab switching:

```typescript
document.addEventListener("visibilitychange", async () => {
    if (document.hidden) {
        await barcodeCapture.setEnabled(false);
        await DataCaptureContext.sharedInstance.frameSource?.switchToDesiredState(FrameSourceState.Off);
    } else {
        await DataCaptureContext.sharedInstance.frameSource?.switchToDesiredState(FrameSourceState.On);
        await barcodeCapture.setEnabled(true);
    }
});
```

### Cross-origin isolation (COOP / COEP)

`ScanIntention.Smart` and multithreaded SDK processing require `SharedArrayBuffer`, which browsers restrict to [cross-origin isolated](https://developer.mozilla.org/en-US/docs/Web/API/crossOriginIsolated) contexts. Without these headers the SDK falls back to single-threaded mode, which is slower and may reduce scan accuracy.

See the official guide: <https://docs.scandit.com/sdks/web/matrixscan/get-started/#improve-runtime-performance-by-enabling-browser-multithreading>

Always set:
```
Cross-Origin-Opener-Policy: same-origin
```

For `Cross-Origin-Embedder-Policy`, the value depends on how you host the SDK:

| Hosting | COEP value |
|---------|-----------|
| Self-hosted SDK files | `require-corp` |
| CDN (`cdn.jsdelivr.net`) | `credentialless` (Chrome/Edge 96+) |

For the complete Vite setup — COOP/COEP middleware, `sdc-lib` self-hosting with `vite-plugin-static-copy`, and license key injection — use the official sample as the source of truth:
<https://github.com/Scandit/datacapture-web-samples/blob/master/01_Single_Scanning_Samples/02_Barcode_Scanning_with_Low-level_API/BarcodeCaptureSimpleSample/vite.config.ts>

Key things to know when adapting it:
- Headers are set via a **Vite middleware**, not `server.headers` — this ensures both the dev server and the preview server send them.
- `sdc-lib` is copied from **both** `@scandit/web-datacapture-core` and `@scandit/web-datacapture-barcode` using `vite-plugin-static-copy`. The `libraryLocation` in your code must match the destination path.
- Use `credentialless` for COEP when serving the SDK from the CDN; use `require-corp` when self-hosting.

> **Heads up:** COEP blocks cross-origin resources (images, fonts, iframes, third-party scripts) that do not include `Cross-Origin-Resource-Policy` or `Access-Control-Allow-Origin`. Audit your page's cross-origin dependencies before enabling COEP in production — some third-party embeds (analytics, ads, chat widgets) may stop loading. After changing headers, clear your browser cache and restart the dev server.

---

## Key Rules

1. **Await everything** — `DataCaptureContext.forLicenseKey`, `BarcodeCapture.forContext`, `DataCaptureView.forContext`, `BarcodeCaptureOverlay.withBarcodeCaptureForView`, `camera.applySettings`, `setFrameSource`, `switchToDesiredState`, and `setEnabled` are all async. Forgetting an `await` causes silent failures.
2. **Use `sharedInstance`** — after `DataCaptureContext.forLicenseKey()`, reference the context via `DataCaptureContext.sharedInstance`, not a captured return value.
3. **Disable inside `didScan`** — call `await barcodeCapture.setEnabled(false)` before doing any non-trivial work to avoid duplicate scans.
4. **Listener name** — the callback is `didScan`, not `onBarcodeScanned` (that is the Android name).
5. **`codeDuplicateFilter` is a number** — set it to an integer (milliseconds), not a `TimeInterval` object.
6. **Mount point dimensions** — the element passed to `view.connectToElement()` must have non-zero width and height and a set `position` (fixed or absolute). Zero-sized containers silently break the preview.
7. **Camera lifecycle** — turn the camera off with `FrameSourceState.Off` when the scanning surface is no longer visible. The camera does not stop automatically.
8. **Overlay is explicit** — `BarcodeCaptureOverlay.withBarcodeCaptureForView(barcodeCapture, view)` adds the overlay to the view. There is no implicit overlay.
9. **Symbologies** — enable only what's needed; each extra symbology adds processing time. Verify symbology names against the API reference — web uses camelCase (e.g. `Symbology.EAN13UPCA`, `Symbology.Code128`).
10. **Active symbol counts** — for variable-length codes (Code 39, ITF, Code 128), always set `activeSymbolCounts` to the exact lengths you expect. Accepting all lengths increases false-positive risk.
11. **Scan intention and cross-origin isolation** — `ScanIntention.Smart` requires `SharedArrayBuffer`. If you enable it, serve the page with `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp` (self-hosted) or `credentialless` (CDN), otherwise the SDK silently degrades to single-threaded mode. The default is `ScanIntention.Manual`.
