// Existing ID Capture integration written against SDK v7.
// Uses the v7 APIs that were removed/reshaped in v8:
//   - settings.scannerType = new FullDocumentScanner()   (renamed/wrapped -> settings.scanner)
//   - AamvaBarcodeVerifier.create(context) + verifier.verify(...) (removed)
// The skill should migrate this to the v8 API.

import React, { useEffect, useRef } from 'react';
import { Alert } from 'react-native';
import {
  DataCaptureContext,
  DataCaptureView,
  Camera,
  FrameSourceState,
} from 'scandit-react-native-datacapture-core';
import {
  IdCapture,
  IdCaptureSettings,
  IdCaptureRegion,
  DriverLicense,
  FullDocumentScanner,
  AamvaBarcodeVerifier,
  AamvaBarcodeVerificationResult,
  CapturedId,
  RejectionReason,
} from 'scandit-react-native-datacapture-id';

const licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';
DataCaptureContext.initialize(licenseKey);
const dataCaptureContext = DataCaptureContext.sharedInstance;

export function IdScanScreen() {
  const idCapture = useRef<IdCapture | null>(null);
  const camera = useRef<Camera | null>(null);
  const verifier = useRef<AamvaBarcodeVerifier | null>(null);

  useEffect(() => {
    const settings = new IdCaptureSettings();
    settings.acceptedDocuments.push(new DriverLicense(IdCaptureRegion.Us));
    // v7 scanner assignment (removed in v8):
    settings.scannerType = new FullDocumentScanner();

    idCapture.current = new IdCapture(settings);

    const listener = {
      didCaptureId: async (_: IdCapture, capturedId: CapturedId) => {
        idCapture.current!.isEnabled = false;
        // v7 verification call (removed in v8):
        const result: AamvaBarcodeVerificationResult =
          await verifier.current!.verify(capturedId);
        Alert.alert('AAMVA', `all checks passed: ${result.allChecksPassed}`);
        idCapture.current!.isEnabled = true;
      },
      didRejectId: (_: IdCapture, _rejectedId: CapturedId | null, reason: RejectionReason) => {
        Alert.alert('Rejected', String(reason));
      },
    };

    idCapture.current.addListener(listener);
    dataCaptureContext.setMode(idCapture.current);

    (async () => {
      camera.current = Camera.default;
      await camera.current.applySettings(IdCapture.createRecommendedCameraSettings());
      await dataCaptureContext.setFrameSource(camera.current);
      await camera.current.switchToDesiredState(FrameSourceState.On);
      idCapture.current!.isEnabled = true;

      // v7 standalone verifier (removed in v8):
      verifier.current = await AamvaBarcodeVerifier.create(dataCaptureContext);
    })();

    return () => {
      dataCaptureContext.removeMode(idCapture.current!);
    };
  }, []);

  return <DataCaptureView style={{ flex: 1 }} context={dataCaptureContext} />;
}
