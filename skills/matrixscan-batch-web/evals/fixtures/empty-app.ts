import {
  Camera,
  DataCaptureContext,
  DataCaptureView,
  FrameSourceState,
} from "@scandit/web-datacapture-core";
import {
  BarcodeBatch,
  BarcodeBatchBasicOverlay,
  BarcodeBatchBasicOverlayStyle,
  BarcodeBatchSettings,
  barcodeCaptureLoader,
  Symbology,
} from "@scandit/web-datacapture-barcode";

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
  settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.Code128]);

  const barcodeBatch = await BarcodeBatch.forContext(context, settings);
  barcodeBatch.addListener({
    didUpdateSession: (_mode, session) => {
      for (const tracked of Object.values(session.trackedBarcodes)) {
        console.log("Tracking:", tracked.barcode.data);
      }
    },
  });

  const camera = Camera.pickBestGuess();
  await camera.applySettings(BarcodeBatch.recommendedCameraSettings);
  await context.setFrameSource(camera);

  await BarcodeBatchBasicOverlay.withBarcodeBatchForViewWithStyle(
    barcodeBatch,
    view,
    BarcodeBatchBasicOverlayStyle.Frame
  );

  await context.frameSource?.switchToDesiredState(FrameSourceState.On);
  await barcodeBatch.setEnabled(true);
}

run();
