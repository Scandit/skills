// Existing ID Capture integration written against SDK v6 for Capacitor.
// Uses the v6 APIs that were removed/reshaped at v6 -> v7 (and again at v7 -> v8):
//   - settings.supportedDocuments = IdDocumentType bitmask   (removed -> acceptedDocuments + typed docs)
//   - settings.supportedSides = SupportedSides.FrontAndBack  (removed -> scanner / IdCaptureScanner)
//   - capturedId.documentType                                (removed -> capturedId.document?.documentType)
//   - listener.onIdCapturedTimedOut(...)                     (removed -> onIdRejected with RejectionReason.Timeout)
// The skill should migrate this to the current (v8) API.

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
  IdDocumentType,
  SupportedSides,
  CapturedId,
} from 'scandit-capacitor-datacapture-id';

const licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

async function bootstrap(): Promise<void> {
  await ScanditCaptureCorePlugin.initializePlugins();

  const context = DataCaptureContext.initialize(licenseKey);

  const settings = new IdCaptureSettings();
  // v6 bitmask of supported documents (removed in v7):
  settings.supportedDocuments =
    IdDocumentType.IdCardViz | IdDocumentType.DLViz | IdDocumentType.PassportMrz;
  // v6 implicit scanner via supported sides (removed in v7):
  settings.supportedSides = SupportedSides.FrontAndBack;

  const camera = Camera.withSettings(IdCapture.createRecommendedCameraSettings());
  await context.setFrameSource(camera);

  const idCapture = new IdCapture(settings);

  await idCapture.addListener({
    onIdCaptured: (_: IdCapture, capturedId: CapturedId) => {
      idCapture.isEnabled = false;
      // v6 document-type getter directly on the captured id (removed in v8):
      console.log('Captured document type:', capturedId.documentType);
      console.log('Name:', capturedId.fullName);
      idCapture.isEnabled = true;
    },
    // v6 dedicated timeout callback (removed -> onIdRejected with RejectionReason.Timeout):
    onIdCapturedTimedOut: (_: IdCapture, capturedId: CapturedId | null) => {
      console.log('Capture timed out');
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
