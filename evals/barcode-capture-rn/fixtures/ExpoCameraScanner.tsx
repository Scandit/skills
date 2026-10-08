// Existing barcode scanner built on expo-camera's CameraView. It scans EAN-13,
// UPC-A, Code 128 and QR codes, has a torch toggle, accepts one code and then
// stops until "Scan again" is pressed, and can also decode an image file. We want
// to migrate this to Scandit BarcodeCapture while keeping the same behavior.

import React, { useState } from 'react';
import { Button, StyleSheet, Text, View } from 'react-native';
import { CameraView, scanFromURLAsync, useCameraPermissions } from 'expo-camera';
import type { BarcodeScanningResult } from 'expo-camera';

interface Props {
  imageUri?: string;
}

export const ExpoCameraScanner = ({ imageUri }: Props) => {
  const [permission, requestPermission] = useCameraPermissions();
  const [scanned, setScanned] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [torchOn, setTorchOn] = useState(false);

  const handleScan = ({ type, data }: BarcodeScanningResult) => {
    if (scanned) return;
    setScanned(true);
    setResult(`${type}: ${data}`);
  };

  const scanImage = async () => {
    if (imageUri == null) return;
    const results = await scanFromURLAsync(imageUri, ['ean13', 'upc_a', 'code128', 'qr']);
    if (results.length > 0) handleScan(results[0]);
  };

  if (permission == null) {
    return <View style={styles.center} />;
  }

  if (!permission.granted) {
    return (
      <View style={styles.center}>
        <Text>Camera access is needed to scan.</Text>
        <Button title="Grant permission" onPress={requestPermission} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <CameraView
        style={StyleSheet.absoluteFill}
        facing="back"
        enableTorch={torchOn}
        barcodeScannerSettings={{ barcodeTypes: ['ean13', 'upc_a', 'code128', 'qr'] }}
        onBarcodeScanned={scanned ? undefined : handleScan}
      />
      <View style={styles.controls}>
        <Button title={torchOn ? 'Torch off' : 'Torch on'} onPress={() => setTorchOn(on => !on)} />
        <Button title="Scan image" onPress={scanImage} />
      </View>
      {scanned && (
        <View style={styles.result}>
          <Text style={styles.resultText}>{result}</Text>
          <Button
            title="Scan again"
            onPress={() => {
              setScanned(false);
              setResult(null);
            }}
          />
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  controls: { position: 'absolute', top: 48, right: 16 },
  result: { position: 'absolute', bottom: 0, left: 0, right: 0, padding: 16, backgroundColor: '#fff' },
  resultText: { fontWeight: 'bold', marginBottom: 8 },
});
