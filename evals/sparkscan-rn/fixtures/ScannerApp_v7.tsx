// Pre-migration v7 SparkScan React Native integration.
// Uses v7 API surface: DataCaptureContext.forLicenseKey (still valid in v7),
// SparkScan.forSettings (still valid in v7), and v7 SparkScanView property names.
//
// The skill should migrate this to v8.

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

    // v7 factory — deprecated in v7, removed in v8.
    sparkScanMode.current = SparkScan.forSettings(settings);

    sparkScanMode.current.addListener({
      didScan: async (_: SparkScan, session: SparkScanSession) => {
        const barcode = session.newlyRecognizedBarcode;
        if (barcode) {
          setLastScan(barcode.data ?? null);
        }
      },
    });
  }

  const sparkScanViewRef = useRef<SparkScanView | null>(null);

  useEffect(() => {
    return () => {
      // v7 teardown — in v8, the context is a singleton and must not be disposed;
      // use dataCaptureContext.removeMode(sparkScanMode.current) instead.
      dataCaptureContext.dispose();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <SparkScanView
      style={{ flex: 1 }}
      context={dataCaptureContext}
      sparkScan={sparkScanMode.current}
      sparkScanViewSettings={new SparkScanViewSettings()}
      ref={view => {
        if (view) {
          // v7 property names — unchanged in v8.
          view.torchControlVisible = true;
          view.barcodeFindButtonVisible = true;
          view.triggerButtonCollapsedColor = Color.fromHex('#FF5500');
          view.triggerButtonExpandedColor = Color.fromHex('#FF5500');
          view.triggerButtonAnimationColor = Color.fromHex('#FF5500');
          view.triggerButtonTintColor = Color.fromHex('#FFFFFF');
        }
        sparkScanViewRef.current = view;
      }}
    >
      <View style={{ flex: 1 }} />
    </SparkScanView>
  );
};
