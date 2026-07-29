// Basic MatrixScan AR (BarcodeAr) integration already in place (Cordova, plugin 8.2+).
// Evals in this group add features on top of this baseline (custom highlight providers,
// annotation providers, lifecycle teardown, custom popover actions, etc.).

// @ts-check

let context = null;
let camera = null;
let barcodeAr = null;
let barcodeArView = null;

async function initializeSDK() {
  if (context) return;

  context = Scandit.DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  const cameraSettings = Scandit.BarcodeAr.createRecommendedCameraSettings();
  camera = Scandit.Camera.withSettings(cameraSettings);
  await context.setFrameSource(camera);

  const settings = new Scandit.BarcodeArSettings();
  settings.enableSymbologies([
    Scandit.Symbology.EAN13UPCA,
    Scandit.Symbology.EAN8,
    Scandit.Symbology.Code128,
    Scandit.Symbology.DataMatrix,
  ]);

  barcodeAr = new Scandit.BarcodeAr(settings);

  const viewSettings = new Scandit.BarcodeArViewSettings();
  barcodeArView = new Scandit.BarcodeArView({
    context,
    barcodeAr,
    settings: viewSettings,
    cameraSettings,
  });

  barcodeArView.highlightProvider = {
    highlightForBarcode: async (barcode) => {
      const highlight = new Scandit.BarcodeArRectangleHighlight(barcode);
      highlight.brush = new Scandit.Brush(
        Scandit.Color.fromHex('#00FFFF66'),
        Scandit.Color.fromHex('#00FFFF'),
        1.0,
      );
      return highlight;
    },
  };

  const containerEl = document.getElementById('barcode-ar-view');
  await barcodeArView.connectToElement(containerEl);
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

document.addEventListener('deviceready', () => {
  startScanning();
}, false);
