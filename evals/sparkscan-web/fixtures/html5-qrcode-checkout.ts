import { Html5Qrcode, Html5QrcodeSupportedFormats, type Html5QrcodeResult } from "html5-qrcode";

interface Ticket {
  code: string;
  format: string;
}

const resultPanel = document.getElementById("result") as HTMLDivElement;
const scanAgainButton = document.getElementById("scan-again") as HTMLButtonElement;
const torchButton = document.getElementById("torch") as HTMLButtonElement;

const scanner = new Html5Qrcode("reader", {
  formatsToSupport: [Html5QrcodeSupportedFormats.QR_CODE, Html5QrcodeSupportedFormats.EAN_13],
  verbose: false,
});

let current: Ticket | null = null;

async function checkIn(ticket: Ticket): Promise<void> {
  resultPanel.textContent = `Checking ${ticket.code}…`;
  const response = await fetch(`/api/tickets/${encodeURIComponent(ticket.code)}/check-in`, { method: "POST" });
  resultPanel.textContent = response.ok ? `Welcome! (${ticket.format})` : "Ticket not valid";
}

async function onScanSuccess(decodedText: string, decodedResult: Html5QrcodeResult): Promise<void> {
  if (current) {
    return;
  }
  current = { code: decodedText, format: decodedResult.result.format?.formatName ?? "unknown" };
  await scanner.stop();
  scanAgainButton.hidden = false;
  await checkIn(current);
}

export async function startScanner(): Promise<void> {
  current = null;
  scanAgainButton.hidden = true;
  resultPanel.textContent = "";
  await scanner.start(
    { facingMode: "environment" },
    { fps: 10, qrbox: { width: 250, height: 250 } },
    (decodedText: string, decodedResult: Html5QrcodeResult) => void onScanSuccess(decodedText, decodedResult),
    undefined,
  );
}

scanAgainButton.addEventListener("click", () => void startScanner());

torchButton.addEventListener("click", async () => {
  const torch = scanner.getRunningTrackCameraCapabilities().torchFeature();
  if (torch.isSupported()) {
    await torch.apply(!torch.value());
  }
});

void startScanner();
