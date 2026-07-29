import {
    barcodeCaptureLoader,
    SparkScan,
    SparkScanSettings,
    SparkScanView,
    SparkScanViewSettings,
    Symbology,
} from "@scandit/web-datacapture-barcode";
import { configure, DataCaptureContext } from "@scandit/web-datacapture-core";

async function run() {
    await configure({
        libraryLocation: new URL("sdc-lib", document.baseURI).toString(),
        licenseKey: "-- LICENSE KEY --",
        moduleLoaders: [barcodeCaptureLoader()],
    });

    const context = await DataCaptureContext.create();

    const settings = new SparkScanSettings();
    settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.Code128]);

    const sparkScan = SparkScan.forSettings(settings);

    sparkScan.addListener({
        didScan: (_sparkScan, session) => {
            const barcode = session.newlyRecognizedBarcode;
            if (barcode) {
                console.log("Scanned:", barcode.data);
            }
        },
    });

    const sparkScanViewSettings = new SparkScanViewSettings();

    const sparkScanView = SparkScanView.forElement(
        document.getElementById("spark-scan-view")!,
        context,
        sparkScan,
        sparkScanViewSettings
    );

    sparkScanView.isTorchControlVisible = true;
    sparkScanView.triggerButtonCollapsedColor = "#0000FF";
    sparkScanView.triggerButtonExpandedColor = "#0000FF";
    sparkScanView.triggerButtonAnimationColor = "#0000FF";
    sparkScanView.triggerButtonTintColor = "#FFFFFF";
    sparkScanView.isBarcodeFindButtonVisible = false;

    await sparkScanView.prepareScanning();
}

run();
