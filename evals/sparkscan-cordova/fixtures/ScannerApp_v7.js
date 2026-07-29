// Pre-migration v7 SparkScan Cordova integration.
// Uses v7 API surface: DataCaptureContext.forLicenseKey (still valid in v7),
// SparkScan.forSettings (still valid in v7), and v7 SparkScanView property names.

let context;
let sparkScan = null;
let sparkScanView = null;

document.addEventListener('deviceready', () => {
  context = Scandit.DataCaptureContext.forLicenseKey('YOUR_LICENSE_KEY');

  const settings = new Scandit.SparkScanSettings();
  settings.enableSymbologies([
    Scandit.Symbology.EAN13UPCA,
    Scandit.Symbology.Code128,
    Scandit.Symbology.QR,
  ]);

  sparkScan = Scandit.SparkScan.forSettings(settings);
  sparkScan.addListener({
    didScan: (_sparkScan, session) => {
      const barcode = session.newlyRecognizedBarcode;
      if (barcode) {
        console.log('Scanned:', barcode.data);
      }
    },
  });

  sparkScanView = Scandit.SparkScanView.forContext(context, sparkScan, null);
  sparkScanView.torchControlVisible = true;
  sparkScanView.barcodeFindButtonVisible = true;
  sparkScanView.triggerButtonCollapsedColor = Scandit.Color.fromHex('#FF5500');
  sparkScanView.triggerButtonExpandedColor = Scandit.Color.fromHex('#FF5500');
  sparkScanView.triggerButtonAnimationColor = Scandit.Color.fromHex('#FF5500');
  sparkScanView.triggerButtonTintColor = Scandit.Color.fromHex('#FFFFFF');
}, false);
