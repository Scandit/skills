// Pre-migration v6 BarcodeCapture Cordova integration.
// Uses v6 API surface: DataCaptureContext.forLicenseKey, BarcodeCapture.forContext,
// BarcodeCaptureOverlay.withBarcodeCaptureForView, and the v6 newlyRecognizedBarcodes array.

let context;
let barcodeCapture = null;
let view = null;
let overlay = null;

document.addEventListener('deviceready', () => {
  context = Scandit.DataCaptureContext.forLicenseKey('YOUR_LICENSE_KEY');

  const camera = Scandit.Camera.default;
  context.setFrameSource(camera);

  const settings = new Scandit.BarcodeCaptureSettings();
  settings.enableSymbologies([
    Scandit.Symbology.EAN13UPCA,
    Scandit.Symbology.Code128,
    Scandit.Symbology.QR,
  ]);

  barcodeCapture = Scandit.BarcodeCapture.forContext(context, settings);
  barcodeCapture.addListener({
    didScan: (_barcodeCapture, session) => {
      const barcode = session.newlyRecognizedBarcodes && session.newlyRecognizedBarcodes[0];
      if (barcode) {
        console.log('Scanned:', barcode.data);
      }
    },
  });

  view = Scandit.DataCaptureView.forContext(context);
  view.connectToElement(document.getElementById('data-capture-view'));

  overlay = Scandit.BarcodeCaptureOverlay.withBarcodeCaptureForView(barcodeCapture, view);

  camera.switchToDesiredState(Scandit.FrameSourceState.On);
  barcodeCapture.isEnabled = true;
}, false);
