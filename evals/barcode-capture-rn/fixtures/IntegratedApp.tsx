// Basic BarcodeCapture integration already in place (React Native, v8 API,
// function component with hooks). Evals in this group add features on top of
// this baseline (custom feedback, viewfinder, location selection, scan
// intention, codeDuplicateFilter, lifecycle cleanup, etc.).

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';

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
  SymbologyDescription,
} from 'scandit-react-native-datacapture-barcode';

const licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';
DataCaptureContext.initialize(licenseKey);
const dataCaptureContext = DataCaptureContext.sharedInstance;

export const ScanScreen = () => {
  const [lastScan, setLastScan] = useState<string | null>(null);

  const viewRef = useRef<DataCaptureView | null>(null);
  const cameraRef = useRef<Camera | null>(null);
  const barcodeCaptureRef = useRef<BarcodeCapture | null>(null);

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
    const barcodeCapture = new BarcodeCapture(settings);
    dataCaptureContext.addMode(barcodeCapture);
    barcodeCaptureRef.current = barcodeCapture;
  }

  useEffect(() => {
    const barcodeCapture = barcodeCaptureRef.current!;

    const listener = {
      didScan: async (
        mode: BarcodeCapture,
        session: BarcodeCaptureSession,
      ) => {
        const barcode = session.newlyRecognizedBarcode;
        if (barcode == null) return;
        mode.isEnabled = false;
        const symbology = new SymbologyDescription(barcode.symbology);
        setLastScan(`${barcode.data} (${symbology.readableName})`);
        mode.isEnabled = true;
      },
    };
    barcodeCapture.addListener(listener);

    const overlay = new BarcodeCaptureOverlay(barcodeCapture);
    viewRef.current?.addOverlay(overlay);

    return () => {
      // No teardown of the mode yet — evals may add removeMode here.
    };
  }, []);

  useFocusEffect(
    useCallback(() => {
      const barcodeCapture = barcodeCaptureRef.current!;
      const camera = cameraRef.current;
      barcodeCapture.isEnabled = true;
      camera?.switchToDesiredState(FrameSourceState.On);
      return () => {
        barcodeCapture.isEnabled = false;
        camera?.switchToDesiredState(FrameSourceState.Off);
      };
    }, []),
  );

  return (
    <View style={styles.container}>
      <DataCaptureView
        style={styles.preview}
        context={dataCaptureContext}
        ref={view => { viewRef.current = view; }}
      />
      <View style={styles.results}>
        <Text>{lastScan ?? 'Waiting for scan...'}</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1 },
  preview: { flex: 1 },
  results: { padding: 16, backgroundColor: '#fff' },
});
