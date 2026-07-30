// Legacy MatrixScan Count integration using the pre-7.6 factory pattern.
// Migrate this to use the new `new BarcodeCount(settings)` constructor
// and `dataCaptureContext.addMode(barcodeCount)`.

import React, { useEffect, useRef } from 'react';
import {
  BarcodeCount,
  BarcodeCountSettings,
  BarcodeCountSession,
  BarcodeCountView,
  BarcodeCountViewStyle,
  BarcodeCountViewListener,
  BarcodeCountViewUiListener,
  Symbology,
  TrackedBarcode,
} from 'scandit-react-native-datacapture-barcode';
import {
  Camera,
  DataCaptureContext,
  FrameSourceState,
} from 'scandit-react-native-datacapture-core';

// Legacy singleton setup
const dataCaptureContext = DataCaptureContext.forLicenseKey(
  '-- ENTER YOUR SCANDIT LICENSE KEY HERE --',
);

export const LegacyCountScreen = () => {
  const cameraRef = useRef<Camera>(null!);
  if (!cameraRef.current) {
    // Old: use Camera.default — recommended camera settings not yet available
    const camera = Camera.default;
    if (!camera) throw new Error('No camera');
    dataCaptureContext.setFrameSource(camera);
    cameraRef.current = camera;
  }

  const barcodeCountRef = useRef<BarcodeCount>(null!);
  if (!barcodeCountRef.current) {
    const settings = new BarcodeCountSettings();
    settings.enableSymbologies([
      Symbology.EAN13UPCA,
      Symbology.Code128,
    ]);

    // Old factory: context passed as first argument, mode auto-added to context
    const mode = BarcodeCount.forDataCaptureContext(dataCaptureContext, settings);

    mode.addListener({
      didScan: async (_: BarcodeCount, session: BarcodeCountSession) => {
        // Old pattern: session API varied by version
        console.log('Scan complete, frame:', session.frameSequenceID);
      },
    });

    barcodeCountRef.current = mode;
  }

  const viewListenerRef = useRef<BarcodeCountViewListener | null>(null);
  if (!viewListenerRef.current) {
    viewListenerRef.current = {
      didTapRecognizedBarcode: (_view: BarcodeCountView, tb: TrackedBarcode) => {
        console.log('Tapped:', tb.barcode.data);
      },
    };
  }

  const viewUiListenerRef = useRef<BarcodeCountViewUiListener | null>(null);
  if (!viewUiListenerRef.current) {
    viewUiListenerRef.current = {
      didTapExitButton: (_view: BarcodeCountView) => {
        cameraRef.current.switchToDesiredState(FrameSourceState.Off);
      },
    };
  }

  useEffect(() => {
    cameraRef.current.switchToDesiredState(FrameSourceState.On);
    return () => {
      dataCaptureContext.setFrameSource(null);
    };
  }, []);

  return (
    <BarcodeCountView
      style={{ flex: 1 }}
      barcodeCount={barcodeCountRef.current}
      context={dataCaptureContext}
      viewStyle={BarcodeCountViewStyle.Icon}
      ref={view => {
        if (view) {
          view.listener = viewListenerRef.current;
          view.uiListener = viewUiListenerRef.current;
        }
      }}
    />
  );
};
