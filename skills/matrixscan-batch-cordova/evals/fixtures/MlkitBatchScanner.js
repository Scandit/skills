// Legacy multi-barcode scanning using a Cordova ML Kit barcode plugin
// (cordova-plugin-mlkit-barcode-scanner style). The plugin runs a continuous
// scanner that returns ALL barcodes visible in each frame, which the app
// filters by format and accumulates into a dedup-by-value list.
//
// We want to replace this with Scandit MatrixScan Batch (BarcodeBatch).

// Formats this app cares about (ML Kit numeric format constants).
const MLKIT_FORMAT_EAN_13 = 32;
const MLKIT_FORMAT_CODE_128 = 1;
const MLKIT_FORMAT_QR_CODE = 256;

const wantedFormats = [
  MLKIT_FORMAT_EAN_13,
  MLKIT_FORMAT_CODE_128,
  MLKIT_FORMAT_QR_CODE,
];

// Accumulated results, deduplicated by the decoded string value.
const scannedValues = new Set();
const scannedBarcodes = [];

function addBarcode(displayValue, format) {
  if (scannedValues.has(displayValue)) {
    return; // already seen this value — skip duplicate
  }
  scannedValues.add(displayValue);
  scannedBarcodes.push({ value: displayValue, format: format });
  renderList(scannedBarcodes);
}

function renderList(list) {
  const el = document.getElementById('results');
  el.innerHTML = list.map(b => `<li>${b.value}</li>`).join('');
}

document.addEventListener('deviceready', () => {
  // Continuous multi-barcode scan loop via the ML Kit plugin.
  window.cordova.plugins.mlkit.barcodeScanner.scan(
    {
      formats: wantedFormats,
      detectorSize: 0.6,
    },
    (results) => {
      // results.barcodes: every barcode detected in the current frame.
      results.barcodes.forEach((barcode) => {
        if (wantedFormats.indexOf(barcode.format) !== -1) {
          addBarcode(barcode.displayValue, barcode.format);
        }
      });
    },
    (error) => {
      console.error('ML Kit scan error:', error);
    },
  );
}, false);
