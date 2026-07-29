import {
    Camera,
    CameraSwitchControl,
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
    IdCaptureScanner,
    IdCaptureSettings,
    IdCard,
    idCaptureLoader,
    type Listener,
    Passport,
    Region,
    RejectionReason,
} from "@scandit/web-datacapture-id";

async function run() {
    const view = new DataCaptureView();
    view.connectToElement(document.getElementById("data-capture-view")!);
    view.showProgressBar();

    const context = await DataCaptureContext.forLicenseKey(
        "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
        {
            libraryLocation: new URL("library/engine/", document.baseURI).toString(),
            moduleLoaders: [idCaptureLoader({ enableVIZDocuments: true })],
        }
    );
    view.hideProgressBar();

    const camera = Camera.pickBestGuess();
    await camera.applySettings(IdCapture.recommendedCameraSettings);
    await context.setFrameSource(camera);
    await view.setContext(context);
    view.addControl(new CameraSwitchControl());

    const settings = new IdCaptureSettings();
    settings.scanner = new IdCaptureScanner({ physicalDocument: new FullDocumentScanner() });
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

    await IdCaptureOverlay.withIdCaptureForView(idCapture, view);

    async function mount() {
        await idCapture.setEnabled(false);
        await camera.switchToDesiredState(FrameSourceState.On);
        await idCapture.setEnabled(true);
    }

    async function unmount() {
        idCapture.removeListener(idCaptureListener);
        await camera.switchToDesiredState(FrameSourceState.Off);
        view.detachFromElement();
    }

    return mount().catch(async (error) => {
        console.error(error);
        await unmount();
    });
}

run();
