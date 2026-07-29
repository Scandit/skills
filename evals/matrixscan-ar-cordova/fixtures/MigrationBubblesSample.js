// MatrixScanBubblesSample — legacy BarcodeBatch + BarcodeBatchAdvancedOverlay integration.
// This file is a migration fixture. Migrate it to the BarcodeAr API.
//
// NOTE: This sample uses TrackedBarcodeView.withHTMLElement and setViewForTrackedBarcode
// to render freeform HTML overlays per barcode. BarcodeArCustomAnnotation, which is the
// conceptual successor for custom HTML annotations, is NOT available on Cordova. The
// migration must replace the HTML bubble with a built-in annotation type
// (BarcodeArInfoAnnotation, BarcodeArPopoverAnnotation, BarcodeArStatusIconAnnotation,
// or BarcodeArResponsiveAnnotation).

const isViewShowingAlternateContent = {};
const viewContents = {};

const Elements = {
  dataCaptureView: document.getElementById('data-capture-view'),
  freezeButton: document.getElementById('freeze-button'),
};

document.addEventListener('deviceready', () => {
  // Calculate the width of a quadrilateral (barcode location) based on its corners.
  Scandit.Quadrilateral.prototype.width = function () {
    return Math.max(this.topRight.x - this.topLeft.x, this.bottomRight.x - this.bottomLeft.x);
  };

  // Enter your Scandit License key here.
  // Your Scandit License key is available via your Scandit SDK web account.
  const context = Scandit.DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  // Use the recommended camera settings for the BarcodeBatch mode as default settings.
  // Setting the preferred resolution to 4K helps to get a better decode range.
  const cameraSettings = Scandit.BarcodeBatch.createRecommendedCameraSettings();
  cameraSettings.preferredResolution = Scandit.VideoResolution.UHD4K;

  // Use the default camera and set it as the frame source of the context. The camera is off by
  // default and must be turned on to start streaming frames to the data capture context for recognition.
  window.camera = Scandit.Camera.withSettings(cameraSettings);
  context.setFrameSource(window.camera);

  // The barcode batch process is configured through barcode batch settings
  // and are then applied to the barcode batch instance that manages barcode batch.
  const settings = new Scandit.BarcodeBatchSettings();

  // The settings instance initially has all types of barcodes (symbologies) disabled. For the purpose of this
  // sample we enable a very generous set of symbologies. In your own app ensure that you only enable the
  // symbologies that your app requires as every additional enabled symbology has an impact on processing times.
  settings.enableSymbologies([
    Scandit.Symbology.EAN13UPCA,
    Scandit.Symbology.EAN8,
    Scandit.Symbology.UPCE,
    Scandit.Symbology.Code39,
    Scandit.Symbology.Code128,
  ]);

  // Create new barcode batch mode with the settings from above.
  window.barcodeBatch = new Scandit.BarcodeBatch(settings);

  // Register a listener to get informed of tracked barcodes.
  window.barcodeBatch.addListener({
    didUpdateSession: (barcodeBatch, session) => {
      // Remove information about tracked barcodes that are no longer tracked.
      session.removedTrackedBarcodes.forEach(identifier => {
        isViewShowingAlternateContent[identifier] = null;
        viewContents[identifier] = null;
      });

      // Update AR views
      Object.values(session.trackedBarcodes).forEach(trackedBarcode =>
        window.view.viewQuadrilateralForFrameQuadrilateral(trackedBarcode.location)
          .then(location => updateView(trackedBarcode, location, isViewShowingAlternateContent[trackedBarcode.identifier])));

      session.addedTrackedBarcodes.forEach(trackedBarcode => {
        // The offset of our overlay will be calculated from the top center anchoring point.
        window.advancedOverlay.setAnchorForTrackedBarcode(Scandit.Anchor.TopCenter, trackedBarcode).catch(console.warn);
        // We set the offset's height to be equal of the 100 percent of our overlay.
        // The minus sign means that the overlay will be above the barcode.
        window.advancedOverlay.setOffsetForTrackedBarcode(
          new Scandit.PointWithUnit(
            new Scandit.NumberWithUnit(0, Scandit.MeasureUnit.Fraction),
            new Scandit.NumberWithUnit(-1, Scandit.MeasureUnit.Fraction)
          ), trackedBarcode).catch(console.warn);
      });
    }
  });

  // Add mode to context
  context.setMode(window.barcodeBatch);

  // To visualize the on-going barcode batch process on screen, setup a data capture view that renders the
  // camera preview. The view must be connected to the data capture context.
  window.view = Scandit.DataCaptureView.forContext(context);

  // Connect the data capture view to the HTML element, so it can fill up its size and follow its position.
  window.view.connectToElement(Elements.dataCaptureView);

  // Add a barcode batch overlay to the data capture view to render the tracked barcodes on top of the video
  // preview. This is optional, but recommended for better visual feedback.
  const basicOverlay = new Scandit.BarcodeBatchBasicOverlay(window.barcodeBatch, Scandit.BarcodeBatchBasicOverlayStyle.Dot);
  window.view.addOverlay(basicOverlay);

  // Add an advanced barcode batch overlay to the data capture view to render AR visualization on top of
  // the camera preview.
  window.advancedOverlay = new Scandit.BarcodeBatchAdvancedOverlay(window.barcodeBatch);
  window.advancedOverlay.listener = {
    didTapViewForTrackedBarcode: (overlay, trackedBarcode) => {
      window.view.viewQuadrilateralForFrameQuadrilateral(trackedBarcode.location)
        .then(location => updateView(trackedBarcode, location, !isViewShowingAlternateContent[trackedBarcode.identifier]));
    },
    // The offset of our overlay will be calculated from the center anchoring point.
    anchorForTrackedBarcode: () => Scandit.Anchor.TopCenter,
    // We set the offset's height to be equal of the 100 percent of our overlay.
    // The minus sign means that the overlay will be above the barcode.
    offsetForTrackedBarcode: () => new Scandit.PointWithUnit(
      new Scandit.NumberWithUnit(0, Scandit.MeasureUnit.Fraction),
      new Scandit.NumberWithUnit(-1, Scandit.MeasureUnit.Fraction),
    ),
  };

  window.view.addOverlay(window.advancedOverlay);

  // Switch camera on to start streaming frames and enable the barcode batch mode.
  // The camera is started asynchronously and will take some time to completely turn on.
  window.camera.switchToDesiredState(Scandit.FrameSourceState.On);
  window.barcodeBatch.isEnabled = true;
}, false);

const freeze = () => {
  // Disable barcode batch to stop processing frames.
  window.barcodeBatch.isEnabled = false;
  // Switch the camera off to stop streaming frames. The camera is stopped asynchronously.
  window.camera.switchToDesiredState(Scandit.FrameSourceState.Off);
};

const unfreeze = () => {
  // Enable barcode batch to resume processing frames.
  window.barcodeBatch.isEnabled = true;
  // Switch the camera on to start streaming frames. The camera is started asynchronously.
  window.camera.switchToDesiredState(Scandit.FrameSourceState.On);
};

const toggleFreeze = () => {
  if (Elements.freezeButton.className === 'freeze') {
    freeze();
    Elements.freezeButton.className = 'unfreeze';
  } else {
    unfreeze();
    Elements.freezeButton.className = 'freeze';
  }
};

const updateView = (trackedBarcode, viewLocation, isShowingAlternateContent = false) => {
  isViewShowingAlternateContent[trackedBarcode.identifier] = isShowingAlternateContent;

  // If the barcode is wider than the desired percent of the data capture view's width, show it to the user.
  const shouldBeShown = viewLocation.width() > (screen.width * 0.1);
  var viewContent = null;
  if (shouldBeShown) {
    // Get the information you want to show from your back end system/database.
    viewContent = isShowingAlternateContent
      ? { title: trackedBarcode.barcode.data }
      : { title: 'Report stock count', text: 'Shelf: 4 Back Room: 8' };
  }

  // The AR view associated with the tracked barcode should only be set again if it was changed,
  // to avoid unnecessarily recreating it.
  const didViewChange = JSON.stringify(viewContents[trackedBarcode.identifier]) !== JSON.stringify(viewContent);
  if (didViewChange) {
    viewContents[trackedBarcode.identifier] = viewContent;
    setView(trackedBarcode);
  }
};

const setView = (trackedBarcode) => {
  const viewContent = viewContents[trackedBarcode.identifier];
  const shouldShowARView = viewContent !== null;

  if (shouldShowARView) {
    const bubble = Scandit.TrackedBarcodeView.withHTMLElement(
      createBubbleWithContent(viewContent, trackedBarcode.barcode.data),
      // To get the best possible AR view quality, it is suggested to set AR view sizes with taking into account
      // the device pixel ratio and scale them down based on it.
      { scale: 1 / window.devicePixelRatio },
    );
    window.advancedOverlay.setViewForTrackedBarcode(bubble, trackedBarcode).catch(console.warn);
  } else {
    window.advancedOverlay.setViewForTrackedBarcode(null, trackedBarcode).catch(console.warn);
  }
};

const createBubbleWithContent = (content, barcode) => {
  const bubbleWidth = 200;
  const bubbleHeight = 60;

  const container = document.createElement('div');
  container.id = `bubble-${barcode}`;
  container.style.width = `${bubbleWidth * window.devicePixelRatio}px`;
  container.style.height = `${bubbleHeight * window.devicePixelRatio}px`;
  container.style.borderRadius = `${(bubbleHeight / 2) * window.devicePixelRatio}px`;
  container.style.backgroundColor = '#fffc';
  container.style.display = 'flex';
  container.style.fontFamily = 'Helvetica Neue';
  container.style.fontSize = `${14 * window.devicePixelRatio}px`;

  const textContainer = document.createElement('div');
  textContainer.style.width = `${(bubbleWidth - bubbleHeight) * window.devicePixelRatio}px`;
  textContainer.style.height = `${bubbleHeight * window.devicePixelRatio}px`;
  textContainer.style.display = 'flex';
  textContainer.style.flexDirection = 'column';
  textContainer.style.justifyContent = 'center';
  textContainer.style.alignItems = 'flex-start';
  textContainer.style.paddingLeft = `${7 * window.devicePixelRatio}px`;
  container.appendChild(textContainer);

  if (content.title) {
    const title = document.createElement('p');
    title.style.margin = '0';
    title.style.fontWeight = 'bold';
    title.innerText = content.title;
    textContainer.appendChild(title);
  }

  if (content.text) {
    const text = document.createElement('p');
    text.style.margin = '0';
    text.innerText = content.text;
    textContainer.appendChild(text);
  }

  return container;
};
