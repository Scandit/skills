// Existing multi-barcode scan screen built on react-native-vision-camera's
// useCodeScanner. It tracks every code visible in the frame, dedupes them by value,
// and shows a running count. Migrate this to Scandit MatrixScan Batch (BarcodeBatch).

import React, { useState, useCallback } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import {
  Camera,
  useCameraDevice,
  useCodeScanner,
  Code,
} from 'react-native-vision-camera';

interface ScannedCode {
  value: string;
  type: string;
}

export const VisionCameraScanScreen = () => {
  const device = useCameraDevice('back');
  const [scanned, setScanned] = useState<Map<string, ScannedCode>>(new Map());

  // Multi-barcode: codeScanner reports every code in the frame on each callback.
  const codeScanner = useCodeScanner({
    codeTypes: ['ean-13', 'code-128', 'qr'],
    onCodeScanned: useCallback((codes: Code[]) => {
      setScanned(prev => {
        const next = new Map(prev);
        for (const code of codes) {
          if (code.value && !next.has(code.value)) {
            next.set(code.value, { value: code.value, type: code.type });
          }
        }
        return next;
      });
    }, []),
  });

  if (device == null) {
    return (
      <View style={styles.container}>
        <Text>No camera device</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Camera
        style={StyleSheet.absoluteFill}
        device={device}
        isActive={true}
        codeScanner={codeScanner}
      />
      <View style={styles.counter}>
        <Text style={styles.counterText}>Unique codes: {scanned.size}</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1 },
  counter: { position: 'absolute', top: 48, left: 16 },
  counterText: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
});
