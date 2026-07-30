// Empty starter screen for the ID Capture React Native integration eval.
// The skill should fill in: the DataCaptureContext.initialize() call (in a
// CaptureContext module or at the top of the file), the IdCaptureSettings +
// IdCapture + listener wiring, the <DataCaptureView> with the overlay, and
// the AppState-based camera lifecycle.

import React from 'react';
import { SafeAreaView, Text } from 'react-native';

export function IdScanScreen() {
  return (
    <SafeAreaView style={{ flex: 1 }}>
      <Text>ID Capture will go here</Text>
    </SafeAreaView>
  );
}
