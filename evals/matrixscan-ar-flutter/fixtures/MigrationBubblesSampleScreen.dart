/*
 * This file is part of the Scandit Data Capture SDK
 *
 * Copyright (C) 2021- Scandit AG. All rights reserved.
 */

import 'package:MatrixScanBubblesSample/freeze_button.dart';
import 'package:MatrixScanBubblesSample/product_bubble.dart';
import 'package:MatrixScanBubblesSample/quadrilateral_extension.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_batch.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';
import 'bubble_view_state.dart';

class MatrixScanScreen extends StatefulWidget {
  const MatrixScanScreen({Key? key}) : super(key: key);

  @override
  _MatrixScanScreenState createState() => _MatrixScanScreenState();
}

class _MatrixScanScreenState extends State<MatrixScanScreen>
    with WidgetsBindingObserver
    implements BarcodeBatchListener, BarcodeBatchAdvancedOverlayListener {
  // Use the world-facing (back) camera.
  Camera? _camera = Camera.defaultCamera;
  late BarcodeBatch _barcodeBatch;
  late DataCaptureView _captureView;
  late BarcodeBatchAdvancedOverlay _advancedOverlay;

  Map<int, ProductBubble?> _trackedBarcodes = {};

  bool _isPermissionMessageVisible = false;

  bool _isFrozen = false;

  _MatrixScanScreenState();

  void _checkPermission() {
    Permission.camera.request().then((status) {
      if (!mounted) return;

      final isGranted = status.isGranted;
      setState(() {
        _isPermissionMessageVisible = !isGranted;
      });

      if (isGranted && _camera != null) {
        _camera!.switchToDesiredState(_isFrozen ? FrameSourceState.off : FrameSourceState.on);
      }
    });
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);

    // Use the recommended camera settings for the BarcodeBatch mode.
    var cameraSettings = BarcodeBatch.createRecommendedCameraSettings();
    // Adjust camera settings - set Ultra HD resolution.
    cameraSettings.preferredResolution = VideoResolution.uhd4k;

    _camera?.applySettings(cameraSettings);

    // Switch camera on to start streaming frames and enable the barcode batch mode.
    // The camera is started asynchronously and will take some time to completely turn on.
    _checkPermission();

    // The barcode batch process is configured through barcode batch settings
    // which are then applied to the barcode batch instance that manages barcode batch.
    var captureSettings = BarcodeBatchSettings();

    // The settings instance initially has all types of barcodes (symbologies) disabled. For the purpose of this
    // sample we enable a very generous set of symbologies. In your own app ensure that you only enable the
    // symbologies that your app requires as every additional enabled symbology has an impact on processing times.
    captureSettings.enableSymbologies({
      Symbology.ean8,
      Symbology.ean13Upca,
      Symbology.upce,
      Symbology.code39,
      Symbology.code128,
    });

    // Create new barcode batch mode with the settings from above.
    _barcodeBatch = BarcodeBatch(captureSettings)
      // Register self as a listener to get informed of tracked barcodes.
      ..addListener(this);

    // To visualize the on-going barcode capturing process on screen, setup a data capture view that renders the
    // camera preview. The view must be connected to the data capture context.
    _captureView = DataCaptureView.forContext(DataCaptureContext.sharedInstance);

    // Add a barcode batch overlay to the data capture view to render the tracked barcodes on top of the video
    // preview. This is optional, but recommended for better visual feedback.
    var _basicOverlay = BarcodeBatchBasicOverlay(_barcodeBatch, style: BarcodeBatchBasicOverlayStyle.dot);
    _captureView.addOverlay(_basicOverlay);

    // Add an advanced barcode batch overlay to the data capture view to render AR visualization on
    // top of the camera preview.
    _advancedOverlay = BarcodeBatchAdvancedOverlay(_barcodeBatch)..listener = this;
    _captureView.addOverlay(_advancedOverlay);

    // Set the default camera as the frame source of the context. The camera is off by
    // default and must be turned on to start streaming frames to the data capture context for recognition.
    if (_camera != null) {
      DataCaptureContext.sharedInstance.setFrameSource(_camera!);
    }
    _barcodeBatch.isEnabled = true;

    // Set the barcode batch mode as the current mode of the data capture context.
    DataCaptureContext.sharedInstance.setMode(_barcodeBatch);
  }

  @override
  Widget build(BuildContext context) {
    Widget child;
    if (_isPermissionMessageVisible) {
      child = Text('No permission to access the camera!',
          style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.black));
    } else {
      child = Stack(children: [
        _captureView,
        Container(
          alignment: Alignment.bottomCenter,
          padding: EdgeInsets.all(48.0),
          child: SizedBox(height: 120, width: 120, child: FreezeButton(onPressed: (isFrozen) => _freeze(isFrozen))),
        )
      ]);
    }
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) {
        if (didPop) {
          return;
        }
        // Cleanup everything on back press because this is the only screen
        _cleanup();

        // Exit the app since this is the only screen
        SystemNavigator.pop();
      },
      child: Scaffold(body: child),
    );
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    switch (state) {
      case AppLifecycleState.resumed:
        _checkPermission();
        break;
      default:
        if (!_isFrozen && _camera != null) {
          _camera!.switchToDesiredState(FrameSourceState.off);
        }
        break;
    }
  }

  // This function is called whenever objects are updated and it's the right place to react to
  // the batch results.
  @override
  Future<void> didUpdateSession(
      BarcodeBatch barcodeBatch, BarcodeBatchSession session, Future<FrameData> getFrameData()) async {
    // Remove information about tracked barcodes that are no longer tracked.
    for (final removedBarcodeId in session.removedTrackedBarcodes) {
      _trackedBarcodes[removedBarcodeId] = null;
    }

    // Update AR views
    for (final trackedBarcode in session.trackedBarcodes.values) {
      _captureView
          .viewQuadrilateralForFrameQuadrilateral(trackedBarcode.location)
          .then((location) => _updateView(trackedBarcode, location));
    }
  }

  @override
  Anchor anchorForTrackedBarcode(BarcodeBatchAdvancedOverlay overlay, TrackedBarcode trackedBarcode) {
    // The offset of our overlay will be calculated from the top-center anchoring point.
    return Anchor.topCenter;
  }

  @override
  void didTapViewForTrackedBarcode(BarcodeBatchAdvancedOverlay overlay, TrackedBarcode trackedBarcode) {
    // Transfer the didTap event to the corresponding bubble widget.
    var productBubble = _trackedBarcodes[trackedBarcode.identifier];
    if (productBubble != null) {
      productBubble.onTap();
    }
    // Because the Matrix Scan augmentations (bubbles) are actually drawn on the native layer and not by the Flutter
    // engine, it is not enough to modify the augmentation UI in the productBubble.onTap() call. We also need to reset
    // the widget on the native layer by calling the BarcodeBatchAdvancedOverlay.setWidgetForTrackedBarcode(...)
    // method.
    _advancedOverlay.setWidgetForTrackedBarcode(productBubble, trackedBarcode);
  }

  @override
  PointWithUnit offsetForTrackedBarcode(BarcodeBatchAdvancedOverlay overlay, TrackedBarcode trackedBarcode) {
    // We set the offset's height to be equal of the 100 percent of our overlay.
    // The minus sign means that the overlay will be above the barcode.
    return PointWithUnit(DoubleWithUnit(0, MeasureUnit.fraction), DoubleWithUnit(-1, MeasureUnit.fraction));
  }

  @override
  BarcodeBatchAdvancedOverlayWidget? widgetForTrackedBarcode(
      BarcodeBatchAdvancedOverlay overlay, TrackedBarcode trackedBarcode) {
    return null;
  }

  _updateView(TrackedBarcode trackedBarcode, Quadrilateral viewLocation) {
    // If the barcode is wider than the desired percent of the data capture view's width, show it to the user.
    var shouldBeShown = viewLocation.width() > MediaQuery.of(context).size.width * 0.1;
    if (!shouldBeShown) {
      if (_trackedBarcodes.containsKey(trackedBarcode.identifier) &&
          _trackedBarcodes[trackedBarcode.identifier] == null) {
        return;
      }
      _trackedBarcodes[trackedBarcode.identifier] = null;
      _advancedOverlay.setWidgetForTrackedBarcode(null, trackedBarcode);
      return;
    }

    if (_trackedBarcodes[trackedBarcode.identifier] == null) {
      var bubble = ProductBubble(trackedBarcode.barcode.data ?? '', BubbleViewState(BubbleType.StockInfo));
      _trackedBarcodes[trackedBarcode.identifier] = bubble;
      _advancedOverlay.setWidgetForTrackedBarcode(bubble, trackedBarcode);
    }
  }

  void _freeze(bool isFrozen) {
    // Toggle barcode batch to stop or start processing frames.
    _barcodeBatch.isEnabled = !isFrozen;
    // Switch the camera on or off to toggle streaming frames. The camera is stopped asynchronously.
    _camera?.switchToDesiredState(isFrozen ? FrameSourceState.off : FrameSourceState.on);

    _isFrozen = isFrozen;
  }

  void _cleanup() {
    WidgetsBinding.instance.removeObserver(this);
    _barcodeBatch.removeListener(this);
    _barcodeBatch.isEnabled = false;
    _camera?.switchToDesiredState(FrameSourceState.off);
    DataCaptureContext.sharedInstance.removeCurrentMode();
  }
}
