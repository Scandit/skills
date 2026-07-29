// Pre-migration v7 BarcodeCapture Capacitor integration.
// Uses v7 API surface: DataCaptureContext.forLicenseKey (still valid in v7),
// BarcodeCapture.forContext (still valid in v7), BarcodeCaptureOverlay.withBarcodeCaptureForView (still valid in v7).

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

  const cameraSettings = BarcodeCapture.createRecommendedCameraSettings();
  window.camera = Camera.withSettings(cameraSettings);
  context.setFrameSource(window.camera);

  const settings = new BarcodeCaptureSettings();
  settings.enableSymbologies([
    Symbology.EAN13UPCA,
    Symbology.Code128,
    Symbology.QR,
  ]);

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
  window.overlay = BarcodeCaptureOverlay.withBarcodeCaptureForView(window.barcodeCapture, window.view);

  await window.camera.switchToDesiredState(FrameSourceState.On);
}

document.addEventListener('DOMContentLoaded', () => {
  runApp();
});
