// Setup checklist:
// 1. Install packages: npm install @scandit/web-datacapture-core @scandit/web-datacapture-barcode
// 2. Set cross-origin headers on the server:
//      Cross-Origin-Opener-Policy: same-origin
//      Cross-Origin-Embedder-Policy: require-corp  (self-hosted) or  credentialless  (CDN)
// 3. Configure libraryLocation to point to the SDK engine files
// 4. Replace '-- ENTER YOUR SCANDIT LICENSE KEY HERE --' with your key from https://ssl.scandit.com
// 5. Add a container element to your HTML:
//      <div id="barcode-ar-view" style="position:fixed;inset:0"></div>

import {
  BarcodeAr,
  BarcodeArSettings,
  BarcodeArView,
  BarcodeArCircleHighlight,
  BarcodeArCircleHighlightPreset,
  barcodeCaptureLoader,
  Symbology,
} from "@scandit/web-datacapture-barcode";
import { DataCaptureContext } from "@scandit/web-datacapture-core";

async function run(): Promise<void> {
  // Step 1: Initialize context — forLicenseKey() sets DataCaptureContext.sharedInstance as a side effect
  await DataCaptureContext.forLicenseKey(
    "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
    {
      libraryLocation: new URL("library/engine/", document.baseURI).toString(),
      moduleLoaders: [barcodeCaptureLoader()],
    }
  );

  // Step 2: Configure BarcodeArSettings — enable only the symbologies needed
  const settings = new BarcodeArSettings();
  settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.Code128]);

  // Step 3: Create BarcodeAr mode (async — always await)
  const barcodeAr = await BarcodeAr.forContext(DataCaptureContext.sharedInstance, settings);

  // Step 4: Create BarcodeArView (async — always await)
  // BarcodeArView manages the camera internally — do NOT set up Camera or setFrameSource manually.
  // No DataCaptureView is needed; BarcodeArView.create() replaces it entirely.
  const container = document.getElementById("barcode-ar-view")!;
  const barcodeArView = await BarcodeArView.create(container, DataCaptureContext.sharedInstance, barcodeAr);

  // Step 5: Assign a highlight provider — shows a circle over each tracked barcode.
  // IMPORTANT (web): use the callback pattern — deliver results via callback(highlight).
  // Do NOT return the value (that is the React Native pattern).
  barcodeArView.highlightProvider = {
    async highlightForBarcode(barcode, callback) {
      const highlight = BarcodeArCircleHighlight.create(barcode, BarcodeArCircleHighlightPreset.Dot);
      callback(highlight);
    },
  };

  // Step 6: Start scanning — the view does NOT start automatically after create()
  await barcodeArView.start();
}

run();
