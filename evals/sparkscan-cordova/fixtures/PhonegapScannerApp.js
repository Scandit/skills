// Existing Cordova stock-count screen using phonegap-plugin-barcodescanner
// (cordova-plugin-barcodescanner). It scans EAN-13, UPC-A and Code 128, adds each
// new code to a list and bumps the quantity when a code is scanned again. It has
// a torch button and a Clear button. To be migrated to Scandit SparkScan.
//
// Plugin: cordova plugin add phonegap-plugin-barcodescanner
// API:    cordova.plugins.barcodeScanner.scan(success, error, options)

const items = [];

function renderItems() {
  const listEl = document.getElementById('item-list');
  if (!listEl) return;
  listEl.innerHTML = '';
  items.forEach((item) => {
    const li = document.createElement('li');
    li.textContent = `${item.text} (${item.format}) x${item.quantity}`;
    listEl.appendChild(li);
  });
  const total = items.reduce((sum, item) => sum + item.quantity, 0);
  const totalEl = document.getElementById('total');
  if (totalEl) totalEl.textContent = `Total items: ${total}`;
}

function startScan() {
  cordova.plugins.barcodeScanner.scan(
    function (result) {
      if (result.cancelled) {
        return;
      }
      const existing = items.find((item) => item.text === result.text);
      if (existing) {
        existing.quantity += 1;
      } else {
        items.push({ text: result.text, format: result.format, quantity: 1 });
      }
      renderItems();
      startScan();
    },
    function (error) {
      alert('Scanning failed: ' + error);
    },
    {
      preferFrontCamera: false,
      showFlipCameraButton: false,
      showTorchButton: true,
      formats: 'EAN_13,UPC_A,CODE_128',
      prompt: 'Scan the item barcode',
    }
  );
}

document.addEventListener('deviceready', () => {
  document.getElementById('scan-button').addEventListener('click', startScan);
  document.getElementById('clear-button').addEventListener('click', () => {
    items.length = 0;
    renderItems();
  });
}, false);
