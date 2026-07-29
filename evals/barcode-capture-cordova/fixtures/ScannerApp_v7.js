// Pre-migration v7 BarcodeCapture Cordova integration.
// Uses v7 API surface: DataCaptureContext.forLicenseKey (still valid in v7),
// BarcodeCapture.forContext (still valid in v7),
// BarcodeCaptureOverlay.withBarcodeCaptureForView (still valid in v7),
// and the v7 single newlyRecognizedBarcode property.

let context;
let barcodeCapture = null;
let view = null;
let overlay = null;

document.addEventListener('deviceready', () => {
  context = Scandit.DataCaptureContext.forLicenseKey('YOUR_LICENSE_KEY');

  const camera = Scandit.Camera.default;
  camera.applySettings(Scandit.BarcodeCapture.recommendedCameraSettings);
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
      const barcode = session.newlyRecognizedBarcode;
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
