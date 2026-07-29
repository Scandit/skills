// Product receiving screen: the user scans items against a predefined list of
// expected barcodes. The expected list (targetItems) is provided as a prop.
// MatrixScan Count needs to be added: integrate BarcodeCount with a
// BarcodeCountCaptureList so in-list items appear highlighted differently from
// unknown items. Update scannedCount and notInListCount state from the session.

import React, { useState, useCallback } from 'react';
import { View, Text, FlatList, Pressable, StyleSheet } from 'react-native';

export interface TargetItem {
  data: string;
  quantity: number;
}

export interface ProductListAppProps {
  targetItems: TargetItem[];
}

export const ProductListApp = ({ targetItems }: ProductListAppProps) => {
  const [scannedCount, setScannedCount] = useState(0);
  const [notInListCount, setNotInListCount] = useState(0);

  const onClearTapped = useCallback(() => {
    setScannedCount(0);
    setNotInListCount(0);
  }, []);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerText}>
          Expected: {targetItems.reduce((acc, t) => acc + t.quantity, 0)} items
        </Text>
        <Text style={styles.headerText}>Scanned: {scannedCount}</Text>
        <Text style={[styles.headerText, notInListCount > 0 && styles.warning]}>
          Unknown: {notInListCount}
        </Text>
      </View>

      <FlatList
        style={styles.list}
        data={targetItems}
        keyExtractor={item => item.data}
        renderItem={({ item }) => (
          <View style={styles.row}>
            <Text style={styles.rowData}>{item.data}</Text>
            <Text style={styles.rowQty}>x{item.quantity}</Text>
          </View>
        )}
      />

      <View style={styles.footer}>
        {/* BarcodeCountView goes here once integrated */}
        <Pressable style={styles.clearButton} onPress={onClearTapped}>
          <Text style={styles.clearText}>CLEAR</Text>
        </Pressable>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { padding: 12, backgroundColor: '#f5f5f5', borderBottomWidth: 1, borderColor: '#ddd' },
  headerText: { fontSize: 14, marginBottom: 4 },
  warning: { color: '#F44336', fontWeight: 'bold' },
  list: { flex: 1 },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderBottomWidth: 0.5,
    borderColor: '#ccc',
  },
  rowData: { fontSize: 14 },
  rowQty: { fontSize: 14, fontWeight: 'bold' },
  footer: { padding: 16 },
  clearButton: {
    alignItems: 'center',
    padding: 12,
    borderWidth: 2,
    borderColor: '#000',
    borderRadius: 4,
  },
  clearText: { fontWeight: 'bold' },
});
