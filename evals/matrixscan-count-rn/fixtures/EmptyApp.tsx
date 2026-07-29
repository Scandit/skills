// Entry point component for the React Native app. The MatrixScan Count integration
// should go here as a function component with hooks.
// Assume this file is the screen rendered by the navigator / App root.

import React from 'react';
import { View, Text } from 'react-native';

export const CountScreen = () => {
  // TODO: integrate MatrixScan Count (BarcodeCount*) here.
  return (
    <View style={{ flex: 1 }}>
      <Text>Scanner goes here</Text>
    </View>
  );
};
