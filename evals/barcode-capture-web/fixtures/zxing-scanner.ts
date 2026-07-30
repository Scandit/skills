import {
    BrowserMultiFormatReader,
    DecodeHintType,
    BarcodeFormat,
    Result,
} from "@zxing/library";

interface ScannedItem {
    text: string;
    format: string;
}

const scannedItems: ScannedItem[] = [];

function renderSummary() {
    const list = document.getElementById("results")!;
    list.innerHTML = scannedItems
        .map((item) => `<li>${item.format}: ${item.text}</li>`)
        .join("");
    document.getElementById("count")!.textContent = String(scannedItems.length);
}

export async function startScanner() {
    // Restrict ZXing to the formats this retail app cares about.
    const hints = new Map();
    hints.set(DecodeHintType.POSSIBLE_FORMATS, [
        BarcodeFormat.EAN_13,
        BarcodeFormat.CODE_128,
        BarcodeFormat.QR_CODE,
    ]);

    const reader = new BrowserMultiFormatReader(hints);
    const videoElement = document.getElementById("video") as HTMLVideoElement;

    await reader.decodeFromVideoDevice(
        null,
        videoElement,
        (result: Result | undefined) => {
            if (!result) return;

            const text = result.getText();
            const format = BarcodeFormat[result.getBarcodeFormat()];

            // Deduplicate: ignore a code we have already recorded.
            if (scannedItems.some((item) => item.text === text)) {
                return;
            }

            scannedItems.push({ text, format });
            renderSummary();
        }
    );

    return () => {
        reader.reset();
    };
}

startScanner().catch(console.error);
