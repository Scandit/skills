// Basic MatrixScan Count (BarcodeCount) integration already in place (Cordova, plugin >=7.6).
// Evals in this group add features on top of this baseline (custom brushes, listeners,
// capture lists, status mode, tap-to-uncount, hardware trigger, etc.).

// @ts-check

let context = null;
let camera = null;
let barcodeCount = null;
let barcodeCountView = null;

async function initializeSDK() {
  if (context) return;

  context = Scandit.DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  const cameraSettings = Scandit.BarcodeCount.createRecommendedCameraSettings();
  camera = Scandit.Camera.withSettings(cameraSettings);
  await context.setFrameSource(camera);

  const settings = new Scandit.BarcodeCountSettings();
  settings.enableSymbologies([
    Scandit.Symbology.EAN13UPCA,
    Scandit.Symbology.EAN8,
    Scandit.Symbology.Code128,
    Scandit.Symbology.DataMatrix,
  ]);

  barcodeCount = new Scandit.BarcodeCount(settings);
  context.addMode(barcodeCount);
  barcodeCount.isEnabled = true;

  barcodeCountView = Scandit.BarcodeCountView.forContextWithModeAndStyle(
    context,
    barcodeCount,
    Scandit.BarcodeCountViewStyle.Icon
  );

  barcodeCountView.uiListener = {
    didTapExitButton: () => {
      teardown();
    },
  };

  const containerEl = document.getElementById('barcode-count-view');
  barcodeCountView.connectToElement(containerEl);
}

async function startScanning() {
  await initializeSDK();
  await camera.switchToDesiredState(Scandit.FrameSourceState.On);
}

async function stopScanning() {
  if (camera) {
    await camera.switchToDesiredState(Scandit.FrameSourceState.Off);
  }
}

async function teardown() {
  if (camera) {
    await camera.switchToDesiredState(Scandit.FrameSourceState.Off);
    camera = null;
  }
  if (barcodeCountView) {
    barcodeCountView.detachFromElement();
    barcodeCountView = null;
  }
  if (barcodeCount && context) {
    barcodeCount.isEnabled = false;
    context.removeMode(barcodeCount);
  }
  barcodeCount = null;
  context = null;
}

document.addEventListener('deviceready', () => {
  startScanning();
}, false);

document.addEventListener('pause', async () => {
  if (camera) await camera.switchToDesiredState(Scandit.FrameSourceState.Off);
}, false);

document.addEventListener('resume', async () => {
  if (camera) await camera.switchToDesiredState(Scandit.FrameSourceState.On);
}, false);
