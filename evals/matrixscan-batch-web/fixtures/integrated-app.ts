import {
    BarcodeBatch,
    BarcodeBatchAdvancedOverlay,
    BarcodeBatchSettings,
    barcodeCaptureLoader,
    Symbology,
    TrackedBarcodeView,
} from "@scandit/web-datacapture-barcode";
import {
    Anchor,
    Camera,
    DataCaptureContext,
    DataCaptureView,
    FrameSourceState,
    MeasureUnit,
    NumberWithUnit,
    PointWithUnit,
} from "@scandit/web-datacapture-core";

async function run(): Promise<void> {
    const view = new DataCaptureView();
    view.connectToElement(document.getElementById("data-capture-view")!);
    view.showProgressBar();

    const context = await DataCaptureContext.forLicenseKey(
        "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
        {
            libraryLocation: new URL("library/engine/", document.baseURI).toString(),
            moduleLoaders: [barcodeCaptureLoader()],
        }
    );
    await view.setContext(context);
    view.hideProgressBar();

    const settings = new BarcodeBatchSettings();
    settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.EAN8, Symbology.Code128]);

    const barcodeBatch = await BarcodeBatch.forContext(context, settings);

    barcodeBatch.addListener({
        didUpdateSession: (_mode, session) => {
            for (const trackedBarcode of Object.values(session.trackedBarcodes)) {
                console.log("Tracking:", trackedBarcode.barcode.data);
            }
            for (const id of session.removedTrackedBarcodes) {
                console.log("Removed:", Number.parseInt(id, 10));
            }
        },
    });

    const camera = Camera.pickBestGuess();
    await camera.applySettings(BarcodeBatch.recommendedCameraSettings);
    await context.setFrameSource(camera);

    const advancedOverlay = await BarcodeBatchAdvancedOverlay.withBarcodeBatchForView(barcodeBatch, view);

    advancedOverlay.listener = {
        viewForTrackedBarcode: (_overlay, trackedBarcode) => {
            const el = document.createElement("div");
            el.textContent = trackedBarcode.barcode.data ?? "";
            el.style.cssText =
                "background:#2196F3;color:#fff;padding:4px 8px;border-radius:4px;font-size:12px;";
            return TrackedBarcodeView.withHTMLElement(el, { scale: 1 / window.devicePixelRatio });
        },
        anchorForTrackedBarcode: () => Anchor.TopCenter,
        offsetForTrackedBarcode: () =>
            new PointWithUnit(
                new NumberWithUnit(0, MeasureUnit.Fraction),
                new NumberWithUnit(-1, MeasureUnit.Fraction)
            ),
        didTapViewForTrackedBarcode: (_overlay, trackedBarcode) => {
            console.log("AR bubble tapped:", trackedBarcode.barcode.data);
        },
    };

    await context.frameSource?.switchToDesiredState(FrameSourceState.On);
    await barcodeBatch.setEnabled(true);
}

run();
