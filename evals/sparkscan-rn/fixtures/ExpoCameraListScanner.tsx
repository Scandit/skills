// Existing stock-count screen built on expo-camera's CameraView. It scans EAN-13,
// UPC-A and Code 128, keeps scanning, adds each new code to a list and bumps the
// quantity when a code is scanned again. It has a torch toggle and a Clear button.
// We want to migrate this to Scandit SparkScan while keeping the list behavior.

import React, { useCallback, useState } from 'react';
import { Button, FlatList, StyleSheet, Text, View } from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import type { BarcodeScanningResult } from 'expo-camera';

interface CountedItem {
  code: string;
  format: string;
  quantity: number;
}

export const ExpoCameraListScanner = () => {
  const [permission, requestPermission] = useCameraPermissions();
  const [items, setItems] = useState<CountedItem[]>([]);
  const [torchOn, setTorchOn] = useState(false);

  const handleScan = useCallback(({ type, data }: BarcodeScanningResult) => {
    setItems(prev => {
      const existing = prev.find(item => item.code === data);
      if (existing) {
        return prev.map(item => (item.code === data ? { ...item, quantity: item.quantity + 1 } : item));
      }
      return [{ code: data, format: type, quantity: 1 }, ...prev];
    });
  }, []);

  if (permission == null) {
    return <View style={styles.center} />;
  }

  if (!permission.granted) {
    return (
      <View style={styles.center}>
        <Text>Camera access is needed to count stock.</Text>
        <Button title="Grant permission" onPress={requestPermission} />
      </View>
    );
  }

  const total = items.reduce((sum, item) => sum + item.quantity, 0);

  return (
    <View style={styles.container}>
      <CameraView
        style={styles.camera}
        facing="back"
        enableTorch={torchOn}
        barcodeScannerSettings={{ barcodeTypes: ['ean13', 'upc_a', 'code128'] }}
        onBarcodeScanned={handleScan}
      />
      <View style={styles.toolbar}>
        <Button title={torchOn ? 'Torch off' : 'Torch on'} onPress={() => setTorchOn(on => !on)} />
        <Button title="Clear" onPress={() => setItems([])} />
      </View>
      <Text style={styles.total}>Total items: {total}</Text>
      <FlatList
        data={items}
        keyExtractor={item => item.code}
        renderItem={({ item }) => (
          <Text style={styles.row}>
            {item.code} ({item.format}) x{item.quantity}
          </Text>
        )}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  camera: { height: 300 },
  toolbar: { flexDirection: 'row', justifyContent: 'space-between', padding: 8 },
  total: { fontWeight: 'bold', paddingHorizontal: 16 },
  row: { paddingHorizontal: 16, paddingVertical: 6 },
});
