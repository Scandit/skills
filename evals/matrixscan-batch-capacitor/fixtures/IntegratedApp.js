// Basic MatrixScan Batch integration already in place.
// Evals in this group add features on top of this baseline
// (custom brushes, AR overlays, lifecycle handling, etc.).

import {
  Camera,
  DataCaptureContext,
  DataCaptureView,
  FrameSourceState,
  ScanditCaptureCorePlugin,
  Brush,
  Color,
} from 'scandit-capacitor-datacapture-core';

import {
  BarcodeBatch,
  BarcodeBatchBasicOverlay,
  BarcodeBatchBasicOverlayStyle,
  BarcodeBatchSettings,
  Symbology,
} from 'scandit-capacitor-datacapture-barcode';

let context;

async function runApp() {
  // Initialize plugins — must be first.
  await ScanditCaptureCorePlugin.initializePlugins();

  context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  const cameraSettings = BarcodeBatch.createRecommendedCameraSettings();
  window.camera = Camera.withSettings(cameraSettings);
  context.setFrameSource(window.camera);

  const settings = new BarcodeBatchSettings();
  settings.enableSymbologies([
    Symbology.EAN13UPCA,
    Symbology.EAN8,
    Symbology.Code128,
  ]);

  window.barcodeBatch = new BarcodeBatch(settings);
  context.setMode(window.barcodeBatch);

  window.barcodeBatch.addListener({
    didUpdateSession: async (barcodeBatch, session) => {
      const allTracked = Object.values(session.trackedBarcodes);
      console.log(`Tracking ${allTracked.length} barcode(s)`);
    },
  });

  window.view = DataCaptureView.forContext(context);
  window.view.connectToElement(document.getElementById('data-capture-view'));

  window.basicOverlay = new BarcodeBatchBasicOverlay(
    window.barcodeBatch,
    BarcodeBatchBasicOverlayStyle.Frame,
  );
  window.view.addOverlay(window.basicOverlay);

  await window.camera.switchToDesiredState(FrameSourceState.On);
  window.barcodeBatch.isEnabled = true;
}

async function uninitialize() {
  if (window.camera) {
    await window.camera.switchToDesiredState(FrameSourceState.Off);
    window.camera = null;
  }
  if (window.barcodeBatch) {
    window.barcodeBatch.isEnabled = false;
    window.barcodeBatch = null;
  }
  if (window.view) {
    window.view.detachFromElement();
    window.view = null;
  }
}

window.addEventListener('load', () => {
  runApp();
});
