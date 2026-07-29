// Basic SparkScan integration already in place (Cordova, v8 API).
// Evals in this group add features on top of this baseline (custom feedback,
// custom trigger button, UI customization, lifecycle disposal, etc.).

// @ts-check

let context;
let sparkScan = null;
let sparkScanView = null;
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

function setupSparkScan() {
  if (sparkScan && sparkScanView) return;

  context = Scandit.DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  const settings = new Scandit.SparkScanSettings();
  settings.enableSymbologies([
    Scandit.Symbology.EAN13UPCA,
    Scandit.Symbology.Code128,
    Scandit.Symbology.QR,
  ]);

  sparkScan = new Scandit.SparkScan(settings);
  sparkScan.addListener({
    didScan: async (_sparkScan, session) => {
      const barcode = session.newlyRecognizedBarcode;
      if (!barcode) return;
      scannedProducts.push({ data: barcode.data, symbology: barcode.symbology });
      renderProductList();
    },
  });

  const sparkScanViewSettings = new Scandit.SparkScanViewSettings();
  sparkScanView = Scandit.SparkScanView.forContext(context, sparkScan, sparkScanViewSettings);
}

document.addEventListener('deviceready', () => {
  setupSparkScan();
}, false);
