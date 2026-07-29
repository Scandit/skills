// Pre-migration v7 BarcodeCapture React Native integration.
// Uses v7 API surface: DataCaptureContext.forLicenseKey (still valid in v7),
// BarcodeCapture.forContext (still valid in v7), and
// BarcodeCaptureOverlay.withBarcodeCaptureForView.
//
// The skill should migrate this to v8.

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { View } from 'react-native';

import {
  Camera,
  DataCaptureContext,
  DataCaptureView,
  FrameSourceState,
} from 'scandit-react-native-datacapture-core';
import {
  BarcodeCapture,
  BarcodeCaptureOverlay,
  BarcodeCaptureSession,
  BarcodeCaptureSettings,
  Symbology,
} from 'scandit-react-native-datacapture-barcode';

export const ScanScreen = () => {
  const [, setLastScan] = useState<string | null>(null);

  const dataCaptureContext = useMemo(
    () => DataCaptureContext.forLicenseKey('YOUR_LICENSE_KEY'),
    [],
  );

  const viewRef = useRef<DataCaptureView | null>(null);
  const barcodeCaptureRef = useRef<BarcodeCapture | null>(null);
  const cameraRef = useRef<Camera | null>(null);

  if (cameraRef.current === null) {
    const camera = Camera.default;
    camera?.applySettings(BarcodeCapture.recommendedCameraSettings);
    dataCaptureContext.setFrameSource(camera);
    cameraRef.current = camera;
  }

  if (barcodeCaptureRef.current === null) {
    const settings = new BarcodeCaptureSettings();
    settings.enableSymbologies([
      Symbology.EAN13UPCA,
      Symbology.Code128,
      Symbology.QR,
    ]);

    // v7 factory — still valid in v7, deprecated in v8.
    barcodeCaptureRef.current = BarcodeCapture.forContext(
      dataCaptureContext,
      settings,
    );

    barcodeCaptureRef.current.addListener({
      didScan: async (
        mode: BarcodeCapture,
        session: BarcodeCaptureSession,
      ) => {
        const barcode = session.newlyRecognizedBarcode;
        if (barcode) {
          mode.isEnabled = false;
          setLastScan(barcode.data ?? null);
          mode.isEnabled = true;
        }
      },
    });
  }

  useEffect(() => {
    // v7 overlay factory.
    const overlay = BarcodeCaptureOverlay.withBarcodeCaptureForView(
      barcodeCaptureRef.current!,
      viewRef.current,
    );

    Camera.default?.switchToDesiredState(FrameSourceState.On);

    return () => {
      Camera.default?.switchToDesiredState(FrameSourceState.Off);
      // v7 teardown — in v8 the context is a singleton; replace with removeMode.
      dataCaptureContext.dispose();
      void overlay;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <View style={{ flex: 1 }}>
      <DataCaptureView
        style={{ flex: 1 }}
        context={dataCaptureContext}
        ref={view => { viewRef.current = view; }}
      />
    </View>
  );
};
