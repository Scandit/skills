// Existing barcode scanner built on react-native-vision-camera v5 with the
// react-native-vision-camera-barcode-scanner plugin (useBarcodeScannerOutput).
// It scans every format, has a torch toggle, collects deduplicated values with a
// running summary, and can also decode a photo file. We want to migrate this to
// Scandit BarcodeCapture while keeping the same behavior.

import React, { useCallback, useState } from 'react';
import { Button, FlatList, StyleSheet, Text, View } from 'react-native';
import { Camera, useCameraDevice, useCameraPermission } from 'react-native-vision-camera';
import {
  useBarcodeScanner,
  useBarcodeScannerOutput,
  Barcode,
} from 'react-native-vision-camera-barcode-scanner';
import { loadImage } from 'react-native-nitro-image';

interface ScannedCode {
  value: string;
  format: string;
}

interface Props {
  photoPath?: string;
}

export const VisionCameraV5Scanner = ({ photoPath }: Props) => {
  const device = useCameraDevice('back');
  const { hasPermission, requestPermission } = useCameraPermission();
  const [scanned, setScanned] = useState<ScannedCode[]>([]);
  const [torchOn, setTorchOn] = useState(false);

  const addBarcodes = useCallback((barcodes: Barcode[]) => {
    for (const barcode of barcodes) {
      const value = barcode.rawValue;
      if (value == null) continue;
      setScanned(prev => {
        if (prev.some(c => c.value === value)) return prev;
        return [...prev, { value, format: barcode.format }];
      });
    }
  }, []);

  const barcodeOutput = useBarcodeScannerOutput({
    barcodeFormats: ['all-formats'],
    onBarcodeScanned: addBarcodes,
    onError: error => console.warn(error.message),
  });

  const photoScanner = useBarcodeScanner({ barcodeFormats: ['all-formats'] });

  const scanPhoto = useCallback(async () => {
    if (photoPath == null) return;
    const image = await loadImage({ filePath: photoPath });
    addBarcodes(await photoScanner.scanCodesInImageAsync(image));
  }, [photoPath, photoScanner, addBarcodes]);

  if (!hasPermission) {
    return (
      <View style={styles.center}>
        <Button title="Allow camera" onPress={requestPermission} />
      </View>
    );
  }

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
        outputs={[barcodeOutput]}
        torchMode={torchOn ? 'on' : 'off'}
      />
      <View style={styles.controls}>
        <Button title={torchOn ? 'Torch off' : 'Torch on'} onPress={() => setTorchOn(on => !on)} />
        <Button title="Scan photo" onPress={scanPhoto} />
      </View>
      <View style={styles.summary}>
        <Text style={styles.title}>Scanned: {scanned.length}</Text>
        <FlatList
          data={scanned}
          keyExtractor={item => item.value}
          renderItem={({ item }) => (
            <Text style={styles.row}>
              {item.format}: {item.value}
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
  controls: { position: 'absolute', top: 48, right: 16 },
  summary: { position: 'absolute', bottom: 0, left: 0, right: 0, padding: 16, backgroundColor: '#fff' },
  title: { fontWeight: 'bold', marginBottom: 8 },
  row: { paddingVertical: 4 },
});
