// Entry point for the Cordova app. The BarcodeCapture integration should go here.
// Loaded from index.html via <script src="index.js"></script> after cordova.js.
// The page already has <div id="data-capture-view"></div> sized to the viewport.

function setupEventListeners() {
  // TODO: integrate BarcodeCapture here.
}

document.addEventListener('deviceready', () => {
  setupEventListeners();
}, false);
