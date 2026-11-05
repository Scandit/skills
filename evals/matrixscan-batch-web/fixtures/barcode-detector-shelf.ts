interface DetectedBarcode {
  rawValue: string;
  format: string;
  boundingBox: DOMRectReadOnly;
}

declare class BarcodeDetector {
  constructor(options?: { formats?: string[] });
  detect(source: ImageBitmapSource): Promise<DetectedBarcode[]>;
}

interface ShelfItem {
  code: string;
  format: string;
}

const video = document.querySelector<HTMLVideoElement>("#camera")!;
const overlay = document.querySelector<HTMLCanvasElement>("#overlay")!;
const list = document.querySelector<HTMLUListElement>("#items")!;
const items: ShelfItem[] = [];
const seen = new Set<string>();

function addItem(code: string, format: string): void {
  if (seen.has(code)) {
    return;
  }
  seen.add(code);
  items.push({ code, format });
  const row = document.createElement("li");
  row.textContent = `${format} ${code}`;
  list.append(row);
}

export async function startShelfScan(): Promise<void> {
  if (!("BarcodeDetector" in window)) {
    await import("barcode-detector/polyfill");
  }
  const detector = new BarcodeDetector({ formats: ["ean_13", "ean_8", "upc_a"] });
  video.srcObject = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
  await video.play();
  overlay.width = video.videoWidth;
  overlay.height = video.videoHeight;
  const context = overlay.getContext("2d")!;

  const tick = async (): Promise<void> => {
    const barcodes = await detector.detect(video);
    context.clearRect(0, 0, overlay.width, overlay.height);
    context.strokeStyle = "lime";
    for (const barcode of barcodes) {
      const box = barcode.boundingBox;
      context.strokeRect(box.x, box.y, box.width, box.height);
      addItem(barcode.rawValue, barcode.format);
    }
    requestAnimationFrame(() => void tick());
  };
  requestAnimationFrame(() => void tick());
}
