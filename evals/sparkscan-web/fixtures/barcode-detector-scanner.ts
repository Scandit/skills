interface DetectedBarcode {
  rawValue: string;
  format: string;
}

declare class BarcodeDetector {
  constructor(options?: { formats?: string[] });
  static getSupportedFormats(): Promise<string[]>;
  detect(source: ImageBitmapSource): Promise<DetectedBarcode[]>;
}

const FORMATS = ["qr_code", "code_128", "ean_13", "ean_8"];
const SCAN_INTERVAL_MS = 250;

const video = document.querySelector<HTMLVideoElement>("#camera")!;
const scans = document.querySelector<HTMLOListElement>("#scans")!;
const seen = new Set<string>();
let stream: MediaStream | undefined;
let frameRequest = 0;
let lastDetectAt = 0;

async function createDetector(): Promise<BarcodeDetector> {
  if (!("BarcodeDetector" in window)) {
    await import("barcode-detector/polyfill");
  }
  const supported = await BarcodeDetector.getSupportedFormats();
  return new BarcodeDetector({ formats: FORMATS.filter((format) => supported.includes(format)) });
}

function addScan(value: string, format: string): void {
  if (seen.has(value)) {
    return;
  }
  seen.add(value);
  const row = document.createElement("li");
  row.textContent = `${value} (${format})`;
  scans.prepend(row);
  navigator.vibrate?.(100);
}

export async function start(): Promise<void> {
  const detector = await createDetector();
  stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false });
  video.srcObject = stream;
  await video.play();

  const tick = async (now: number): Promise<void> => {
    if (now - lastDetectAt >= SCAN_INTERVAL_MS && video.readyState >= HTMLMediaElement.HAVE_ENOUGH_DATA) {
      lastDetectAt = now;
      const [barcode] = await detector.detect(video);
      if (barcode) {
        addScan(barcode.rawValue, barcode.format);
      }
    }
    frameRequest = requestAnimationFrame((time) => void tick(time));
  };
  frameRequest = requestAnimationFrame((time) => void tick(time));
}

export function stop(): void {
  cancelAnimationFrame(frameRequest);
  stream?.getTracks().forEach((track) => track.stop());
  video.srcObject = null;
}

document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    stop();
  } else {
    void start();
  }
});

void start();
