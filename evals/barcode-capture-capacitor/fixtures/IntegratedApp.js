// Basic BarcodeCapture integration already in place.
// Evals in this group add features on top of this baseline (custom feedback,
// viewfinder, location selection, code duplicate filter, lifecycle disposal, etc.).

import {
  Camera,
  DataCaptureContext,
  DataCaptureView,
  FrameSourceState,
  ScanditCaptureCorePlugin,
} from 'scandit-capacitor-datacapture-core';

import {
  BarcodeCapture,
  BarcodeCaptureOverlay,
  BarcodeCaptureSettings,
  Symbology,
} from 'scandit-capacitor-datacapture-barcode';

const scannedProducts = [];

function renderProductList() {
  const listEl = document.getElementById('product-list');
  if (!listEl) return;
  listEl.innerHTML = '';
  scannedProducts.forEach((product, index) => {
    const li = document.createElement('li');
    li.textContent = `${index + 1}. ${product.data} (${product.symbology})`;
    listEl.appendChild(li);
  });
}

async function runApp() {
  await ScanditCaptureCorePlugin.initializePlugins();

  const context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  const cameraSettings = BarcodeCapture.createRecommendedCameraSettings();
  window.camera = Camera.withSettings(cameraSettings);
  context.setFrameSource(window.camera);

  const settings = new BarcodeCaptureSettings();
  settings.enableSymbologies([
    Symbology.EAN13UPCA,
    Symbology.Code128,
    Symbology.QR,
  ]);

  window.barcodeCapture = new BarcodeCapture(settings);
  context.setMode(window.barcodeCapture);

  window.barcodeCapture.addListener({
    didScan: async (barcodeCapture, session) => {
      const barcode = session.newlyRecognizedBarcode;
      if (!barcode) return;
      barcodeCapture.isEnabled = false;
      scannedProducts.push({ data: barcode.data, symbology: barcode.symbology });
      renderProductList();
      barcodeCapture.isEnabled = true;
    },
  });

  window.view = DataCaptureView.forContext(context);
  window.view.connectToElement(document.getElementById('data-capture-view'));
  window.overlay = new BarcodeCaptureOverlay(window.barcodeCapture);
  window.view.addOverlay(window.overlay);

  await window.camera.switchToDesiredState(FrameSourceState.On);
}

document.addEventListener('DOMContentLoaded', () => {
  runApp();
});
