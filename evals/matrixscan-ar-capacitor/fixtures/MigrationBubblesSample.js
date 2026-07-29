import {
    Anchor,
    Camera,
    DataCaptureContext,
    DataCaptureView,
    FrameSourceState,
    MeasureUnit,
    NumberWithUnit,
    PointWithUnit,
    Quadrilateral,
    ScanditCaptureCorePlugin,
    VideoResolution
} from 'scandit-capacitor-datacapture-core';

import {
    BarcodeBatch,
    BarcodeBatchAdvancedOverlay,
    BarcodeBatchBasicOverlay,
    BarcodeBatchBasicOverlayStyle,
    BarcodeBatchSettings,
    Symbology,
    TrackedBarcodeView
} from 'scandit-capacitor-datacapture-barcode';

const isViewShowingAlternateContent = {};
const viewContents = {};

const Elements = {
    dataCaptureView: document.getElementById('data-capture-view'),
    freezeButton: document.getElementById('freeze-button'),
}

async function runApp() {
    // Initialize the plugins.
    await ScanditCaptureCorePlugin.initializePlugins();

    // Calculate the width of a quadrilateral (barcode location) based on it's corners.
    Quadrilateral.prototype.width = function () {
        return Math.max(this.topRight.x - this.topLeft.x, this.bottomRight.x - this.bottomLeft.x);
    }

    // Enter your Scandit License key here.
    // Your Scandit License key is available via your Scandit SDK web account.
    const context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

    // Use the recommended camera settings for the BarcodeBatch mode as default settings.
    // The preferred resolution is automatically chosen, which currently defaults to HD on all devices.
    // Setting the preferred resolution to 4K helps to get a better decode range.
    const cameraSettings = BarcodeBatch.createRecommendedCameraSettings();
    cameraSettings.preferredResolution = VideoResolution.UHD4K;

    // Use the default camera and set it as the frame source of the context. The camera is off by
    // default and must be turned on to start streaming frames to the data capture context for recognition.
    window.camera = Camera.withSettings(cameraSettings);
    context.setFrameSource(window.camera);

    // The barcode batch process is configured through barcode batch settings
    // and are then applied to the barcode batch instance that manages barcode batch.
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
    window.barcodeBatch = new BarcodeBatch(settings);

    // Register a listener to get informed of tracked barcodes.
    window.barcodeBatch.addListener({
        // This function is called whenever objects are updated and it's the right place to react to the batch results.
        didUpdateSession: async (mode, session) => {
            // Remove information about tracked barcodes that are no longer tracked.
            session.removedTrackedBarcodes.forEach(identifier => {
                isViewShowingAlternateContent[identifier] = null;
                viewContents[identifier] = null;
            });

            // Update AR views
            Object.values(session.trackedBarcodes).forEach(trackedBarcode =>
                window.view.viewQuadrilateralForFrameQuadrilateral(trackedBarcode.location)
                    .then(location => updateView(trackedBarcode, location, isViewShowingAlternateContent[trackedBarcode.identifier])));
        }
    });

    // Set the barcode batch mode to the context.
    context.setMode(window.barcodeBatch);

    // To visualize the on-going barcode batch process on screen, setup a data capture view that renders the
    // camera preview. The view must be connected to the data capture context.
    window.view = DataCaptureView.forContext(context);

    // Connect the data capture view to the HTML element, so it can fill up its size and follow its position.
    window.view.connectToElement(Elements.dataCaptureView);

    // Add a barcode batch overlay to the data capture view to render the tracked barcodes on top of the video
    // preview. This is optional, but recommended for better visual feedback. The overlay is automatically added
    // to the view.
    const basicOverlay = new BarcodeBatchBasicOverlay(window.barcodeBatch, BarcodeBatchBasicOverlayStyle.Dot);
    // Add the overlay to the view.
    window.view.addOverlay(basicOverlay);

    // Add an advanced barcode batch overlay to the data capture view to render AR visualization on top of
    // the camera preview.
    window.advancedOverlay = new BarcodeBatchAdvancedOverlay(window.barcodeBatch);
    window.advancedOverlay.listener = {
        didTapViewForTrackedBarcode: (overlay, trackedBarcode) => {
            window.view.viewQuadrilateralForFrameQuadrilateral(trackedBarcode.location)
                .then(location => updateView(trackedBarcode, location, !isViewShowingAlternateContent[trackedBarcode.identifier]));
        },
        anchorForTrackedBarcode: (overlay, trackedBarcode) => {
            // The offset of our overlay will be calculated from the top center anchoring point.
            return Anchor.TopCenter;
        },
        offsetForTrackedBarcode: (overlay, trackedBarcode) => {
            // We set the offset's height to be equal of the 100 percent of our overlay.
            // The minus sign means that the overlay will be above the barcode.
            return new PointWithUnit(
                new NumberWithUnit(0, MeasureUnit.Fraction),
                new NumberWithUnit(-1, MeasureUnit.Fraction)
            );
        }
    }

    // Add the advanced overlay to the view.
    window.view.addOverlay(window.advancedOverlay);

    // Switch camera on to start streaming frames and enable the barcode batch mode.
    // The camera is started asynchronously and will take some time to completely turn on.
    await window.camera.switchToDesiredState(FrameSourceState.On);
    window.barcodeBatch.isEnabled = true;
}

const freeze = async () => {
    // Disable barcode batch to stop processing frames.
    window.barcodeBatch.isEnabled = false
    // Switch the camera off to stop streaming frames. The camera is stopped asynchronously.
    await window.camera.switchToDesiredState(FrameSourceState.Off)
}

const unfreeze = async () => {
    // Enable barcode batch to resume processing frames.
    window.barcodeBatch.isEnabled = true
    // Switch the camera on to start streaming frames. The camera is started asynchronously.
    await window.camera.switchToDesiredState(FrameSourceState.On)
}

const toggleFreeze = () => {
    if (Elements.freezeButton.className === "freeze") {
        freeze();
        Elements.freezeButton.className = "unfreeze";
    } else {
        unfreeze();
        Elements.freezeButton.className = "freeze";
    }
}

const updateView = (trackedBarcode, viewLocation, isShowingAlternateContent = false) => {
    isViewShowingAlternateContent[trackedBarcode.identifier] = isShowingAlternateContent;

    // If the barcode is wider than the desired percent of the data capture view's width, show it to the user.
    const shouldBeShown = viewLocation.width() > (screen.width * 0.1);
    let viewContent = null;
    if (shouldBeShown) {
        // Get the information you want to show from your back end system/database.
        viewContent = isShowingAlternateContent
            ? { title: trackedBarcode.barcode.data }
            : { title: "Report stock count", text: "Shelf: 4 Back Room: 8" };
    }

    // The AR view associated with the tracked barcode should only be set again if it was changed,
    // to avoid unnecessarily recreating it.
    const didViewChange = JSON.stringify(viewContents[trackedBarcode.identifier]) !== JSON.stringify(viewContent);
    if (didViewChange) {
        viewContents[trackedBarcode.identifier] = viewContent;
        setView(trackedBarcode);
    }
}

const setView = (trackedBarcode) => {
    const viewContent = viewContents[trackedBarcode.identifier];
    const shouldShowARView = viewContent !== null;

    if (shouldShowARView) {
        const bubble = TrackedBarcodeView.withHTMLElement(
            createBubbleWithContent(viewContent),
            // To get the best possible AR view quality, it is suggested to set AR view sizes with taking into account
            // the device pixel ratio and scale them down based on it.
            { scale: 1 / window.devicePixelRatio },
        );
        window.advancedOverlay.setViewForTrackedBarcode(bubble, trackedBarcode).catch(console.warn);
    } else {
        window.advancedOverlay.setViewForTrackedBarcode(null, trackedBarcode).catch(console.warn);
    }
}

const createBubbleWithContent = (content) => {
    const bubbleWidth = 200;
    const bubbleHeight = 60;

    const container = document.createElement("div");
    container.style.zIndex = 5;
    container.style.width = `${bubbleWidth * window.devicePixelRatio}px`;
    container.style.height = `${bubbleHeight * window.devicePixelRatio}px`;
    container.style.borderRadius = `${(bubbleHeight / 2) * window.devicePixelRatio}px`;
    container.style.backgroundColor = "#fffc"
    container.style.display = "flex";
    container.style.fontFamily = "Helvetica Neue";
    container.style.fontSize = `${14 * window.devicePixelRatio}px`;

    const textContainer = document.createElement("div");
    textContainer.style.width = `${(bubbleWidth - bubbleHeight) * window.devicePixelRatio}px`;
    textContainer.style.height = `${bubbleHeight * window.devicePixelRatio}px`;
    textContainer.style.display = "flex";
    textContainer.style.flexDirection = "column";
    textContainer.style.justifyContent = "center";
    textContainer.style.alignItems = "flex-start";
    textContainer.style.paddingLeft = `${7 * window.devicePixelRatio}px`;
    container.appendChild(textContainer);

    if (content.title) {
        const title = document.createElement("p");
        title.style.margin = "0";
        title.style.fontWeight = "bold";
        title.innerText = content.title;
        textContainer.appendChild(title);
    }

    if (content.text) {
        const text = document.createElement("p");
        text.style.margin = "0";
        text.innerText = content.text;
        textContainer.appendChild(text);
    }

    return container;
};

Elements.freezeButton.addEventListener('click', toggleFreeze.bind(this));

(function () {
    runApp();
})();
