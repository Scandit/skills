// Fully integrated MatrixScan AR screen (React Native, v8 API,
// function component with hooks). Evals in this group add features on top of
// this baseline (custom highlights, annotation types, lifecycle cleanup, etc.).

import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';

import { Color, Brush } from 'scandit-react-native-datacapture-core';
import {
  BarcodeAr,
  BarcodeArSettings,
  BarcodeArView,
  BarcodeArViewSettings,
  BarcodeArListener,
  BarcodeArSession,
  BarcodeArHighlightProvider,
  BarcodeArAnnotationProvider,
  BarcodeArCircleHighlight,
  BarcodeArCircleHighlightPreset,
  BarcodeArInfoAnnotation,
  BarcodeArInfoAnnotationBodyComponent,
  BarcodeArInfoAnnotationWidthPreset,
  BarcodeArInfoAnnotationListener,
  BarcodeArAnnotationTrigger,
  Barcode,
  Symbology,
} from 'scandit-react-native-datacapture-barcode';

import { DataCaptureContext } from 'scandit-react-native-datacapture-core';

const licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';
DataCaptureContext.initialize(licenseKey);
const dataCaptureContext = DataCaptureContext.sharedInstance;

function createBarcodeAr(): BarcodeAr {
  const settings = new BarcodeArSettings();
  settings.enableSymbologies([
    Symbology.EAN13UPCA,
    Symbology.EAN8,
    Symbology.UPCE,
    Symbology.Code39,
    Symbology.Code128,
    Symbology.QR,
  ]);
  return new BarcodeAr(settings);
}

export const ArScreen = () => {
  const [scanCount, setScanCount] = useState(0);

  const barcodeArRef = useRef<BarcodeAr>(null!);
  const viewRef = useRef<BarcodeArView | null>(null);

  if (!barcodeArRef.current) {
    const barcodeAr = createBarcodeAr();

    const listener: BarcodeArListener = {
      didUpdateSession: async (_: BarcodeAr, session: BarcodeArSession) => {
        if (session.addedTrackedBarcodes.length > 0) {
          setScanCount(prev => prev + session.addedTrackedBarcodes.length);
        }
      },
    };
    barcodeAr.addListener(listener);
    dataCaptureContext.addMode(barcodeAr);
    barcodeArRef.current = barcodeAr;
  }

  useEffect(() => {
    return () => {
      dataCaptureContext.removeMode(barcodeArRef.current);
    };
  }, []);

  const highlightProvider: BarcodeArHighlightProvider = {
    highlightForBarcode: async (barcode: Barcode) => {
      const highlight = new BarcodeArCircleHighlight(barcode, BarcodeArCircleHighlightPreset.Dot);
      highlight.brush = new Brush(
        Color.fromHex('#4D99FF'),
        Color.fromHex('#4D99FF'),
        1.0,
      );
      return highlight;
    },
  };

  const annotationListener: BarcodeArInfoAnnotationListener = {
    didTap(annotation: BarcodeArInfoAnnotation) {
      console.log('Annotation tapped for barcode:', annotation.barcode.data);
    },
  };

  const annotationProvider: BarcodeArAnnotationProvider = {
    annotationForBarcode: async (barcode: Barcode) => {
      const bodyRow = new BarcodeArInfoAnnotationBodyComponent();
      bodyRow.text = barcode.data ?? '(no data)';

      const annotation = new BarcodeArInfoAnnotation(barcode);
      annotation.body = [bodyRow];
      annotation.width = BarcodeArInfoAnnotationWidthPreset.Medium;
      annotation.isEntireAnnotationTappable = true;
      annotation.annotationTrigger = BarcodeArAnnotationTrigger.HighlightTapAndBarcodeScan;
      annotation.listener = annotationListener;
      return annotation;
    },
  };

  return (
    <BarcodeArView
      style={styles.container}
      context={dataCaptureContext}
      barcodeAr={barcodeArRef.current}
      settings={new BarcodeArViewSettings()}
      highlightProvider={highlightProvider}
      annotationProvider={annotationProvider}
      ref={(view: BarcodeArView | null) => {
        if (view) {
          view.start();
          view.shouldShowCameraSwitchControl = true;
          viewRef.current = view;
        }
      }}
    >
      <View style={styles.badge}>
        <Text style={styles.badgeText}>
          {scanCount} {scanCount === 1 ? 'barcode' : 'barcodes'} detected
        </Text>
      </View>
    </BarcodeArView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1 },
  badge: {
    position: 'absolute',
    top: 16,
    left: 16,
    backgroundColor: 'rgba(0,0,0,0.6)',
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  badgeText: { color: 'white', fontWeight: 'bold', fontSize: 13 },
});
