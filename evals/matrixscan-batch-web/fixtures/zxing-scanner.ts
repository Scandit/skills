import { BarcodeFormat, DecodeHintType } from "@zxing/library";
import { BrowserMultiFormatReader } from "@zxing/browser";

// A continuous multi-scan built on ZXing-js: decode one barcode per frame in a
// callback loop and accumulate distinct text values, deduped via a Set<string>.

export interface ScannedBarcode {
  value: string;
  format: string;
}

const scannedBarcodes: ScannedBarcode[] = [];
const seenValues = new Set<string>();

export async function startScanning(videoElement: HTMLVideoElement): Promise<void> {
  const hints = new Map();
  hints.set(DecodeHintType.POSSIBLE_FORMATS, [
    BarcodeFormat.EAN_13,
    BarcodeFormat.UPC_A,
    BarcodeFormat.CODE_128,
    BarcodeFormat.QR_CODE,
  ]);

  const reader = new BrowserMultiFormatReader(hints);

  await reader.decodeFromVideoDevice(undefined, videoElement, (result, _err) => {
    if (!result) {
      return;
    }
    const value = result.getText();
    // Dedupe on the decoded string — the only identity ZXing-js exposes.
    if (seenValues.has(value)) {
      return;
    }
    seenValues.add(value);
    scannedBarcodes.push({
      value,
      format: BarcodeFormat[result.getBarcodeFormat()],
    });
    renderList(scannedBarcodes);
  });
}

declare function renderList(items: ScannedBarcode[]): void;
