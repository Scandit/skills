// Entry point component for the React Native app. The MatrixScan AR integration
// should go here as a function component with hooks.
// Assume this file is the screen rendered by the navigator / App root.

import React from 'react';
import { View, Text } from 'react-native';

export const ArScreen = () => {
  // TODO: integrate MatrixScan AR (BarcodeAr*) here.
  return (
    <View style={{ flex: 1 }}>
      <Text>Scanner goes here</Text>
    </View>
  );
};
