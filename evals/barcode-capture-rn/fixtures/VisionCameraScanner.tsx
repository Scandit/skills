// Existing barcode scanner built on react-native-vision-camera's built-in
// code scanner (useCodeScanner). The app collects scanned values, deduplicates
// them, and shows a running summary. We want to migrate this to Scandit
// BarcodeCapture while keeping the same dedup + summary behavior.

import React, { useState, useCallback } from 'react';
import { View, Text, FlatList, StyleSheet } from 'react-native';
import {
  Camera,
  useCameraDevice,
  useCameraPermission,
  useCodeScanner,
  Code,
} from 'react-native-vision-camera';

interface ScannedCode {
  value: string;
  type: string;
}

export const VisionCameraScanner = () => {
  const device = useCameraDevice('back');
  const { hasPermission, requestPermission } = useCameraPermission();
  const [scanned, setScanned] = useState<ScannedCode[]>([]);

  const codeScanner = useCodeScanner({
    codeTypes: ['ean-13', 'code-128', 'qr'],
    onCodeScanned: (codes: Code[]) => {
      for (const code of codes) {
        const value = code.value;
        if (value == null) continue;
        setScanned(prev => {
          // Deduplicate: ignore a value we've already collected.
          if (prev.some(c => c.value === value)) return prev;
          return [...prev, { value, type: code.type }];
        });
      }
    },
  });

  const onStart = useCallback(async () => {
    if (!hasPermission) await requestPermission();
  }, [hasPermission, requestPermission]);

  if (device == null) {
    return (
      <View style={styles.center}>
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
        onTouchStart={onStart}
      />
      <View style={styles.summary}>
        <Text style={styles.title}>Scanned: {scanned.length}</Text>
        <FlatList
          data={scanned}
          keyExtractor={item => item.value}
          renderItem={({ item }) => (
            <Text style={styles.row}>
              {item.type}: {item.value}
            </Text>
          )}
        />
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  summary: { position: 'absolute', bottom: 0, left: 0, right: 0, padding: 16, backgroundColor: '#fff' },
  title: { fontWeight: 'bold', marginBottom: 8 },
  row: { paddingVertical: 4 },
});
