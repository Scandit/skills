# SparkScan Web Integration Guide

SparkScan is a pre-built scanning UI for high-volume single-scanning workflows.
It overlays a trigger button on top of any screen so users can scan without leaving their workflow.

## Starting from zero? Use the pre-built sample

If the user has no existing app yet, always offer the official sample as the fastest path to a working integration — it already has the correct project structure, dependencies, and best practices in place.

Ask whether they are using React or plain web (TypeScript/JavaScript), then point them to the right sample:

- **Vanilla JS / TypeScript:** <https://github.com/Scandit/datacapture-web-samples/tree/master/01_Single_Scanning_Samples/01_Barcode_Scanning_with_Pre-built_UI/ListBuildingSample>
- **React:** <https://github.com/Scandit/datacapture-web-samples/tree/master/05_Framework_Integration_Samples/SparkScanReactSample>

Tell the user to clone the repo and open the relevant sample folder. Once they have it open, help them:

1. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with their key from <https://ssl.scandit.com>
2. Adjust the enabled symbologies to match their use case (remind them to only enable what they need — fewer symbologies means better performance and accuracy)
3. Run `npm install` (or their package manager of choice) and start the app

Only proceed to the manual integration steps below if the user already has an existing project they need to add SparkScan to.

---

## Adding SparkScan to an existing project

### Prerequisites

- Scandit Data Capture SDK for web — add via npm, pnpm or yarn:
  - `@scandit/web-datacapture-core`: <https://www.npmjs.com/package/@scandit/web-datacapture-core>
  - `@scandit/web-datacapture-barcode`: <https://www.npmjs.com/package/@scandit/web-datacapture-barcode>
  - A valid Scandit license key — sign in at <https://ssl.scandit.com> to generate one (no account? sign up at <https://ssl.scandit.com/dashboard/sign-up?p=test>)

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask which file or component they'd like to integrate SparkScan into. Then write the integration code directly into that file — do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**

1. Add `@scandit/web-datacapture-core` and `@scandit/web-datacapture-barcode` via your package manager: <https://www.npmjs.com/package/@scandit/web-datacapture-core> <https://www.npmjs.com/package/@scandit/web-datacapture-barcode>
2. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from <https://ssl.scandit.com>

The code example below is a basic TypeScript v8 implementation.
If the user is using React, use the React get-started guide and SparkScanReactSample instead (see References).

> **Mount point requirement:** The SparkScan view needs a container with defined dimensions and positioning to render its camera preview and trigger button correctly. If the container has zero or unresolved dimensions, the SparkScan UI will not display.
> - **Vanilla JS:** style the element passed to `SparkScanView.forElement` — e.g. `document.body.style.cssText = "position: fixed; top: 0; left: 0; width: 100%; height: 100%;"`.
> - **React:** wrap `<spark-scan-view>` in a container `<div>` with those styles — e.g. `<div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%' }}>`. The `<spark-scan-view>` element itself does not need the styles.

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
import { DataCaptureContext } from "@scandit/web-datacapture-core";

async function run() {
    
    await DataCaptureContext.forLicenseKey(
        "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
        {
         // or use the cdn https://cdn.jsdelivr.net/npm/@scandit/web-datacapture-barcode@8/sdc-lib/
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
        didScan: (sparkScan, session) => {
            const barcode = session.newlyRecognizedBarcode;
            if (barcode) {
              console.log("Scanned", barcode.symbology, barcode.data);
            }
        },
    };
    sparkScan.addListener(sparkScanListener);

    const sparkScanViewSettings = new SparkScanViewSettings();

    // SparkScan requires the mount element to have defined dimensions and positioning.
    document.body.style.cssText = "position: fixed; top: 0; left: 0; width: 100%; height: 100%;";

    const sparkScanView = SparkScanView.forElement(
      document.body,
      DataCaptureContext.sharedInstance,
      sparkScan,
      sparkScanViewSettings
    );

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
