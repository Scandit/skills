import type {
    Barcode,
    SparkScanBarcodeFeedback,
    SparkScanFeedbackDelegate,
    SparkScanSession,
} from "@scandit/web-datacapture-barcode";
import {
    SparkScan,
    SparkScanBarcodeErrorFeedback,
    SparkScanBarcodeSuccessFeedback,
    SparkScanSettings,
    SparkScanView,
    SparkScanViewSettings,
    Symbology,
    barcodeCaptureLoader,
} from "@scandit/web-datacapture-barcode";
import type { FrameData } from "@scandit/web-datacapture-core";
import { DataCaptureContext } from "@scandit/web-datacapture-core";

interface ScannedItem {
    data: string;
    symbology: string;
    quantity: number;
}

export class AppController implements SparkScanFeedbackDelegate {
    private readonly scannedItems: Map<string, ScannedItem> = new Map();

    private dataCaptureContext?: DataCaptureContext;

    private sparkScanSettings?: SparkScanSettings;

    private sparkScan?: SparkScan;

    private sparkScanViewSettings?: SparkScanViewSettings;

    private sparkScanView?: SparkScanView;

    public async connect(): Promise<void> {
        // Enter your Scandit License key here.
        // Your Scandit License key is available via your Scandit SDK web account.
        await DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --", {
            libraryLocation: new URL("library/engine", document.baseURI).toString(),
            moduleLoaders: [barcodeCaptureLoader()],
        });
        this.sparkScanSettings = new SparkScanSettings();
        this.sparkScanSettings.enableSymbologies([Symbology.EAN13UPCA, Symbology.Code128]);
        this.sparkScan = SparkScan.forSettings(this.sparkScanSettings);
        this.sparkScanViewSettings = new SparkScanViewSettings();
        this.sparkScanView = SparkScanView.forElement(
            document.getElementById("spark-scan-ui")!,
            DataCaptureContext.sharedInstance,
            this.sparkScan,
            this.sparkScanViewSettings
        );
        this.sparkScanView.feedbackDelegate = this;
        this.sparkScan.addListener(this);
        await this.sparkScanView.prepareScanning();
        this.renderList();
    }

    public async disconnect(): Promise<void> {
        this.sparkScan?.removeListener(this);
        await this.sparkScanView?.stopScanning();
        await this.dataCaptureContext?.dispose();
    }

    public isBarcodeRejected(barcode: Barcode): boolean {
        return barcode.data === "5901234123457";
    }

    public getFeedbackForBarcode(barcode: Barcode): SparkScanBarcodeFeedback {
        if (this.isBarcodeRejected(barcode)) {
            return new SparkScanBarcodeErrorFeedback("Barcode rejected.", 60_000);
        }
        return new SparkScanBarcodeSuccessFeedback();
    }

    public clearList(): void {
        this.scannedItems.clear();
        this.renderList();
    }

    public didScan(_sparkScan: SparkScan, session: SparkScanSession, _frameData: FrameData): void {
        const barcode = session.newlyRecognizedBarcode;
        if (!barcode || this.isBarcodeRejected(barcode)) {
            return;
        }
        const itemId = `${barcode.symbology}-${barcode.data ?? ""}`;
        const existing = this.scannedItems.get(itemId);
        if (existing) {
            existing.quantity++;
        } else {
            this.scannedItems.set(itemId, {
                data: barcode.data ?? "",
                symbology: barcode.symbology,
                quantity: 1,
            });
        }
        this.renderList();
    }

    private renderList(): void {
        const listElement = document.getElementById("scanned-items-list")!;
        const countElement = document.getElementById("scanned-items-count")!;
        countElement.textContent = `Total: ${this.scannedItems.size} items`;
        const fragment = document.createDocumentFragment();
        for (const [, item] of this.scannedItems) {
            const li = document.createElement("li");
            li.textContent = `${item.data} (${item.symbology}) x${item.quantity}`;
            fragment.appendChild(li);
        }
        listElement.replaceChildren(fragment);
    }
}
