# BarcodeCapture Web Integration Guide

BarcodeCapture is the low-level single-barcode scanning mode. On web you wire it up by hand: a `DataCaptureContext`, a `Camera` as the frame source, the `BarcodeCapture` mode with a `BarcodeCaptureListener`, a `DataCaptureView` for the camera preview, and a `BarcodeCaptureOverlay` for the highlight. Unlike SparkScan, there is no pre-built scanning UI — the camera preview and highlight rectangle are the only visuals.

Examples below use TypeScript (v8). The same APIs work in plain JavaScript — just remove the type annotations.

## Starting from zero? Use the pre-built sample

If the user has no existing app yet, always offer the official sample as the fastest path to a working integration — it already has the correct project structure, dependencies, and best practices in place.

Ask whether they are using React or plain web (TypeScript/JavaScript), then point them to the right sample:

- **Vanilla JS / TypeScript:** <https://github.com/Scandit/datacapture-web-samples/tree/master/01_Single_Scanning_Samples/02_Barcode_Scanning_with_Low-level_API/BarcodeCaptureSimpleSample>
- **React:** <https://github.com/Scandit/datacapture-web-samples/tree/master/05_Framework_Integration_Samples/BarcodeCaptureReactSample>

Tell the user to clone the repo and open the relevant sample folder. Once they have it open, help them:

1. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key (see **Licence key** in `SKILL.md`).
2. Adjust the enabled symbologies to match their use case (remind them to only enable what they need — fewer symbologies means better performance and accuracy)
3. Run `npm install` (or their package manager of choice) and start the app

Only proceed to the manual integration steps below if the user already has an existing project they need to add BarcodeCapture to.

---

## Adding BarcodeCapture to an existing project

### Prerequisites

- Scandit Data Capture SDK for web — add via npm, pnpm or yarn:
  - `@scandit/web-datacapture-core`: <https://www.npmjs.com/package/@scandit/web-datacapture-core>
  - `@scandit/web-datacapture-barcode`: <https://www.npmjs.com/package/@scandit/web-datacapture-barcode>
  - A valid Scandit license key — see **Licence key** in this skill's `SKILL.md`.

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask which file or component they'd like to integrate BarcodeCapture into. Then write the integration code directly into that file — do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**

1. Add `@scandit/web-datacapture-core` and `@scandit/web-datacapture-barcode` via your package manager: <https://www.npmjs.com/package/@scandit/web-datacapture-core> <https://www.npmjs.com/package/@scandit/web-datacapture-barcode>
2. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key (see **Licence key** in `SKILL.md`).
3. Add a `<div id="capture-element">` (or similar) to your HTML with defined dimensions and positioning (see mount point requirement below)
4. If self-hosting the SDK engine files, update `libraryLocation` to point to the correct path. Alternatively, use the CDN path pinned to the exact version you import, for example `https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-barcode@8.6.1/sdc-lib/` (see [Loading the SDK from a CDN](#loading-the-sdk-from-a-cdn))
5. Serve the page with `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp`, also when the SDK comes from the CDN (see [Loading the SDK from a CDN](#loading-the-sdk-from-a-cdn)).
6. Add the `multithreading-warning` helper module from [Loading the SDK from a CDN](#loading-the-sdk-from-a-cdn) (`multithreading-warning.js` on a plain-HTML page, `multithreading-warning.ts` in a bundled app) and import `showMultithreadingWarning` from it. The helper adds the dialog to the page itself, so the page needs no markup for it.

The code example below is a basic TypeScript v8 implementation. It starts the multithreading check in parallel with `forLicenseKey()`: import `showMultithreadingWarning` from the `multithreading-warning` helper module in [Loading the SDK from a CDN](#loading-the-sdk-from-a-cdn), which adds the dialog to the page itself, so the page needs no markup for it. Leave the check out when the user asked to run single-threaded.
If the user is using React, see the React section below.

> **Mount point requirement:** The `DataCaptureView` needs a container with defined dimensions and positioning to render its camera preview correctly. If the container has zero or unresolved dimensions, the camera preview will not display.
> - Style the element before calling `view.connectToElement()` — e.g., `captureElement.style.cssText = "position: fixed; top: 0; left: 0; width: 100%; height: 100%;"`.
> - The element can be any block-level element (`<div>`, `<main>`, etc.) as long as it has non-zero width and height.
> - **Revert the mount-point style after `view.detachFromElement()`.** The element and the style above belong to the app, not to the SDK, so detaching the view does not undo them. A full-viewport `position: fixed` element left in the DOM is invisible and empty, and still swallows every click, keystroke and dropdown interaction on the page underneath. Undo what you set: restore the element's previous style if you mounted into an element the app already used, or hide or remove it if you created it only for scanning. In React the element is part of the component's own JSX, so it leaves the DOM when the component unmounts and needs no manual reset.

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
    BrowserHelper,
    Camera,
    DataCaptureContext,
    DataCaptureView,
    type FrameData,
    FrameSourceState,
} from "@scandit/web-datacapture-core";
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
        // Pairs with the display: none in unmount(). Re-attaching also needs
        // view.connectToElement(captureElement) again if unmount() has run.
        captureElement.style.display = "";
        await DataCaptureContext.sharedInstance.frameSource!.switchToDesiredState(FrameSourceState.On);
    }

    async function unmount() {
        barcodeCapture.removeListener(barcodeCaptureListener);
        await DataCaptureContext.sharedInstance.frameSource!.switchToDesiredState(FrameSourceState.Off);
        view.detachFromElement();
        // detachFromElement() cannot undo the inline style set above: that style belongs to
        // the app. Revert it, or the empty full-viewport element keeps blocking every click
        // on the page underneath. Here the element exists only for scanning, so hiding it is
        // enough; restore the previous value instead if you mounted into an existing element.
        captureElement.style.display = "none";
    }

    return mount().catch(async (error) => {
        console.error(error);
        await unmount();
    });
}

run();
```

`unmount()` keeps the context and its engine, so scanning can resume quickly. For a full teardown, for example when the user leaves the scanning feature, release the engine as well. Add `teardown()` inside `run()`, next to `unmount()`, so it uses the same `barcodeCapture`, `barcodeCaptureListener`, `view` and `captureElement`, and return both from `run()`, in place of its last `return` and the `run();` call, so the code that closes the scanner can call them:

```typescript
    async function teardown() {
        barcodeCapture.removeListener(barcodeCaptureListener);
        await DataCaptureContext.sharedInstance.dispose();
        view.detachFromElement();
        captureElement.style.display = "none";
    }

    await mount().catch(async (error) => {
        console.error(error);
        await unmount();
    });
    return { unmount, teardown };
}

const scanner = await run();
document.getElementById("close-scanner")!.addEventListener("click", () => {
    scanner.teardown().catch(console.error);
});
```

`dispose()` turns the camera off and removes the mode and the view from the context. To scan again afterwards, call `DataCaptureContext.forLicenseKey()` again and set the mode, camera, view and overlay up again.

### Showing the camera while the WASM loads

`forLicenseKey()` downloads and compiles the WASM engine, which can take seconds. To show the camera preview meanwhile, pass the camera to `connectToElement` and switch it on before awaiting `forLicenseKey()`. If `forLicenseKey()` rejects (wrong key, network, CSP), the preview is already live: let the `On` request settle, so a denied permission is not left as an unhandled rejection, then switch the camera off before reporting the error:

```typescript
BrowserHelper.checkMultithreadingSupport()
    .then((supported) => {
        if (!supported) {
            showMultithreadingWarning();
        }
    })
    .catch(console.error);

const camera = Camera.pickBestGuess();
await camera.applySettings(BarcodeCapture.recommendedCameraSettings);

const view = new DataCaptureView();
view.connectToElement(captureElement, { camera });
const cameraStarted = camera.switchToDesiredState(FrameSourceState.On);

try {
    await DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --", {
        libraryLocation: new URL("self-hosted-scandit-sdc-lib", document.baseURI).toString(),
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

---

## React integration

For React, use a `useRef` to attach `DataCaptureView` to a DOM element, and `useEffect` for initialization and cleanup. The dialog is rendered from component state instead of the DOM helper, and a module-level flag keeps it to once per page load, so the effect running twice in React StrictMode does not open it twice. The check runs in parallel with `forLicenseKey()`, so set-up waits for neither the check nor the dialog. Once the cleanup has set `cancelled`, the check's result is ignored, so a StrictMode first mount or a fast unmount does not use up the once-per-page-load flag.

```tsx
import { useEffect, useRef, useState } from "react";
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
    BrowserHelper,
    Camera,
    DataCaptureContext,
    DataCaptureView,
    type FrameData,
    FrameSourceState,
} from "@scandit/web-datacapture-core";

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

export const BarcodeScannerComponent: React.FC = () => {
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
        let barcodeCapture: BarcodeCapture | null = null;
        let view: DataCaptureView | null = null;
        let barcodeCaptureListener: BarcodeCaptureListener | null = null;

        async function initialize() {
            BrowserHelper.checkMultithreadingSupport()
                .then((multithreadingSupported) => {
                    if (cancelled) return;
                    if (!multithreadingSupported && !multithreadingWarningShown && !isMultithreadingWarningDismissed()) {
                        multithreadingWarningShown = true;
                        setMultithreadingUnavailable(true);
                    }
                })
                .catch(console.error);

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
            cancelled = true;
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

---

## Progressive Web App (PWA)

The official PWA sample is the recommended starting point:
<https://github.com/Scandit/datacapture-web-samples/tree/master/01_Single_Scanning_Samples/02_Barcode_Scanning_with_Low-level_API/BarcodeCaptureSimplePwaSample>

It includes a production-ready `vite.config.ts` that handles COOP/COEP, `sdc-lib` self-hosting, service worker generation, and manifest configuration. Reference it instead of writing a Workbox config from scratch.

### Why PWA needs special Workbox configuration

The Scandit SDK ships WASM files that can exceed 10 MB. Workbox's default `maximumFileSizeToCacheInBytes` is 2 MB — without raising this limit, the SDK's WASM files are silently excluded from the service worker cache and the app will fail to load offline.

Use the `vite.config.ts` from `BarcodeCaptureSimplePwaSample` as the authoritative reference for the complete Workbox setup — it handles the file size limit, `NetworkFirst` caching for WASM assets, version-aware cache keys, `skipWaiting`/`clientsClaim`, and the PWA manifest:
<https://github.com/Scandit/datacapture-web-samples/blob/master/01_Single_Scanning_Samples/02_Barcode_Scanning_with_Low-level_API/BarcodeCaptureSimplePwaSample/vite.config.ts>

> **Note:** The PWA sample sets `Cross-Origin-Embedder-Policy: credentialless`. Use `require-corp` instead, whether you self-host the `sdc-lib` or load it from the CDN: Safari does not support `credentialless`.

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
| COEP header | `require-corp` (self-hosted or CDN) | Same |
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

By default, BarcodeCapture plays a beep and vibrates on success. Feedback is configured through `BarcodeCaptureFeedback`, whose `success` property is a `core.Feedback` built from an optional `Vibration` and an optional `Sound`. Pass `null` for the part you want to silence.

```typescript
import { BarcodeCaptureFeedback } from "@scandit/web-datacapture-barcode";
import { Feedback, Sound, Vibration } from "@scandit/web-datacapture-core";

// Start from the default and replace the success feedback.
const feedback = BarcodeCaptureFeedback.default;

// Vibration only — no sound:
feedback.success = new Feedback(Vibration.defaultVibration, null);

// Sound only — no vibration:
feedback.success = new Feedback(null, Sound.defaultSound);

// Apply to the mode. `barcodeCapture.feedback` is read-only — use setFeedback().
await barcodeCapture.setFeedback(feedback);
```

- `BarcodeCaptureFeedback.default` returns a feedback with beep and vibration enabled (web getter is `default`, not `defaultFeedback`).
- `new Feedback(vibration, sound)` — both arguments are nullable; pass `null` to disable that channel.
- `Vibration.defaultVibration` and `Sound.defaultSound` are the built-in defaults. `new Sound(resource)` is also possible.
- A fully silent success: `feedback.success = new Feedback(null, null)`.
- `barcodeCapture.feedback` is a read-only getter on web — apply changes with `await barcodeCapture.setFeedback(feedback)`, not by assigning to `barcodeCapture.feedback`.

### Viewfinder

A viewfinder draws a guide on the preview. Build one of the viewfinder types and attach it with the overlay's `setViewfinder()` method (web uses a method, not a property assignment).

```typescript
import {
    AimerViewfinder,
    LaserlineViewfinder,
    RectangularViewfinder,
    RectangularViewfinderLineStyle,
    RectangularViewfinderStyle,
} from "@scandit/web-datacapture-core";

// Rectangular (most common). Styles: Square, Rounded. Line styles: Bold, Light.
const viewfinder = new RectangularViewfinder(
    RectangularViewfinderStyle.Square,
    RectangularViewfinderLineStyle.Light
);
await overlay.setViewfinder(viewfinder);

// Aimer — a crosshair-style aim point (frameColor / dotColor configurable):
await overlay.setViewfinder(new AimerViewfinder());

// Laserline — a horizontal line (width / enabledColor / disabledColor configurable):
await overlay.setViewfinder(new LaserlineViewfinder());
```

`RectangularViewfinder` exposes `setSize(...)`, `setWidthAndAspectRatio(...)`, `color`, and `dimming`. Pass no arguments (`new RectangularViewfinder()`) for the default `Rounded` + `Light` style.

### Location selection

To restrict scanning to a sub-area of the preview, set `locationSelection` on `BarcodeCaptureSettings`. Only barcodes whose location overlaps the selection area are reported — useful for aiming at one code in a dense layout.

```typescript
import {
    NumberWithUnit,
    MeasureUnit,
    RadiusLocationSelection,
    RectangularLocationSelection,
    SizeWithUnit,
} from "@scandit/web-datacapture-core";

// Rectangular area — e.g. 90% width, 30% height of the view (Fraction units).
settings.locationSelection = RectangularLocationSelection.withSize(
    new SizeWithUnit(
        new NumberWithUnit(0.9, MeasureUnit.Fraction),
        new NumberWithUnit(0.3, MeasureUnit.Fraction)
    )
);

// Circular area centred in the view — e.g. radius of 0.2 of the view.
settings.locationSelection = new RadiusLocationSelection(
    new NumberWithUnit(0.2, MeasureUnit.Fraction)
);
```

`RectangularLocationSelection` also has `withWidthAndAspectRatio(...)` and `withHeightAndAspectRatio(...)`.

### Composite codes

Composite codes (a linear code plus a 2D companion, types CC-A/CC-B/CC-C) require **both** the component symbologies and the composite types to be enabled on `BarcodeCaptureSettings`.

```typescript
import { CompositeType, Symbology } from "@scandit/web-datacapture-barcode";

const settings = new BarcodeCaptureSettings();

// 1. Enable the composite types you want to read.
settings.enabledCompositeTypes = [CompositeType.A, CompositeType.B, CompositeType.C];

// 2. Enable the symbologies that make up those composite types.
settings.enableSymbologiesForCompositeTypes([
    CompositeType.A,
    CompositeType.B,
    CompositeType.C,
]);
```

`enabledCompositeTypes` is a `CompositeType[]` (values `A`, `B`, `C`). `enableSymbologiesForCompositeTypes(...)` turns on the underlying linear + 2D symbologies — calling it is required in addition to setting `enabledCompositeTypes`.

### Symbology extensions

Extensions configure symbology-specific behaviour (e.g. how to treat the leading zero of a UPC-A code, or full-ASCII mode for Code 39). Get the per-symbology `SymbologySettings` with `settings.settingsForSymbology(symbology)`, then call `setExtensionEnabled(name, enabled)`.

```typescript
const code39Settings = settings.settingsForSymbology(Symbology.Code39);
code39Settings.setExtensionEnabled("full_ascii", true);
```

The set of currently enabled extensions is readable via `code39Settings.enabledExtensions` (a `string[]`). See [Symbology Properties](https://docs.scandit.com/symbology-properties) for the extension names per symbology.

### Symbology checksums

Optional checksums add a validation step for symbologies that support them. Set the `checksums` property (a `Set<Checksum>` on web) on the symbology's `SymbologySettings`. The code is accepted if any configured checksum matches, in addition to any mandatory checksum of the symbology.

```typescript
import { Checksum, Symbology } from "@scandit/web-datacapture-barcode";

const code39Settings = settings.settingsForSymbology(Symbology.Code39);
code39Settings.checksums = new Set([Checksum.Mod43]);
```

`Checksum` values include `None`, `Mod10`, `Mod11`, `Mod16`, `Mod43`, `Mod47`, `Mod103`, `Mod10AndMod11`, `Mod10AndMod10`. Only one checksum is applied even if multiple are set.

### Color-inverted codes

By default the engine decodes dark codes on a bright background. To also read bright-on-dark (color-inverted) codes for a symbology, set `isColorInvertedEnabled` on its `SymbologySettings`. The symbology must also be enabled normally.

```typescript
const dataMatrixSettings = settings.settingsForSymbology(Symbology.DataMatrix);
dataMatrixSettings.isColorInvertedEnabled = true;
```

### Active symbol counts

For variable-length symbologies (Code 39, ITF, Code 128, etc.) you can restrict which barcode lengths are accepted. This reduces false positives and can speed up scanning — especially useful when you know the exact length of the barcodes in your use case (e.g., ITF-14 is always 14 characters).

```typescript
// Accept only ITF (Interleaved 2 of 5) barcodes of length 14 (ITF-14)
const itfSettings = settings.settingsForSymbology(Symbology.InterleavedTwoOfFive);
itfSettings.activeSymbolCounts = [14];

// Accept Code 39 barcodes of 6, 7, or 8 characters
const code39Settings = settings.settingsForSymbology(Symbology.Code39);
code39Settings.activeSymbolCounts = [6, 7, 8];
```

Call `settings.settingsForSymbology(symbology)` to get the `SymbologySettings` for that symbology, then set `activeSymbolCounts` to a `number[]` containing the accepted lengths. For fixed-length symbologies (EAN-13, QR Code, DataMatrix) this property has no effect.

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

When scanning is paused (dialog open, scanning panel closed), stop the camera and disable the mode to avoid unnecessary CPU and power consumption:

```typescript
// Pause scanning
await barcodeCapture.setEnabled(false);
await DataCaptureContext.sharedInstance.frameSource?.switchToDesiredState(FrameSourceState.Off);

// Resume scanning
await DataCaptureContext.sharedInstance.frameSource?.switchToDesiredState(FrameSourceState.On);
await barcodeCapture.setEnabled(true);
```

Do not add a `visibilitychange` handler for tab switching. `DataCaptureView` already stops the camera while the page is hidden and resumes it when the page is visible again; a second handler races the SDK's own.

### Cross-origin isolation (COOP / COEP)

`ScanIntention.Smart` and multithreaded SDK processing require `SharedArrayBuffer`, which browsers restrict to [cross-origin isolated](https://developer.mozilla.org/en-US/docs/Web/API/crossOriginIsolated) contexts. Without these headers the SDK falls back to single-threaded mode, which is slower and may reduce scan accuracy.

The headers, the multithreading check and the dialog shown when the check fails are in [Loading the SDK from a CDN](#loading-the-sdk-from-a-cdn); the same two headers apply whether the SDK files come from jsDelivr or are self-hosted. The check also returns `false` on devices with fewer than 2 CPU cores or without nested workers, so an error message should not always blame the headers.

For the complete Vite setup — COOP/COEP middleware, `sdc-lib` self-hosting with `vite-plugin-static-copy`, and license key injection — use the official sample as the source of truth:
<https://github.com/Scandit/datacapture-web-samples/blob/master/01_Single_Scanning_Samples/02_Barcode_Scanning_with_Low-level_API/BarcodeCaptureSimpleSample/vite.config.ts>

Key things to know when adapting it:
- Headers are set via a **Vite middleware**, not `server.headers` — this ensures both the dev server and the preview server send them.
- `sdc-lib` is copied from **both** `@scandit/web-datacapture-core` and `@scandit/web-datacapture-barcode` using `vite-plugin-static-copy`. The `libraryLocation` in your code must match the destination path.
- Use `require-corp` for COEP, whether the SDK is self-hosted or served from the CDN.

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

> **Heads up:** COEP blocks cross-origin resources (images, fonts, iframes, third-party scripts) that do not include `Cross-Origin-Resource-Policy` or `Access-Control-Allow-Origin`. Audit your page's cross-origin dependencies before enabling COEP in production — some third-party embeds (analytics, ads, chat widgets) may stop loading. After changing headers, clear your browser cache and restart the dev server.

---

## Key Rules

1. **Await everything** — `DataCaptureContext.forLicenseKey`, `BarcodeCapture.forContext`, `DataCaptureView.forContext`, `BarcodeCaptureOverlay.withBarcodeCaptureForView`, `camera.applySettings`, `setFrameSource`, `switchToDesiredState`, and `setEnabled` are all async. Forgetting an `await` causes silent failures.
2. **Use `sharedInstance`** — after `DataCaptureContext.forLicenseKey()`, reference the context via `DataCaptureContext.sharedInstance`, not a captured return value. `forLicenseKey()` is idempotent: it returns the shared instance once ready, waits for an initialization already in flight, and retries after a failure. `sharedInstance` is never `null`, so it cannot tell whether the context is initialized: await `forLicenseKey()` for that.
3. **Disable inside `didScan`** — call `await barcodeCapture.setEnabled(false)` before doing any non-trivial work to avoid duplicate scans.
4. **Listener name** — the callback is `didScan`, not `onBarcodeScanned` (that is the Android name).
5. **`codeDuplicateFilter` is a number** — set it to an integer (milliseconds), not a `TimeInterval` object.
6. **Mount point dimensions** — the element passed to `view.connectToElement()` must have non-zero width and height and a set `position` (fixed or absolute). Zero-sized containers silently break the preview.
7. **Camera lifecycle** — turn the camera off with `FrameSourceState.Off` when the scanning surface is closed. Do not handle `visibilitychange`: `DataCaptureView` already stops the camera while the page is hidden.
8. **Overlay is explicit** — `BarcodeCaptureOverlay.withBarcodeCaptureForView(barcodeCapture, view)` adds the overlay to the view. There is no implicit overlay.
9. **Symbologies** — enable only what's needed; each extra symbology adds processing time. Verify symbology names against the API reference — web uses camelCase (e.g. `Symbology.EAN13UPCA`, `Symbology.Code128`).
10. **Active symbol counts** — for variable-length codes (Code 39, ITF, Code 128), always set `activeSymbolCounts` to the exact lengths you expect. Accepting all lengths increases false-positive risk.
11. **Scan intention and cross-origin isolation** — `ScanIntention.Smart` requires `SharedArrayBuffer`. If you enable it, serve the page with `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp` (self-hosted or CDN), otherwise the SDK silently degrades to single-threaded mode. The default is `ScanIntention.Manual`.
