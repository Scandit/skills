// MatrixScan Batch integration written against Scandit Capacitor SDK v6,
// which used the legacy BarcodeTracking* class names (later renamed to BarcodeBatch*).

import {
  Camera,
  DataCaptureContext,
  DataCaptureView,
  FrameSourceState,
  ScanditCaptureCorePlugin,
} from 'scandit-capacitor-datacapture-core';

import {
  BarcodeTracking,
  BarcodeTrackingBasicOverlay,
  BarcodeTrackingBasicOverlayStyle,
  BarcodeTrackingSettings,
  Symbology,
} from 'scandit-capacitor-datacapture-barcode';

async function runApp() {
  await ScanditCaptureCorePlugin.initializePlugins();

  // v6 context factory.
  const context = DataCaptureContext.forLicenseKey('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  window.camera = Camera.default;
  context.setFrameSource(window.camera);

  const settings = new BarcodeTrackingSettings();
  settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.Code128]);

  // v6 capture-mode factory.
  window.barcodeTracking = BarcodeTracking.forContext(context, settings);

  window.barcodeTracking.addListener({
    didUpdateSession: (barcodeTracking, session) => {
      const allTracked = Object.values(session.trackedBarcodes);
      console.log(`Tracking ${allTracked.length} barcode(s)`);
    },
  });

  window.view = DataCaptureView.forContext(context);
  window.view.connectToElement(document.getElementById('data-capture-view'));

  window.overlay = BarcodeTrackingBasicOverlay.withBarcodeTrackingForView(
    window.barcodeTracking,
    window.view,
    BarcodeTrackingBasicOverlayStyle.Frame,
  );

  await window.camera.switchToDesiredState(FrameSourceState.On);
  window.barcodeTracking.isEnabled = true;
}

window.addEventListener('load', () => {
  runApp();
});
