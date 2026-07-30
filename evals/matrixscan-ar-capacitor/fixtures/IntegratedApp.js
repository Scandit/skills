// Basic MatrixScan AR integration already in place.
// Evals in this group add features on top of this baseline (info annotations,
// popover annotations, status icon annotations, custom highlights, etc.).

import {
  Camera,
  DataCaptureContext,
  FrameSourceState,
  ScanditCaptureCorePlugin,
  VideoResolution,
  Color,
  Brush,
} from 'scandit-capacitor-datacapture-core';

import {
  BarcodeAr,
  BarcodeArView,
  BarcodeArSettings,
  BarcodeArViewSettings,
  BarcodeArRectangleHighlight,
  Symbology,
} from 'scandit-capacitor-datacapture-barcode';

let context;
let camera;

async function initializeSDK() {
  if (!context) {
    context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
  }

  const cameraSettings = BarcodeAr.createRecommendedCameraSettings();
  cameraSettings.preferredResolution = VideoResolution.UHD4K;
  camera = Camera.withSettings(cameraSettings);
  await context.setFrameSource(camera);

  const settings = new BarcodeArSettings();
  settings.enableSymbologies([
    Symbology.EAN13UPCA,
    Symbology.EAN8,
    Symbology.Code128,
    Symbology.QR,
  ]);

  window.barcodeAr = new BarcodeAr(settings);

  const viewSettings = new BarcodeArViewSettings();

  window.barcodeArView = new BarcodeArView({
    context,
    barcodeAr: window.barcodeAr,
    settings: viewSettings,
    cameraSettings,
  });

  const containerEl = document.getElementById('barcode-ar-view');
  await window.barcodeArView.connectToElement(containerEl);

  window.barcodeArView.highlightProvider = {
    highlightForBarcode: async (barcode) => {
      const highlight = new BarcodeArRectangleHighlight(barcode);
      highlight.brush = new Brush(
        Color.fromHex('#2EC1CE66'),
        Color.fromHex('#2EC1CE'),
        2.0,
      );
      return highlight;
    },
  };

  await camera.switchToDesiredState(FrameSourceState.On);
}

async function uninitializeSDK() {
  if (camera) {
    await camera.switchToDesiredState(FrameSourceState.Off);
    camera = null;
  }
  if (window.barcodeArView) {
    window.barcodeArView.detachFromElement();
    window.barcodeArView = null;
  }
}

window.addEventListener('load', async () => {
  await ScanditCaptureCorePlugin.initializePlugins();
  await initializeSDK();
});
