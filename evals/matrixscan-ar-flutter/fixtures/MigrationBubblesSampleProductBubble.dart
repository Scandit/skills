/*
 * This file is part of the Scandit Data Capture SDK
 *
 * Copyright (C) 2021- Scandit AG. All rights reserved.
 */

import 'package:flutter/material.dart';
import 'bubble_view_state.dart';

import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_batch.dart';

class ProductBubble extends BarcodeBatchAdvancedOverlayWidget {
  final String barcodeData;
  final BubbleViewState viewState;

  ProductBubble(this.barcodeData, this.viewState, {Key? key}) : super(key: key);

  @override
  ProductBubbleState createState() => ProductBubbleState();

  void onTap() {
    viewState.switchState();
  }
}

class ProductBubbleState extends BarcodeBatchAdvancedOverlayWidgetState<ProductBubble> {
  Widget? _stockInfo;
  Widget? _barcodeData;

  @override
  void initState() {
    super.initState();
    _stockInfo = Column(
      mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: CrossAxisAlignment.start,
      textDirection: TextDirection.ltr,
      children: [
        Text("Report stock count",
            textDirection: TextDirection.ltr,
            style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.black)),
        Text("Shelf: 4 Back room: 8",
            textDirection: TextDirection.ltr, style: TextStyle(fontSize: 10, color: Colors.black))
      ],
    );
    _barcodeData =
        Text(widget.barcodeData, textDirection: TextDirection.ltr, style: TextStyle(fontSize: 12, color: Colors.black));
  }

  @override
  BarcodeBatchAdvancedOverlayContainer build(BuildContext context) {
    return BarcodeBatchAdvancedOverlayContainer(
      width: 160,
      height: 60,
      decoration: BoxDecoration(color: const Color(0xFFFFFFEE), borderRadius: BorderRadius.circular(30)),
      child: Row(
        textDirection: TextDirection.ltr,
        children: [
          Expanded(
              child: Center(
            // The text content of the bubble, switching between stock information and the barcode data.
            child: widget.viewState.viewType == BubbleType.BarcodeData ? _barcodeData : _stockInfo,
          ))
        ],
      ),
    );
  }
}
