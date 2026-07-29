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
    configure,
    DataCaptureContext,
    DataCaptureView,
    FrameSourceState,
} from "@scandit/web-datacapture-core";

async function run() {
    await configure({
        libraryLocation: new URL("sdc-lib", document.baseURI).toString(),
        licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
        moduleLoaders: [barcodeCaptureLoader()],
    });
    const context = await DataCaptureContext.create();

    const settings = new BarcodeCaptureSettings();
    settings.enableSymbologies([
        Symbology.EAN13UPCA,
        Symbology.Code128,
    ]);

    const camera = Camera.pickBestGuess();
    await camera.applySettings(BarcodeCapture.recommendedCameraSettings);
    await context.setFrameSource(camera);

    const barcodeCapture = await BarcodeCapture.forContext(context, settings);

    const barcodeCaptureListener: BarcodeCaptureListener = {
        didScan: async (bc: BarcodeCapture, session: BarcodeCaptureSession) => {
            const barcode = session.newlyRecognizedBarcode;
            if (!barcode) return;
            await bc.setEnabled(false);
            console.log("Scanned", barcode.symbology, barcode.data);
            await bc.setEnabled(true);
        },
    };
    barcodeCapture.addListener(barcodeCaptureListener);

    const captureElement = document.getElementById("capture-element")!;
    captureElement.style.cssText = "position: fixed; top: 0; left: 0; width: 100%; height: 100%;";

    const view = await DataCaptureView.forContext(context);
    view.connectToElement(captureElement);

    await BarcodeCaptureOverlay.withBarcodeCaptureForView(barcodeCapture, view);

    async function mount() {
        await context.frameSource!.switchToDesiredState(FrameSourceState.On);
    }

    async function unmount() {
        barcodeCapture.removeListener(barcodeCaptureListener);
        await context.frameSource!.switchToDesiredState(FrameSourceState.Off);
        view.detachFromElement();
    }

    return mount().catch(async (error) => {
        console.error(error);
        await unmount();
    });
}

run();
