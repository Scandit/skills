// Product list app with basic DOM state management.
// MatrixScan Count (BarcodeCount) needs to be added: barcodes recognized by the count session
// should be appended to scannedProducts and the list re-rendered.
// Plugin minimum version: scandit-cordova-datacapture-barcode 7.6.

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
  updateTotal();
}

function updateTotal() {
  const totalLabel = document.getElementById('total-label');
  if (!totalLabel) return;
  totalLabel.textContent = `Total scanned: ${scannedProducts.length}`;
}

function onClearTapped() {
  scannedProducts.length = 0;
  renderProductList();
}

function setupEventListeners() {
  const clearButton = document.getElementById('clear-button');
  if (clearButton) {
    clearButton.addEventListener('click', onClearTapped);
  }
  renderProductList();
}

document.addEventListener('deviceready', () => {
  setupEventListeners();
}, false);
