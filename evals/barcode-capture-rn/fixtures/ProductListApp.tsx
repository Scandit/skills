// Product list screen with basic React state management.
// BarcodeCapture needs to be added: scanned barcodes should be appended to
// scannedProducts via setScannedProducts and the list re-rendered.

import React, { useState, useCallback } from 'react';
import { View, Text, FlatList, Pressable, StyleSheet } from 'react-native';

export interface ScannedProduct {
  data: string;
  symbology: string;
}

export const ProductListScreen = () => {
  const [scannedProducts, setScannedProducts] = useState<ScannedProduct[]>([]);

  const onClearTapped = useCallback(() => {
    setScannedProducts([]);
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.total}>Total scanned: {scannedProducts.length}</Text>
      <FlatList
        style={styles.list}
        data={scannedProducts}
        keyExtractor={(_, i) => String(i)}
        renderItem={({ item, index }) => (
          <View style={styles.row}>
            <Text>
              {index + 1}. {item.data} ({item.symbology})
            </Text>
          </View>
        )}
      />
      <Pressable style={styles.clearButton} onPress={onClearTapped}>
        <Text style={styles.clearText}>CLEAR LIST</Text>
      </Pressable>
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1 },
  total: { padding: 12, fontWeight: 'bold' },
  list: { flex: 1 },
  row: { paddingHorizontal: 12, paddingVertical: 8, borderBottomWidth: 0.5, borderColor: '#ccc' },
  clearButton: {
    alignItems: 'center', padding: 12, margin: 16,
    borderWidth: 2, borderColor: '#000', borderRadius: 4,
  },
  clearText: { fontWeight: 'bold' },
});
