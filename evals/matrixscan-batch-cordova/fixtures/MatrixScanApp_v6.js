// Pre-migration legacy MatrixScan Cordova integration.
// Uses the old BarcodeTracking* API surface (the pre-v7 name for MatrixScan Batch):
//   DataCaptureContext.forLicenseKey, new BarcodeTrackingSettings(),
//   BarcodeTracking.forContext(context, settings),
//   BarcodeTrackingBasicOverlay.withBarcodeTrackingForView(tracking, view),
//   and the BarcodeTrackingListener.didUpdateSession callback.

let context;
let barcodeTracking = null;
let view = null;
let overlay = null;

document.addEventListener('deviceready', () => {
  context = Scandit.DataCaptureContext.forLicenseKey('YOUR_LICENSE_KEY');

  const camera = Scandit.Camera.default;
  context.setFrameSource(camera);

  const settings = new Scandit.BarcodeTrackingSettings();
  settings.enableSymbologies([
    Scandit.Symbology.EAN13UPCA,
    Scandit.Symbology.EAN8,
    Scandit.Symbology.Code128,
  ]);

  barcodeTracking = Scandit.BarcodeTracking.forContext(context, settings);
  barcodeTracking.addListener({
    didUpdateSession: (_barcodeTracking, session) => {
      const allTracked = Object.values(session.trackedBarcodes);
      console.log('Tracking ' + allTracked.length + ' barcode(s)');
    },
  });

  view = Scandit.DataCaptureView.forContext(context);
  view.connectToElement(document.getElementById('data-capture-view'));

  overlay = Scandit.BarcodeTrackingBasicOverlay.withBarcodeTrackingForView(barcodeTracking, view);

  camera.switchToDesiredState(Scandit.FrameSourceState.On);
  barcodeTracking.isEnabled = true;
}, false);
