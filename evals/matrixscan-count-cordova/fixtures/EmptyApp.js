// Entry point for the Cordova app. The MatrixScan Count (BarcodeCount) integration should go here.
// Loaded from index.html via <script src="index.js"></script> after cordova.js.
// Plugin minimum version: scandit-cordova-datacapture-barcode 6.24 for BarcodeCount.
// Use plugin >=7.6 for the context-free constructor (new Scandit.BarcodeCount(settings)).

function setupEventListeners() {
  // TODO: integrate MatrixScan Count (BarcodeCount) here.
}

document.addEventListener('deviceready', () => {
  setupEventListeners();
}, false);
