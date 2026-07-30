// Product list BLoC with basic stream-based state management.
// BarcodeCount (MatrixScan Count) needs to be added: scanned barcodes from
// each didScan callback should be appended to scannedItems and emitted through
// _scannedItemsController so the UI updates.

import 'dart:async';

class ScannedItem {
  final String data;
  final String symbology;
  final int quantity;

  ScannedItem(this.data, this.symbology, {this.quantity = 1});
}

class ProductListBloc {
  final List<ScannedItem> scannedItems = [];
  final StreamController<List<ScannedItem>> _scannedItemsController =
      StreamController<List<ScannedItem>>.broadcast();

  Stream<List<ScannedItem>> get scannedItemsStream =>
      _scannedItemsController.stream;

  int get totalCount => scannedItems.length;

  void clear() {
    scannedItems.clear();
    _scannedItemsController.add(List.unmodifiable(scannedItems));
  }

  void dispose() {
    _scannedItemsController.close();
  }
}
