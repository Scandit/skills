// Basic SparkScan integration already in place.
// Evals in this group add features on top of this baseline (custom feedback,
// custom trigger button, UI customization, lifecycle disposal, etc.).

import {
  DataCaptureContext,
  ScanditCaptureCorePlugin,
} from 'scandit-capacitor-datacapture-core';

import {
  SparkScan,
  SparkScanSettings,
  SparkScanView,
  Symbology,
} from 'scandit-capacitor-datacapture-barcode';

const scannedProducts = [];

function renderProductList() {
  const listEl = document.getElementById('product-list');
  if (!listEl) return;
  listEl.innerHTML = '';
  scannedProducts.forEach((product, index) => {
    const li = document.createElement('li');
    li.textContent = `${index + 1}. ${product.data} (${product.symbology})`;
    listEl.appendChild(li);
  });
}

async function runApp() {
  await ScanditCaptureCorePlugin.initializePlugins();

  const context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  const settings = new SparkScanSettings();
  settings.enableSymbologies([
    Symbology.EAN13UPCA,
    Symbology.Code128,
    Symbology.QR,
  ]);

  window.sparkScan = new SparkScan(settings);
  window.sparkScan.addListener({
    didScan: (_sparkScan, session) => {
      const barcode = session.newlyRecognizedBarcode;
      if (!barcode) return;
      scannedProducts.push({ data: barcode.data, symbology: barcode.symbology });
      renderProductList();
    },
  });

  window.sparkScanView = SparkScanView.forContext(context, window.sparkScan);
}

document.addEventListener('DOMContentLoaded', () => {
  runApp();
});
