// Basic MatrixScan Count integration already in place.
// Evals in this group add features on top of this baseline (capture lists,
// custom brushes, status mode, hardware trigger, etc.).

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

  camera = Camera.withSettings(BarcodeCount.recommendedCameraSettings);
  await context.setFrameSource(camera);

  const settings = new BarcodeCountSettings();
  settings.enableSymbologies([
    Symbology.EAN13UPCA,
    Symbology.EAN8,
    Symbology.Code128,
    Symbology.QR,
  ]);

  window.barcodeCount = new BarcodeCount(settings);
  context.addMode(window.barcodeCount);

  window.barcodeCount.addListener({
    didScan: async (barcodeCount, session) => {
      const barcodes = session.recognizedBarcodes;
      console.log(`Scanned ${barcodes.length} barcode(s)`);
    },
  });

  window.barcodeCountView = new BarcodeCountView({
    context,
    barcodeCount: window.barcodeCount,
    style: BarcodeCountViewStyle.Icon,
  });

  window.barcodeCountView.uiListener = {
    didTapListButton: (_view) => {
      console.log('List button tapped');
    },
    didTapExitButton: (_view) => {
      console.log('Exit button tapped');
    },
  };

  window.barcodeCountView.connectToElement(document.getElementById('data-capture-view'));

  camera.switchToDesiredState(FrameSourceState.On);
  window.barcodeCount.isEnabled = true;
}

async function uninitializeSDK() {
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

window.addEventListener('load', async () => {
  await ScanditCaptureCorePlugin.initializePlugins();
  await initializeSDK();
});
