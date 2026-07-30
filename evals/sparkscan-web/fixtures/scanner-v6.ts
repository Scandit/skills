import {
    barcodeCaptureLoader,
    SparkScan,
    SparkScanSettings,
    SparkScanView,
    SparkScanViewSettings,
    Symbology,
} from "scandit-web-datacapture-barcode";
import { configure, DataCaptureContext } from "scandit-web-datacapture-core";

async function run() {
    await configure({
        libraryLocation: new URL("build/engine", document.baseURI).toString(),
        licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
        moduleLoaders: [barcodeCaptureLoader()],
    });

    const context = await DataCaptureContext.create();

    const settings = new SparkScanSettings();
    settings.enableSymbologies([Symbology.EAN13UPCA]);

    const sparkScan = SparkScan.forSettings(settings);

    sparkScan.addListener({
        didScan: (_sparkScan, session) => {
            const barcode = session.newlyRecognizedBarcode;
            if (barcode) {
                console.log(`Scanned barcode - ${barcode.data}`);
            }
        },
    });

    const viewSettings = new SparkScanViewSettings();
    viewSettings.defaultHandMode = "right";

    const sparkScanView = SparkScanView.forElement(
        document.getElementById("spark-scan-view")!,
        context,
        sparkScan,
        viewSettings
    );

    sparkScanView.isTorchButtonVisible = true;
    sparkScanView.captureButtonBackgroundColor = "#0000FF";
    sparkScanView.captureButtonTintColor = "#FFFFFF";
    sparkScanView.captureButtonActiveBackgroundColor = "#333333";
    sparkScanView.isHandModeButtonVisible = false;
    sparkScanView.isSoundModeButtonVisible = true;
    sparkScanView.isHapticModeButtonVisible = true;
    sparkScanView.stopCapturingText = "Stop";
    sparkScanView.startCapturingText = "Scan";
    sparkScanView.resumeCapturingText = "Resume";
    sparkScanView.scanningCapturingText = "Scanning...";
    sparkScanView.shouldShowScanAreaGuides = true;
    sparkScanView.isFastFindButtonVisible = false;

    await sparkScanView.prepareScanning();
}

run();
