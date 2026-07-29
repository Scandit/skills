import {
    Camera,
    DataCaptureContext,
    DataCaptureView,
    FrameSourceState,
    ScanditCaptureCorePlugin,
    VideoResolution
} from 'scandit-capacitor-datacapture-core';

import {
    BarcodeBatch,
    BarcodeBatchBasicOverlay,
    BarcodeBatchBasicOverlayStyle,
    BarcodeBatchSettings,
    Symbology,
    SymbologyDescription,
} from 'scandit-capacitor-datacapture-barcode';

async function runApp() {
    let results = {};
    resetResults();

    // Initialize the plugins.
    await ScanditCaptureCorePlugin.initializePlugins();

    // Enter your Scandit License key here.
    // Your Scandit License key is available via your Scandit SDK web account.
    const context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

    // Use the world-facing (back) camera and set it as the frame source of the context. The camera is off by
    // default and must be turned on to start streaming frames to the data capture context for recognition.
    const camera = Camera.default;
    camera.preferredResolution = VideoResolution.FullHD;
    context.setFrameSource(camera);

    // The barcode batch process is configured through barcode batch settings
    // which are then applied to the barcode batch instance that manages barcode batch.
    const settings = new BarcodeBatchSettings();

    // The settings instance initially has all types of barcodes (symbologies) disabled. For the purpose of this
    // sample we enable a very generous set of symbologies. In your own app ensure that you only enable the
    // symbologies that your app requires as every additional enabled symbology has an impact on processing times.
    settings.enableSymbologies([
        Symbology.EAN13UPCA,
        Symbology.EAN8,
        Symbology.UPCE,
        Symbology.Code39,
        Symbology.Code128,
    ]);

    // Create new barcode batch mode with the settings from above.
    const barcodeBatch = new BarcodeBatch(settings);

    // Register a listener to get informed whenever a new barcode is tracked.
    barcodeBatch.addListener({
        didUpdateSession: async (barcodeBatch, session) => {
            Object.values(session.trackedBarcodes).forEach(trackedBarcode => {
                results[trackedBarcode.barcode.data] = trackedBarcode;
            });
        }
    });

    // Set the barcode batch mode to the context.
    context.setMode(barcodeBatch);

    // To visualize the on-going barcode batch process on screen, setup a data capture view that renders the
    // camera preview. The view must be connected to the data capture context.
    const view = DataCaptureView.forContext(context);

    // Connect the data capture view to the HTML element, so it can fill up its size and follow its position.
    view.connectToElement(document.getElementById('data-capture-view'));

    // Add a Barcode Batch overlay to the data capture view to render the tracked barcodes on
    // top of the video preview.
    // This is optional, but recommended for better visual feedback.
    const basicOverlay = new BarcodeBatchBasicOverlay(barcodeBatch, BarcodeBatchBasicOverlayStyle.Frame);
    // Add the overlay to the view.
    view.addOverlay(basicOverlay);

    // Switch camera on to start streaming frames and enable the barcode batch mode.
    // The camera is started asynchronously and will take some time to completely turn on.
    camera.switchToDesiredState(FrameSourceState.On);
    barcodeBatch.isEnabled = true;

    const updateResults = () => {
        const list = document.getElementById('list');
        list.innerHTML = Object.values(results)
            .map(trackedBarcode => {
                const dataHTML = `<p class="barcodeData">${trackedBarcode.barcode.data}</p>`
                const symbology = new SymbologyDescription(trackedBarcode.barcode.symbology);
                const symbologyHTML = `<p class="symbology">${symbology.readableName}</p>`
                return `<div class="result">${dataHTML}${symbologyHTML}</div>`;
            })
            .join('');
    }

    function resetResults() {
        results = {};
        document.getElementById('results').hidden = true;
    }

    const done = () => {
        updateResults();
        barcodeBatch.isEnabled = false;
        document.getElementById('results').hidden = false;
    }

    const scanAgain = () => {
        resetResults();
        barcodeBatch.isEnabled = true;
    }

    document.getElementById('scan-again').addEventListener('click', scanAgain.bind(this));
    document.getElementById('done').addEventListener('click', done.bind(this));
}

(function () {
    runApp();
})();
