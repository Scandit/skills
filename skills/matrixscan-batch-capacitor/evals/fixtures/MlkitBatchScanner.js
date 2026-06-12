// Continuous multi-barcode scanner built on @capacitor-mlkit/barcode-scanning.
// Every visible barcode is reported on the 'barcodesScanned' event; the app
// deduplicates by raw value and accumulates a summary of unique codes.

import {
  BarcodeScanner,
  BarcodeFormat,
} from '@capacitor-mlkit/barcode-scanning';

// Accumulated unique scans, deduplicated by rawValue.
const seen = new Set();
const scanned = [];

let listenerHandle = null;

async function startScanning() {
  // Ask ML Kit to detect only the formats we care about.
  listenerHandle = await BarcodeScanner.addListener(
    'barcodesScanned',
    (event) => {
      for (const barcode of event.barcodes) {
        if (seen.has(barcode.rawValue)) {
          continue;
        }
        seen.add(barcode.rawValue);
        scanned.push({ value: barcode.rawValue, format: barcode.format });
        console.log(`New barcode [${barcode.format}]: ${barcode.rawValue}`);
      }
      renderSummary();
    },
  );

  await BarcodeScanner.startScan({
    formats: [
      BarcodeFormat.Ean13,
      BarcodeFormat.Code128,
      BarcodeFormat.QrCode,
    ],
  });
}

async function stopScanning() {
  await BarcodeScanner.stopScan();
  if (listenerHandle) {
    await listenerHandle.remove();
    listenerHandle = null;
  }
}

function renderSummary() {
  const list = document.getElementById('scanned-list');
  list.innerHTML = '';
  for (const item of scanned) {
    const li = document.createElement('li');
    li.textContent = `${item.value} (${item.format})`;
    list.appendChild(li);
  }
}

document.getElementById('start-btn').addEventListener('click', startScanning);
document.getElementById('stop-btn').addEventListener('click', stopScanning);
