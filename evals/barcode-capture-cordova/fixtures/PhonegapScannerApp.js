// Existing Cordova app using phonegap-plugin-barcodescanner
// (cordova-plugin-barcodescanner). To be migrated to Scandit BarcodeCapture.
//
// Plugin: cordova plugin add phonegap-plugin-barcodescanner
// API:    cordova.plugins.barcodeScanner.scan(success, error, options)

const scannedItems = [];

function renderItems() {
  const listEl = document.getElementById('item-list');
  if (!listEl) return;
  listEl.innerHTML = '';
  scannedItems.forEach((item, index) => {
    const li = document.createElement('li');
    li.textContent = `${index + 1}. ${item.text} (${item.format})`;
    listEl.appendChild(li);
  });
  const countEl = document.getElementById('count');
  if (countEl) countEl.textContent = `Scanned: ${scannedItems.length}`;
}

function startScan() {
  cordova.plugins.barcodeScanner.scan(
    function (result) {
      if (result.cancelled) {
        return;
      }
      // Deduplicate: ignore a code we've already scanned.
      const alreadyScanned = scannedItems.some((item) => item.text === result.text);
      if (alreadyScanned) {
        return;
      }
      scannedItems.push({ text: result.text, format: result.format });
      renderItems();
    },
    function (error) {
      alert('Scanning failed: ' + error);
    },
    {
      preferFrontCamera: false,
      showFlipCameraButton: true,
      showTorchButton: true,
      formats: 'QR_CODE,EAN_13,CODE_128,UPC_A',
      prompt: 'Place a barcode inside the scan area',
    }
  );
}

document.addEventListener('deviceready', () => {
  const scanButton = document.getElementById('scan-button');
  if (scanButton) {
    scanButton.addEventListener('click', startScan);
  }
}, false);
