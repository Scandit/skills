// Basic MatrixScan Batch integration already in place.
// Evals in this group add features on top of this baseline
// (custom brushes, AR overlays, lifecycle handling, etc.).

document.addEventListener('deviceready', () => {
  const context = Scandit.DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  const cameraSettings = Scandit.BarcodeBatch.createRecommendedCameraSettings();
  window.camera = Scandit.Camera.withSettings(cameraSettings);
  context.setFrameSource(window.camera);

  const settings = new Scandit.BarcodeBatchSettings();
  settings.enableSymbologies([
    Scandit.Symbology.EAN13UPCA,
    Scandit.Symbology.EAN8,
    Scandit.Symbology.Code128,
  ]);

  window.barcodeBatch = new Scandit.BarcodeBatch(settings);
  context.setMode(window.barcodeBatch);

  window.barcodeBatch.addListener({
    didUpdateSession: (barcodeBatch, session) => {
      const allTracked = Object.values(session.trackedBarcodes);
      console.log('Tracking ' + allTracked.length + ' barcode(s)');
    },
  });

  window.view = Scandit.DataCaptureView.forContext(context);
  window.view.connectToElement(document.getElementById('data-capture-view'));

  window.basicOverlay = new Scandit.BarcodeBatchBasicOverlay(
    window.barcodeBatch,
    Scandit.BarcodeBatchBasicOverlayStyle.Frame,
  );
  window.view.addOverlay(window.basicOverlay);

  window.camera.switchToDesiredState(Scandit.FrameSourceState.On);
  window.barcodeBatch.isEnabled = true;
}, false);

async function uninitialize() {
  if (window.camera) {
    await window.camera.switchToDesiredState(Scandit.FrameSourceState.Off);
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
