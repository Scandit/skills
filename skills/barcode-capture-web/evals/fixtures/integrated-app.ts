import {
    BarcodeCapture,
    type BarcodeCaptureListener,
    BarcodeCaptureOverlay,
    type BarcodeCaptureSession,
    BarcodeCaptureSettings,
    barcodeCaptureLoader,
    Symbology,
} from "@scandit/web-datacapture-barcode";
import {
    Camera,
    DataCaptureContext,
    DataCaptureView,
    type FrameData,
    FrameSourceState,
} from "@scandit/web-datacapture-core";

async function run() {
    await DataCaptureContext.forLicenseKey(
        "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
        {
            libraryLocation: new URL("self-hosted-scandit-sdc-lib", document.baseURI).toString(),
            moduleLoaders: [barcodeCaptureLoader()],
        }
    );

    const settings = new BarcodeCaptureSettings();
    settings.enableSymbologies([
        Symbology.EAN13UPCA,
        Symbology.Code128,
        Symbology.QR,
    ]);

    const camera = Camera.pickBestGuess();
    await camera.applySettings(BarcodeCapture.recommendedCameraSettings);
    await DataCaptureContext.sharedInstance.setFrameSource(camera);

    const barcodeCapture = await BarcodeCapture.forContext(
        DataCaptureContext.sharedInstance,
        settings
    );

    const barcodeCaptureListener: BarcodeCaptureListener = {
        didScan: async (barcodeCapture: BarcodeCapture, session: BarcodeCaptureSession, frameData: FrameData) => {
            const barcode = session.newlyRecognizedBarcode;
            if (!barcode) return;
            await barcodeCapture.setEnabled(false);
            console.log("Scanned", barcode.symbology, barcode.data);
            await barcodeCapture.setEnabled(true);
        },
    };
    barcodeCapture.addListener(barcodeCaptureListener);

    const captureElement = document.getElementById("capture-element")!;
    captureElement.style.cssText = "position: fixed; top: 0; left: 0; width: 100%; height: 100%;";

    const view = await DataCaptureView.forContext(DataCaptureContext.sharedInstance);
    view.connectToElement(captureElement);

    await BarcodeCaptureOverlay.withBarcodeCaptureForView(barcodeCapture, view);

    async function mount() {
        await DataCaptureContext.sharedInstance.frameSource!.switchToDesiredState(FrameSourceState.On);
    }

    async function unmount() {
        barcodeCapture.removeListener(barcodeCaptureListener);
        await DataCaptureContext.sharedInstance.frameSource!.switchToDesiredState(FrameSourceState.Off);
        view.detachFromElement();
    }

    return mount().catch(async (error) => {
        console.error(error);
        await unmount();
    });
}

run();
