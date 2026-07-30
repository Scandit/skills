import {
    type Barcode,
    barcodeCaptureLoader,
    SparkScan,
    SparkScanBarcodeErrorFeedback,
    SparkScanBarcodeSuccessFeedback,
    type SparkScanFeedbackDelegate,
    type SparkScanSession,
    SparkScanSettings,
    SparkScanView,
    SparkScanViewSettings,
    Symbology,
} from "@scandit/web-datacapture-barcode";
import { DataCaptureContext } from "@scandit/web-datacapture-core";

async function run() {
    await DataCaptureContext.forLicenseKey(
        "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
        {
            libraryLocation: new URL("self-hosted-scandit-sdc-lib", document.baseURI).toString(),
            moduleLoaders: [barcodeCaptureLoader()],
        }
    );

    const settings: SparkScanSettings = new SparkScanSettings();
    settings.enableSymbologies([
        Symbology.EAN13UPCA,
        Symbology.Code128,
        Symbology.QR,
    ]);

    const sparkScan: SparkScan = SparkScan.forSettings(settings);

    const sparkScanListener = {
        didScan: (sparkScan: SparkScan, session: SparkScanSession) => {
            const barcode = session.newlyRecognizedBarcode;
            if (barcode) {
                console.log("Scanned", barcode.symbology, barcode.data);
            }
        },
    };
    sparkScan.addListener(sparkScanListener);

    const sparkScanViewSettings = new SparkScanViewSettings();

    document.body.style.cssText = "position: fixed; top: 0; left: 0; width: 100%; height: 100%;";

    const sparkScanView = SparkScanView.forElement(
        document.body,
        DataCaptureContext.sharedInstance,
        sparkScan,
        sparkScanViewSettings
    );

    const feedbackDelegate: SparkScanFeedbackDelegate = {
        getFeedbackForBarcode: (barcode: Barcode) => {
            if (barcode.data === "5901234123457") {
                return new SparkScanBarcodeErrorFeedback("Invalid barcode.", 60_000);
            } else {
                return new SparkScanBarcodeSuccessFeedback();
            }
        },
    };

    sparkScanView.feedbackDelegate = feedbackDelegate;

    async function mount() {
        await sparkScanView.prepareScanning();
    }

    async function unmount() {
        sparkScan.removeListener(sparkScanListener);
        await sparkScanView.stopScanning();
    }

    return mount().catch(async (error) => {
        console.error(error);
        await unmount();
    });
}

run();
