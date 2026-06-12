// MatrixScan Batch integration written against Scandit Capacitor SDK v7.
// Uses the BarcodeBatch* names (renamed from BarcodeTracking* in v7) but still
// uses the v7 context factory (forLicenseKey) and capture-mode factory (forContext).

import {
  Camera,
  DataCaptureContext,
  DataCaptureView,
  FrameSourceState,
  ScanditCaptureCorePlugin,
} from 'scandit-capacitor-datacapture-core';

import {
  BarcodeBatch,
  BarcodeBatchBasicOverlay,
  BarcodeBatchBasicOverlayStyle,
  BarcodeBatchSettings,
  Symbology,
} from 'scandit-capacitor-datacapture-barcode';

async function runApp() {
  await ScanditCaptureCorePlugin.initializePlugins();

  // v7 context factory.
  const context = DataCaptureContext.forLicenseKey('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  window.camera = Camera.default;
  context.setFrameSource(window.camera);

  const settings = new BarcodeBatchSettings();
  settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.Code128]);

  // v7 capture-mode factory.
  window.barcodeBatch = BarcodeBatch.forContext(context, settings);

  window.barcodeBatch.addListener({
    didUpdateSession: (barcodeBatch, session) => {
      const allTracked = Object.values(session.trackedBarcodes);
      console.log(`Tracking ${allTracked.length} barcode(s)`);
    },
  });

  window.view = DataCaptureView.forContext(context);
  window.view.connectToElement(document.getElementById('data-capture-view'));

  window.overlay = new BarcodeBatchBasicOverlay(
    window.barcodeBatch,
    BarcodeBatchBasicOverlayStyle.Frame,
  );
  window.view.addOverlay(window.overlay);

  await window.camera.switchToDesiredState(FrameSourceState.On);
  window.barcodeBatch.isEnabled = true;
}

window.addEventListener('load', () => {
  runApp();
});
