// MatrixScanSimpleSample — legacy BarcodeBatch integration.
// This file is a migration fixture. Migrate it to the BarcodeAr API.

resetResults();

document.addEventListener('deviceready', () => {
  // Enter your Scandit License key here.
  // Your Scandit License key is available via your Scandit SDK web account.
  const context = Scandit.DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  // Use the world-facing (back) camera and set it as the frame source of the context. The camera is off by
  // default and must be turned on to start streaming frames to the data capture context for recognition.
  const cameraSettings = Scandit.BarcodeBatch.createRecommendedCameraSettings();
  cameraSettings.preferredResolution = Scandit.VideoResolution.FullHD;
  const camera = Scandit.Camera.withSettings(cameraSettings);
  context.setFrameSource(camera);

  // The barcode batch process is configured through barcode batch settings
  // which are then applied to the barcode batch instance that manages barcode batch.
  const settings = new Scandit.BarcodeBatchSettings();

  // The settings instance initially has all types of barcodes (symbologies) disabled. For the purpose of this
  // sample we enable a very generous set of symbologies. In your own app ensure that you only enable the
  // symbologies that your app requires as every additional enabled symbology has an impact on processing times.
  settings.enableSymbologies([
    Scandit.Symbology.EAN13UPCA,
    Scandit.Symbology.EAN8,
    Scandit.Symbology.UPCE,
    Scandit.Symbology.Code39,
    Scandit.Symbology.Code128,
  ]);

  // Create new barcode batch mode with the settings from above.
  const barcodeBatch = new Scandit.BarcodeBatch(settings);

  // Register a listener to get informed whenever a new barcode is tracked.
  barcodeBatch.addListener({
    didUpdateSession: (barcodeBatch, session) => {
      Object.values(session.trackedBarcodes).forEach(trackedBarcode => {
        window.results[trackedBarcode.barcode.data] = trackedBarcode;
      });
    }
  });

  // Add mode to context
  context.setMode(barcodeBatch);

  // To visualize the on-going barcode batch process on screen, setup a data capture view that renders the
  // camera preview. The view must be connected to the data capture context.
  const view = Scandit.DataCaptureView.forContext(context);

  // Connect the data capture view to the HTML element, so it can fill up its size and follow its position.
  view.connectToElement(document.getElementById('data-capture-view'));

  // Add a Barcode Batch overlay to the data capture view to render the tracked barcodes on
  // top of the video preview. This is optional, but recommended for better visual feedback.
  const overlay = new Scandit.BarcodeBatchBasicOverlay(barcodeBatch, Scandit.BarcodeBatchBasicOverlayStyle.Frame);
  view.addOverlay(overlay);

  // Switch camera on to start streaming frames and enable the barcode batch mode.
  // The camera is started asynchronously and will take some time to completely turn on.
  camera.switchToDesiredState(Scandit.FrameSourceState.On);
  barcodeBatch.isEnabled = true;
}, false);

function updateResults() {
  const list = document.getElementById('list');
  list.innerHTML = Object.values(window.results)
    .map(trackedBarcode => {
      const dataHTML = `<p class="barcodeData">${trackedBarcode.barcode.data}</p>`;
      const symbology = new Scandit.SymbologyDescription(trackedBarcode.barcode.symbology);
      const symbologyHTML = `<p class="symbology">${symbology.readableName}</p>`;
      return `<div class="result">${dataHTML}${symbologyHTML}</div>`;
    })
    .join('');
}

function resetResults() {
  window.results = {};
  document.getElementById('scanning').hidden = false;
  document.getElementById('results').hidden = true;
}

function done() {
  updateResults();
  document.getElementById('scanning').hidden = true;
  document.getElementById('results').hidden = false;
}

function scanAgain() {
  resetResults();
}
