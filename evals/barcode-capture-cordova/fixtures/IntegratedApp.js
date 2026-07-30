// Basic BarcodeCapture integration already in place (Cordova, v8 API).
// Evals in this group add features on top of this baseline (custom feedback,
// custom trigger button, viewfinder, lifecycle teardown, duplicate filter, etc.).

// @ts-check

let context;
let camera = null;
let barcodeCapture = null;
let view = null;
let overlay = null;
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

function setupBarcodeCapture() {
  if (barcodeCapture && view) return;

  context = Scandit.DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  camera = Scandit.Camera.default;
  camera.applySettings(Scandit.BarcodeCapture.recommendedCameraSettings);
  context.setFrameSource(camera);

  const settings = new Scandit.BarcodeCaptureSettings();
  settings.enableSymbologies([
    Scandit.Symbology.EAN13UPCA,
    Scandit.Symbology.Code128,
    Scandit.Symbology.QR,
  ]);

  barcodeCapture = new Scandit.BarcodeCapture(settings);
  context.setMode(barcodeCapture);

  barcodeCapture.addListener({
    didScan: (_barcodeCapture, session, _getFrameData) => {
      const barcode = session.newlyRecognizedBarcode;
      if (!barcode) return;
      scannedProducts.push({ data: barcode.data, symbology: barcode.symbology });
      renderProductList();
    },
  });

  view = Scandit.DataCaptureView.forContext(context);
  view.connectToElement(document.getElementById('data-capture-view'));

  overlay = new Scandit.BarcodeCaptureOverlay(barcodeCapture);
  view.addOverlay(overlay);

  camera.switchToDesiredState(Scandit.FrameSourceState.On);
  barcodeCapture.isEnabled = true;
}

document.addEventListener('deviceready', () => {
  setupBarcodeCapture();
}, false);
