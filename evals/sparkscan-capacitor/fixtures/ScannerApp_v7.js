// Pre-migration v7 SparkScan Capacitor integration.
// Uses v7 API surface: DataCaptureContext.forLicenseKey (still valid in v7),
// SparkScan.forSettings (still valid in v7), and v7 SparkScanView property names.

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
      const barcode = session.newlyRecognizedBarcode;
      if (barcode) {
        console.log('Scanned:', barcode.data);
      }
    },
  });

  window.sparkScanView = SparkScanView.forContext(context, window.sparkScan);
  window.sparkScanView.torchControlVisible = true;
  window.sparkScanView.barcodeFindButtonVisible = true;
  window.sparkScanView.triggerButtonCollapsedColor = Color.fromHex('#FF5500');
  window.sparkScanView.triggerButtonExpandedColor = Color.fromHex('#FF5500');
  window.sparkScanView.triggerButtonAnimationColor = Color.fromHex('#FF5500');
  window.sparkScanView.triggerButtonTintColor = Color.fromHex('#FFFFFF');
}

document.addEventListener('DOMContentLoaded', () => {
  runApp();
});
