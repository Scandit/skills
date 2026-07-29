// Pre-migration v6 BarcodeCapture Capacitor integration.
// Uses v6 API surface: DataCaptureContext.forLicenseKey, BarcodeCapture.forContext,
// BarcodeCaptureOverlay.withBarcodeCaptureForView, and Camera.default.

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

async function runApp() {
  await ScanditCaptureCorePlugin.initializePlugins();

  const context = DataCaptureContext.forLicenseKey('YOUR_LICENSE_KEY');

  window.camera = Camera.default;
  context.setFrameSource(window.camera);

  const settings = new BarcodeCaptureSettings();
  settings.enableSymbologies([
    Symbology.EAN13UPCA,
    Symbology.Code128,
    Symbology.QR,
  ]);

  // v6 factory — both constructs the mode and registers it with the context.
  window.barcodeCapture = BarcodeCapture.forContext(context, settings);

  window.barcodeCapture.addListener({
    didScan: (_barcodeCapture, session) => {
      const barcode = session.newlyRecognizedBarcode;
      if (barcode) {
        console.log('Scanned:', barcode.data);
      }
    },
  });

  window.view = DataCaptureView.forContext(context);
  window.view.connectToElement(document.getElementById('data-capture-view'));

  // v6 factory — both constructs the overlay and adds it to the view.
  window.overlay = BarcodeCaptureOverlay.withBarcodeCaptureForView(window.barcodeCapture, window.view);

  await window.camera.switchToDesiredState(FrameSourceState.On);
}

document.addEventListener('DOMContentLoaded', () => {
  runApp();
});
