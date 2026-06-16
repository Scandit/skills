// Existing barcode scanning built on @capacitor-mlkit/barcode-scanning (Google ML Kit).
// The app scans product barcodes, deduplicates them, and renders a running summary.

import {
  BarcodeScanner,
  BarcodeFormat,
  type Barcode,
} from '@capacitor-mlkit/barcode-scanning';

interface ScannedProduct {
  value: string;
  format: string;
}

const scannedProducts: ScannedProduct[] = [];

function renderSummary(): void {
  const listEl = document.getElementById('product-list');
  if (!listEl) return;
  listEl.innerHTML = '';
  scannedProducts.forEach((product, index) => {
    const li = document.createElement('li');
    li.textContent = `${index + 1}. ${product.value} (${product.format})`;
    listEl.appendChild(li);
  });
  const countEl = document.getElementById('count-label');
  if (countEl) countEl.textContent = `Scanned: ${scannedProducts.length}`;
}

function addProduct(barcode: Barcode): void {
  // Deduplicate: ignore a code we have already scanned.
  const exists = scannedProducts.some((p) => p.value === barcode.rawValue);
  if (exists) return;
  scannedProducts.push({ value: barcode.rawValue, format: String(barcode.format) });
  renderSummary();
}

async function startScanning(): Promise<void> {
  const { camera } = await BarcodeScanner.requestPermissions();
  if (camera !== 'granted' && camera !== 'limited') {
    console.error('Camera permission denied');
    return;
  }

  // One-shot scan limited to retail product formats.
  const { barcodes } = await BarcodeScanner.scan({
    formats: [
      BarcodeFormat.Ean13,
      BarcodeFormat.Ean8,
      BarcodeFormat.UpcA,
      BarcodeFormat.Code128,
      BarcodeFormat.QrCode,
    ],
  });

  barcodes.forEach(addProduct);
}

async function startContinuousScanning(): Promise<void> {
  await BarcodeScanner.addListener('barcodesScanned', (result) => {
    result.barcodes.forEach(addProduct);
  });
  await BarcodeScanner.startScan({
    formats: [BarcodeFormat.Ean13, BarcodeFormat.Code128, BarcodeFormat.QrCode],
  });
}

async function stopScanning(): Promise<void> {
  await BarcodeScanner.stopScan();
  await BarcodeScanner.removeAllListeners();
}

document.getElementById('scan-button')?.addEventListener('click', () => {
  startScanning();
});
