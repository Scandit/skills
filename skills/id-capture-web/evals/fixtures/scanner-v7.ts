import {
    Camera,
    configure,
    DataCaptureContext,
    DataCaptureView,
    FrameSourceState,
} from "@scandit/web-datacapture-core";
import {
    type CapturedId,
    DriverLicense,
    FullDocumentScanner,
    IdCapture,
    IdCaptureOverlay,
    IdCaptureSettings,
    IdCard,
    idCaptureLoader,
    type Listener,
    Passport,
    Region,
    RejectionReason,
} from "@scandit/web-datacapture-id";

async function run() {
    await configure({
        libraryLocation: new URL("sdc-lib", document.baseURI).toString(),
        licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
        moduleLoaders: [idCaptureLoader({ enableVIZDocuments: true })],
    });
    const context = await DataCaptureContext.create();

    const camera = Camera.default;
    await camera.applySettings(IdCapture.recommendedCameraSettings);
    await context.setFrameSource(camera);

    const settings = new IdCaptureSettings();
    settings.scannerType = new FullDocumentScanner();
    settings.acceptedDocuments = [
        new IdCard(Region.Any),
        new Passport(Region.Any),
        new DriverLicense(Region.Any),
    ];

    const idCapture = await IdCapture.forContext(context, settings);

    const idCaptureListener: Listener = {
        didCaptureId: async (capturedId: CapturedId) => {
            await idCapture.setEnabled(false);
            console.log("Captured", capturedId.fullName, capturedId.documentNumber);
            await idCapture.setEnabled(true);
        },
        didRejectId: async (_capturedId: CapturedId, reason: RejectionReason) => {
            await idCapture.setEnabled(false);
            console.log("Rejected:", reason);
            await idCapture.setEnabled(true);
        },
    };
    idCapture.addListener(idCaptureListener);

    const captureElement = document.getElementById("data-capture-view")!;
    const view = await DataCaptureView.forContext(context);
    view.connectToElement(captureElement);

    await IdCaptureOverlay.withIdCaptureForView(idCapture, view);

    await camera.switchToDesiredState(FrameSourceState.On);
    await idCapture.setEnabled(true);
}

run();
