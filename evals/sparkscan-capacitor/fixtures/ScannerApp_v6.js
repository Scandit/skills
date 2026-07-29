// Pre-migration v6 SparkScan Capacitor integration.
// Uses v6 API surface: DataCaptureContext.forLicenseKey, SparkScan.forSettings,
// and v6 SparkScanView property names.

import {
  DataCaptureContext,
  ScanditCaptureCorePlugin,
  Color,
} from 'scandit-capacitor-datacapture-core';

import {
  SparkScan,
  SparkScanSettings,
  SparkScanView,
  Symbology,
} from 'scandit-capacitor-datacapture-barcode';

async function runApp() {
  await ScanditCaptureCorePlugin.initializePlugins();

  const context = DataCaptureContext.forLicenseKey('YOUR_LICENSE_KEY');

  const settings = new SparkScanSettings();
  settings.enableSymbologies([
    Symbology.EAN13UPCA,
    Symbology.Code128,
    Symbology.QR,
  ]);

  window.sparkScan = SparkScan.forSettings(settings);
  window.sparkScan.addListener({
    didScan: (_sparkScan, session) => {
      const barcode = session.newlyRecognizedBarcodes && session.newlyRecognizedBarcodes[0];
      if (barcode) {
        console.log('Scanned:', barcode.data);
      }
    },
  });

  window.sparkScanView = SparkScanView.forContext(context, window.sparkScan);

  // v6 properties — all of these need migration to v7.
  window.sparkScanView.torchButtonVisible = true;
  window.sparkScanView.fastFindButtonVisible = true;
  window.sparkScanView.handModeButtonVisible = false;
  window.sparkScanView.soundModeButtonVisible = false;
  window.sparkScanView.hapticModeButtonVisible = false;
  window.sparkScanView.shouldShowScanAreaGuides = false;
  window.sparkScanView.captureButtonBackgroundColor = Color.fromHex('#FF5500');
  window.sparkScanView.captureButtonActiveBackgroundColor = Color.fromHex('#AA3300');
  window.sparkScanView.captureButtonTintColor = Color.fromHex('#FFFFFF');
  window.sparkScanView.startCapturingText = 'START';
  window.sparkScanView.stopCapturingText = 'STOP';
  window.sparkScanView.resumeCapturingText = 'RESUME';
  window.sparkScanView.scanningCapturingText = 'SCANNING';
}

document.addEventListener('DOMContentLoaded', () => {
  runApp();
});
