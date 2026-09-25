// Pre-migration v6 BarcodeCapture Cordova integration.
// Uses v6 API surface: DataCaptureContext.forLicenseKey, BarcodeCapture.forContext,
// BarcodeCaptureOverlay.withBarcodeCaptureForViewWithStyle + BarcodeCaptureOverlayStyle.Legacy,
// RectangularViewfinderStyle.Legacy, and the v6 BarcodeCapture.recommendedCameraSettings getter.

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

  overlay = Scandit.BarcodeCaptureOverlay.withBarcodeCaptureForViewWithStyle(
    barcodeCapture,
    view,
    Scandit.BarcodeCaptureOverlayStyle.Legacy,
  );
  overlay.viewfinder = new Scandit.RectangularViewfinder(Scandit.RectangularViewfinderStyle.Legacy);

  camera.switchToDesiredState(Scandit.FrameSourceState.On);
  barcodeCapture.isEnabled = true;
}, false);
