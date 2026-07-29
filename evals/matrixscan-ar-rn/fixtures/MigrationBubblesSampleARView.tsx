import React from 'react';
import { Text, TouchableWithoutFeedback, View } from 'react-native';
import { styles } from './styles';
import { BarcodeBatchAdvancedOverlayView } from 'scandit-react-native-datacapture-barcode';

interface ARViewProps {
  stock: {
    shelf: string;
    backRoom: string;
  };
  barcodeData: string;
}

// The component must be registered and must have a static `moduleName` property.
// See: `AppRegistry.registerComponent(ARView.moduleName, () => ARView);` in index.js
export class ARView extends BarcodeBatchAdvancedOverlayView {
  state = { showBarcodeData: false };
  render() {
    const { stock = { shelf: '', backRoom: '' } } = this.props as ARViewProps;
    const { showBarcodeData } = this.state;

    // The text content of the bubble, switching between stock information and the barcode data.
    const stockInfo = (
      <>
        <Text style={styles.arBubbleHeader}>Report Stock Count</Text>
        <Text style={styles.arBubbleInfo}>
          Shelf: {stock.shelf} Back Room: {stock.backRoom}
        </Text>
      </>
    );

    return (
      <TouchableWithoutFeedback onPress={() => this.setState({ showBarcodeData: !showBarcodeData })}>
        <View style={styles.arBubbleContainer}>
          <View style={styles.arBubbleContent}>
            {showBarcodeData ? (
              <Text style={styles.arBubbleHeader}>{(this.props as ARViewProps).barcodeData}</Text>
            ) : (
              stockInfo
            )}
          </View>
        </View>
      </TouchableWithoutFeedback>
    );
  }
}
