// Packing-slip / receiving app with basic DOM state management.
// MatrixScan Count needs to be added: after each shutter-press scan,
// the recognized barcodes should be appended to packingList and the list re-rendered.

const packingList = [];

function renderPackingList() {
  const listEl = document.getElementById('packing-list');
  if (!listEl) return;
  listEl.innerHTML = '';
  packingList.forEach((item, index) => {
    const li = document.createElement('li');
    li.textContent = `${index + 1}. ${item.data} (${item.symbology})`;
    listEl.appendChild(li);
  });
  updateTotal();
}

function updateTotal() {
  const totalLabel = document.getElementById('total-label');
  if (!totalLabel) return;
  totalLabel.textContent = `Total scanned: ${packingList.length}`;
}

function onClearTapped() {
  packingList.length = 0;
  renderPackingList();
}

function runApp() {
  const clearButton = document.getElementById('clear-button');
  if (clearButton) {
    clearButton.addEventListener('click', onClearTapped);
  }
  renderPackingList();
}

window.addEventListener('load', () => {
  runApp();
});
