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
const photoInput = document.querySelector<HTMLInputElement>("#photo")!;
const photoStatus = document.querySelector<HTMLParagraphElement>("#photo-status")!;
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

async function createDetector(): Promise<BarcodeDetector> {
  if (!("BarcodeDetector" in window)) {
    await import("barcode-detector/polyfill");
  }
  return new BarcodeDetector({ formats: ["ean_13", "ean_8", "upc_a"] });
}

export async function startShelfScan(): Promise<void> {
  const detector = await createDetector();
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

photoInput.addEventListener("change", async () => {
  const file = photoInput.files?.[0];
  if (file == null) {
    return;
  }
  const detector = await createDetector();
  const found = await detector.detect(await createImageBitmap(file));
  for (const barcode of found) {
    addItem(barcode.rawValue, barcode.format);
  }
  photoStatus.textContent = found.length === 0 ? "No barcode found in this photo" : `${found.length} barcode(s) added`;
  photoInput.value = "";
});
