import { BrowserMultiFormatReader, type IScannerControls } from "@zxing/browser";
import { BarcodeFormat, DecodeHintType, type Result } from "@zxing/library";

interface InventoryItem {
  code: string;
  format: string;
  quantity: number;
}

const REPEAT_COOLDOWN_MS = 1500;

const items = new Map<string, InventoryItem>();
let controls: IScannerControls | undefined;
let torchOn = false;
let lastCode = "";
let lastScanAt = 0;

const video = document.getElementById("preview") as HTMLVideoElement;
const list = document.getElementById("items") as HTMLUListElement;
const total = document.getElementById("total") as HTMLSpanElement;
const torchButton = document.getElementById("torch") as HTMLButtonElement;
const clearButton = document.getElementById("clear") as HTMLButtonElement;

function render(): void {
  list.replaceChildren(
    ...[...items.values()].map((item) => {
      const row = document.createElement("li");
      row.textContent = `${item.format} ${item.code} × ${item.quantity}`;
      return row;
    }),
  );
  total.textContent = String([...items.values()].reduce((sum, item) => sum + item.quantity, 0));
}

function addCode(code: string, format: string): void {
  const now = Date.now();
  if (code === lastCode && now - lastScanAt < REPEAT_COOLDOWN_MS) {
    return;
  }
  lastCode = code;
  lastScanAt = now;

  const existing = items.get(code);
  if (existing) {
    existing.quantity += 1;
  } else {
    items.set(code, { code, format, quantity: 1 });
  }
  render();
}

export async function startScanner(): Promise<void> {
  const hints = new Map();
  hints.set(DecodeHintType.POSSIBLE_FORMATS, [BarcodeFormat.EAN_13, BarcodeFormat.UPC_A, BarcodeFormat.CODE_128]);
  const reader = new BrowserMultiFormatReader(hints, { delayBetweenScanAttempts: 300 });

  controls = await reader.decodeFromVideoDevice(undefined, video, (result: Result | undefined) => {
    if (!result) {
      return;
    }
    addCode(result.getText(), BarcodeFormat[result.getBarcodeFormat()]);
  });
}

torchButton.addEventListener("click", async () => {
  torchOn = !torchOn;
  await controls?.switchTorch?.(torchOn);
});

clearButton.addEventListener("click", () => {
  items.clear();
  render();
});

window.addEventListener("pagehide", () => controls?.stop());

void startScanner();
