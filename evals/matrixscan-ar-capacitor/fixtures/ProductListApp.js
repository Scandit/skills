// Product list app with basic DOM state management.
// MatrixScan AR needs to be added: newly tracked barcodes should be appended
// to scannedProducts and the list re-rendered on each session update.

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

function runApp() {
  const clearButton = document.getElementById('clear-button');
  if (clearButton) {
    clearButton.addEventListener('click', onClearTapped);
  }
  renderProductList();
}

window.addEventListener('load', () => {
  runApp();
});
