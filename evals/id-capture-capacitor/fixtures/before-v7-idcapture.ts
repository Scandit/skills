// Existing ID Capture integration written against SDK v7 for Capacitor.
// Uses the v7 APIs that were removed/reshaped in v8:
//   - settings.scannerType = new FullDocumentScanner()   (renamed/wrapped -> settings.scanner)
//   - AamvaBarcodeVerifier.create(context) + verifier.verify(...) (removed)
// The skill should migrate this to the v8 API.

import {
  DataCaptureContext,
  DataCaptureView,
  Camera,
  FrameSourceState,
  ScanditCaptureCorePlugin,
} from 'scandit-capacitor-datacapture-core';
import {
  IdCapture,
  IdCaptureSettings,
  IdCaptureOverlay,
  IdCaptureRegion,
  DriverLicense,
  FullDocumentScanner,
  AamvaBarcodeVerifier,
  AamvaBarcodeVerificationResult,
  CapturedId,
  RejectionReason,
} from 'scandit-capacitor-datacapture-id';

const licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

async function bootstrap(): Promise<void> {
  await ScanditCaptureCorePlugin.initializePlugins();

  const context = DataCaptureContext.initialize(licenseKey);

  const settings = new IdCaptureSettings();
  settings.acceptedDocuments.push(new DriverLicense(IdCaptureRegion.Us));
  // v7 scanner assignment (removed in v8):
  settings.scannerType = new FullDocumentScanner();

  const camera = Camera.withSettings(IdCapture.createRecommendedCameraSettings());
  await context.setFrameSource(camera);

  const idCapture = new IdCapture(settings);

  // v7 standalone verifier (removed in v8):
  const verifier = await AamvaBarcodeVerifier.create(context);

  await idCapture.addListener({
    didCaptureId: async (_: IdCapture, capturedId: CapturedId) => {
      idCapture.isEnabled = false;
      // v7 verification call (removed in v8):
      const result: AamvaBarcodeVerificationResult = await verifier.verify(capturedId);
      console.log('AAMVA all checks passed:', result.allChecksPassed);
      idCapture.isEnabled = true;
    },
    didRejectId: (_: IdCapture, _rejected: CapturedId | null, reason: RejectionReason) => {
      console.log('Rejected:', reason);
    },
  });

  await context.setMode(idCapture);

  const view = DataCaptureView.forContext(context);
  view.connectToElement(document.getElementById('data-capture-view')!);
  view.addOverlay(new IdCaptureOverlay(idCapture));

  await camera.switchToDesiredState(FrameSourceState.On);
  idCapture.isEnabled = true;
}

document.addEventListener('DOMContentLoaded', () => {
  bootstrap();
});
