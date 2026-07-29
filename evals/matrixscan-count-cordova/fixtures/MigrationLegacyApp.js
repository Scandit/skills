// Legacy Cordova MatrixScan Count integration using the pre-7.6 constructor pattern.
// This file is the BEFORE state for migration evals.

// @ts-check

let context = null;
let camera = null;
let barcodeCount = null;
let barcodeCountView = null;

async function initializeSDK() {
  if (context) return;

  // Old factory — pre-7.6 pattern, auto-wires mode to context
  context = Scandit.DataCaptureContext.forLicenseKey('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  camera = Scandit.Camera.default;
  await context.setFrameSource(camera);

  const settings = new Scandit.BarcodeCountSettings();
  settings.enableSymbologies([
    Scandit.Symbology.EAN13UPCA,
    Scandit.Symbology.EAN8,
    Scandit.Symbology.Code128,
  ]);

  // Old constructor — passes context as first argument
  barcodeCount = Scandit.BarcodeCount.forDataCaptureContext(context, settings);
  barcodeCount.isEnabled = true;

  barcodeCount.addListener({
    didScan: async (mode, session) => {
      // session.recognizedBarcodes available >=7.0
      const recognized = session.recognizedBarcodes;
      if (recognized) {
        Object.values(recognized).forEach(barcode => {
          console.log('Scanned:', barcode.data);
        });
      }
    },
  });

  barcodeCountView = Scandit.BarcodeCountView.forContextWithModeAndStyle(
    context,
    barcodeCount,
    Scandit.BarcodeCountViewStyle.Icon
  );

  barcodeCountView.shouldShowToolbar = true;

  barcodeCountView.uiListener = {
    didTapExitButton: () => {
      teardown();
    },
    didTapListButton: () => {
      showResults();
    },
  };

  const containerEl = document.getElementById('barcode-count-view');
  barcodeCountView.connectToElement(containerEl);
}

function showResults() {
  // Show results overlay
  document.getElementById('results-overlay').classList.remove('hidden');
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
  // Old pattern: no removeMode call needed (forDataCaptureContext auto-wired)
  barcodeCount = null;
  context = null;
}

async function startScanning() {
  await initializeSDK();
  await camera.switchToDesiredState(Scandit.FrameSourceState.On);
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
