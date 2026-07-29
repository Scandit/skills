/*
 * This file is part of the Scandit Data Capture SDK
 *
 * Copyright (C) 2021- Scandit AG. All rights reserved.
 */

import 'package:MatrixScanSimpleSample/scan_result.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_batch.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

import 'main.dart';

class MatrixScanScreen extends StatefulWidget {
  final String title;
  final String licenseKey;

  MatrixScanScreen(this.title, this.licenseKey, {Key? key}) : super(key: key);

  @override
  State<StatefulWidget> createState() => _MatrixScanScreenState(DataCaptureContext.forLicenseKey(licenseKey));
}

class _MatrixScanScreenState extends State<MatrixScanScreen>
    with WidgetsBindingObserver
    implements BarcodeBatchListener {
  final DataCaptureContext _context;

  // Use the world-facing (back) camera.
  Camera? _camera = Camera.defaultCamera;
  late BarcodeBatch _barcodeBatch;
  late DataCaptureView _captureView;

  bool _isPermissionMessageVisible = false;

  List<ScanResult> scanResults = [];

  _MatrixScanScreenState(this._context);

  void _checkPermission() {
    Permission.camera.request().then((status) {
      if (!mounted) return;

      final isGranted = status.isGranted;
      setState(() {
        _isPermissionMessageVisible = !isGranted;
      });

      if (isGranted && _camera != null) {
        _camera!.switchToDesiredState(FrameSourceState.on);
      }
    });
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);

    // Use the recommended camera settings for the BarcodeBatch mode.
    var cameraSettings = BarcodeBatch.createRecommendedCameraSettings();
    // Adjust camera settings - set Full HD resolution.
    cameraSettings.preferredResolution = VideoResolution.fullHd;

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
    _captureView = DataCaptureView.forContext(_context);

    // Add a barcode batch overlay to the data capture view to render the tracked barcodes on
    // top of the video preview. This is optional, but recommended for better visual feedback.
    _captureView.addOverlay(BarcodeBatchBasicOverlay(_barcodeBatch, style: BarcodeBatchBasicOverlayStyle.frame));

    // Set the default camera as the frame source of the context. The camera is off by
    // default and must be turned on to start streaming frames to the data capture context for recognition.
    if (_camera != null) {
      _context.setFrameSource(_camera!);
    }
    _barcodeBatch.isEnabled = true;

    // Set the barcode batch mode as the current mode of the data capture context.
    _context.setMode(_barcodeBatch);
  }

  @override
  Widget build(BuildContext context) {
    Widget child;
    if (_isPermissionMessageVisible) {
      child = Text('No permission to access the camera!',
          style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.black));
    } else {
      var bottomPadding = 48 + MediaQuery.of(context).padding.bottom;
      var containerPadding = defaultTargetPlatform == TargetPlatform.iOS
          ? EdgeInsets.fromLTRB(48, 48, 48, bottomPadding)
          : EdgeInsets.all(48);
      child = Stack(children: [
        _captureView,
        Container(
          alignment: Alignment.bottomCenter,
          padding: containerPadding,
          child: SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                  onPressed: () => _showScanResults(context),
                  style: TextButton.styleFrom(
                      backgroundColor: const Color(scanditBlue),
                      padding: EdgeInsets.all(15),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(6.0), side: BorderSide(color: Colors.white, width: 0))),
                  child: Text(
                    'Done',
                    style: TextStyle(fontSize: 16, color: Colors.white),
                  ))),
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
      child: Scaffold(appBar: AppBar(title: Text(widget.title)), body: child),
    );
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    switch (state) {
      case AppLifecycleState.resumed:
        _checkPermission();
        break;
      default:
        if (_camera != null) {
          _camera!.switchToDesiredState(FrameSourceState.off);
        }
        break;
    }
  }

  // This function is called whenever objects are updated and it's the right place to react to
  // the batch results.
  @override
  Future<void> didUpdateSession(
      BarcodeBatch barcodeBatch, BarcodeBatchSession session, Future<void> getFrameData()) async {
    for (final trackedBarcode in session.addedTrackedBarcodes) {
      scanResults.add(ScanResult(trackedBarcode.barcode.symbology, trackedBarcode.barcode.data ?? ''));
    }
  }

  void _cleanup() {
    WidgetsBinding.instance.removeObserver(this);
    _barcodeBatch.removeListener(this);
    _barcodeBatch.isEnabled = false;
    _camera?.switchToDesiredState(FrameSourceState.off);
    _context.removeAllModes();
  }

  void _showScanResults(BuildContext context) {
    _barcodeBatch.isEnabled = false;
    Navigator.pushNamed(context, "/scanResults", arguments: scanResults).then((value) => _resetScanResults());
  }

  void _resetScanResults() {
    scanResults.clear();
    _barcodeBatch.isEnabled = true;
  }
}
