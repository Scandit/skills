// Entry point component for the React Native app. The BarcodeCapture
// integration should go here as a function component with hooks.
// Assume this file is the screen rendered by the navigator / App root.

import React from 'react';
import { View, Text } from 'react-native';

export const ScanScreen = () => {
  // TODO: integrate BarcodeCapture here.
  return (
    <View style={{ flex: 1 }}>
      <Text>Scanner goes here</Text>
    </View>
  );
};
