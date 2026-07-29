// Pre-migration v6 SparkScan React Native integration.
// Uses v6 API surface: DataCaptureContext.forLicenseKey, SparkScan.forSettings,
// onFastFindButtonTappedIn, and v6 SparkScanView property names.
//
// The skill should migrate this to v7 or v8.

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { View } from 'react-native';

import {
  DataCaptureContext,
  Color,
} from 'scandit-react-native-datacapture-core';
import {
  SparkScan,
  SparkScanSettings,
  SparkScanView,
  SparkScanViewSettings,
  SparkScanSession,
  Symbology,
} from 'scandit-react-native-datacapture-barcode';

export const ScanScreen = () => {
  const [, setLastScan] = useState<string | null>(null);

  const dataCaptureContext = useMemo(
    () => DataCaptureContext.forLicenseKey('YOUR_LICENSE_KEY'),
    [],
  );

  const sparkScanMode = useRef<SparkScan>(null!);
  if (!sparkScanMode.current) {
    const settings = new SparkScanSettings();
    settings.enableSymbologies([
      Symbology.EAN13UPCA,
      Symbology.Code128,
      Symbology.QR,
    ]);

    // v6 factory — deprecated in v7, removed in v8.
    sparkScanMode.current = SparkScan.forSettings(settings);

    sparkScanMode.current.addListener({
      didScan: async (_: SparkScan, session: SparkScanSession) => {
        const barcode =
          session.newlyRecognizedBarcodes && session.newlyRecognizedBarcodes[0];
        if (barcode) {
          setLastScan(barcode.data ?? null);
        }
      },
    });
  }

  const sparkScanViewRef = useRef<SparkScanView | null>(null);

  useEffect(() => {
    return () => {
      // v6/v7 teardown pattern — in v8 this becomes removeMode(sparkScanMode.current).
      dataCaptureContext.dispose();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // v6 viewSettings — defaultHandMode no longer exists in v7.
  const viewSettings = useMemo(() => {
    const s = new SparkScanViewSettings();
    // @ts-expect-error v6 only
    s.defaultHandMode = 'right';
    return s;
  }, []);

  return (
    <SparkScanView
      style={{ flex: 1 }}
      context={dataCaptureContext}
      sparkScan={sparkScanMode.current}
      sparkScanViewSettings={viewSettings}
      ref={view => {
        if (view) {
          // v6 properties — all of these need migration to v7.
          // @ts-expect-error v6 only
          view.torchButtonVisible = true;
          // @ts-expect-error v6 only
          view.fastFindButtonVisible = true;
          // @ts-expect-error v6 only
          view.handModeButtonVisible = false;
          // @ts-expect-error v6 only
          view.soundModeButtonVisible = false;
          // @ts-expect-error v6 only
          view.hapticModeButtonVisible = false;
          // @ts-expect-error v6 only
          view.shouldShowScanAreaGuides = false;
          // @ts-expect-error v6 only
          view.captureButtonBackgroundColor = Color.fromHex('#FF5500');
          // @ts-expect-error v6 only
          view.captureButtonActiveBackgroundColor = Color.fromHex('#AA3300');
          // @ts-expect-error v6 only
          view.captureButtonTintColor = Color.fromHex('#FFFFFF');
          // @ts-expect-error v6 only
          view.startCapturingText = 'START';
          // @ts-expect-error v6 only
          view.stopCapturingText = 'STOP';
          // @ts-expect-error v6 only
          view.resumeCapturingText = 'RESUME';
          // @ts-expect-error v6 only
          view.scanningCapturingText = 'SCANNING';

          // v6 ui listener callback — renamed in v7.
          view.uiListener = {
            // @ts-expect-error v6 only
            onFastFindButtonTappedIn: (_: SparkScanView) => {
              // navigate to find screen
            },
          };
        }
        sparkScanViewRef.current = view;
      }}
    >
      <View style={{ flex: 1 }} />
    </SparkScanView>
  );
};
