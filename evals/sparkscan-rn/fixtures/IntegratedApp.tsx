// Basic SparkScan integration already in place (React Native, v8 API,
// function component with hooks). Evals in this group add features on top of
// this baseline (custom feedback, custom trigger button, UI customization,
// lifecycle cleanup, codeDuplicateFilter, etc.).

import React, { useEffect, useRef, useState } from 'react';
import { View, ScrollView, Text, StyleSheet } from 'react-native';

import { DataCaptureContext } from 'scandit-react-native-datacapture-core';
import {
  SparkScan,
  SparkScanSettings,
  SparkScanView,
  SparkScanViewSettings,
  SparkScanSession,
  Symbology,
  SymbologyDescription,
} from 'scandit-react-native-datacapture-barcode';

const licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';
DataCaptureContext.initialize(licenseKey);
const dataCaptureContext = DataCaptureContext.sharedInstance;

interface ScannedProduct {
  data: string | null;
  symbology: string;
}

function createSparkScan(): SparkScan {
  const settings = new SparkScanSettings();
  settings.enableSymbologies([
    Symbology.EAN13UPCA,
    Symbology.Code128,
    Symbology.QR,
  ]);
  return new SparkScan(settings);
}

export const ScanScreen = () => {
  const [scannedProducts, setScannedProducts] = useState<ScannedProduct[]>([]);

  const sparkScanMode = useRef<SparkScan>(null!);
  if (!sparkScanMode.current) {
    sparkScanMode.current = createSparkScan();
  }
  const sparkScanViewRef = useRef<SparkScanView | null>(null);

  useEffect(() => {
    const listener = {
      didScan: async (_: SparkScan, session: SparkScanSession) => {
        const barcode = session.newlyRecognizedBarcode;
        if (barcode == null) return;
        const symbology = new SymbologyDescription(barcode.symbology);
        setScannedProducts(prev => [
          ...prev,
          { data: barcode.data, symbology: symbology.readableName },
        ]);
      },
    };
    sparkScanMode.current.addListener(listener);

    return () => {
      // No cleanup yet — evals may add removeMode here.
    };
  }, []);

  return (
    <SparkScanView
      style={styles.container}
      context={dataCaptureContext}
      sparkScan={sparkScanMode.current}
      sparkScanViewSettings={new SparkScanViewSettings()}
      ref={view => {
        sparkScanViewRef.current = view;
      }}
    >
      <View style={styles.container}>
        <Text style={styles.count}>
          {scannedProducts.length}{' '}
          {scannedProducts.length === 1 ? 'item' : 'items'}
        </Text>
        <ScrollView style={{ flex: 1 }}>
          {scannedProducts.map((product, index) => (
            <View key={index} style={styles.row}>
              <Text style={styles.data}>{product.data}</Text>
              <Text style={styles.symbology}>{product.symbology}</Text>
            </View>
          ))}
        </ScrollView>
      </View>
    </SparkScanView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1 },
  count: { fontWeight: 'bold', padding: 16, fontSize: 14 },
  row: { paddingHorizontal: 16, paddingVertical: 10, borderBottomWidth: 0.5, borderColor: '#ccc' },
  data: { fontWeight: 'bold', fontSize: 14 },
  symbology: { fontSize: 12, color: '#666', marginTop: 2 },
});
