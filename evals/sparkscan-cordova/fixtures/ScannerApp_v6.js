// Pre-migration v6 SparkScan Cordova integration.
// Uses v6 API surface: DataCaptureContext.forLicenseKey, SparkScan.forSettings,
// and v6 SparkScanView property names.

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
      const barcode = session.newlyRecognizedBarcodes && session.newlyRecognizedBarcodes[0];
      if (barcode) {
        console.log('Scanned:', barcode.data);
      }
    },
  });

  sparkScanView = Scandit.SparkScanView.forContext(context, sparkScan, null);

  // v6 properties — all of these need migration to v7.
  sparkScanView.torchButtonVisible = true;
  sparkScanView.fastFindButtonVisible = true;
  sparkScanView.handModeButtonVisible = false;
  sparkScanView.soundModeButtonVisible = false;
  sparkScanView.hapticModeButtonVisible = false;
  sparkScanView.shouldShowScanAreaGuides = false;
  sparkScanView.captureButtonBackgroundColor = Scandit.Color.fromHex('#FF5500');
  sparkScanView.captureButtonActiveBackgroundColor = Scandit.Color.fromHex('#AA3300');
  sparkScanView.captureButtonTintColor = Scandit.Color.fromHex('#FFFFFF');
  sparkScanView.startCapturingText = 'START';
  sparkScanView.stopCapturingText = 'STOP';
  sparkScanView.resumeCapturingText = 'RESUME';
  sparkScanView.scanningCapturingText = 'SCANNING';
}, false);
