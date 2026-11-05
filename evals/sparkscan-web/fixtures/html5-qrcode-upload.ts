import { Html5Qrcode, Html5QrcodeSupportedFormats } from "html5-qrcode";

const scanner = new Html5Qrcode("reader", {
  formatsToSupport: [Html5QrcodeSupportedFormats.EAN_13, Html5QrcodeSupportedFormats.CODE_128],
  verbose: false,
});

const codes = new Set<string>();
const list = document.getElementById("codes") as HTMLUListElement;
const photoInput = document.getElementById("photo") as HTMLInputElement;
const status = document.getElementById("status") as HTMLParagraphElement;

function addCode(code: string): void {
  if (codes.has(code)) {
    return;
  }
  codes.add(code);
  const row = document.createElement("li");
  row.textContent = code;
  list.append(row);
}

export async function startCamera(): Promise<void> {
  await scanner.start(
    { facingMode: "environment" },
    { fps: 10 },
    (decodedText: string) => addCode(decodedText),
    undefined,
  );
}

photoInput.addEventListener("change", async () => {
  const file = photoInput.files?.[0];
  if (!file) {
    return;
  }
  if (scanner.isScanning) {
    await scanner.stop();
  }
  try {
    addCode(await scanner.scanFile(file, false));
    status.textContent = "";
  } catch {
    status.textContent = "No barcode found in the photo";
  }
  photoInput.value = "";
  await startCamera();
});

void startCamera();
