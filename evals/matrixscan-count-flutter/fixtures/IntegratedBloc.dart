// Basic MatrixScan Count integration already in place (Flutter, BLoC pattern).
// Evals in this group add features on top of this baseline (capture list,
// custom brushes, status provider, toolbar hiding, hint localization, etc.).

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_count.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

const String licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

class ScannedProduct {
  final String data;
  final Symbology symbology;
  ScannedProduct(this.data, this.symbology);
}

class CountBloc
    implements BarcodeCountListener, BarcodeCountViewListener, BarcodeCountViewUiListener {
  final DataCaptureContext dataCaptureContext =
      DataCaptureContext.forLicenseKey(licenseKey);
  Camera? _camera;
  late final BarcodeCount barcodeCount;

  final List<ScannedProduct> scannedProducts = [];
  final StreamController<List<ScannedProduct>> _controller =
      StreamController<List<ScannedProduct>>.broadcast();

  Stream<List<ScannedProduct>> get scanned => _controller.stream;

  CountBloc() {
    _camera = Camera.defaultCamera;
    _camera?.applySettings(BarcodeCount.createRecommendedCameraSettings());
    if (_camera != null) dataCaptureContext.setFrameSource(_camera!);

    final settings = BarcodeCountSettings()
      ..enableSymbologies({
        Symbology.ean13Upca,
        Symbology.ean8,
        Symbology.code128,
      });

    barcodeCount = BarcodeCount(settings);
    dataCaptureContext.setMode(barcodeCount);
  }

  void didResume() {
    barcodeCount.addListener(this);
    barcodeCount.isEnabled = true;
    Permission.camera.request().then((status) {
      if (status.isGranted) _camera?.switchToDesiredState(FrameSourceState.on);
    });
  }

  void didPause() {
    _camera?.switchToDesiredState(FrameSourceState.off);
    barcodeCount.removeListener(this);
  }

  @override
  Future<void> didScan(BarcodeCount barcodeCount, BarcodeCountSession session,
      Future<FrameData> Function() getFrameData) async {
    for (final barcode in session.recognizedBarcodes) {
      if (barcode.data == null) continue;
      scannedProducts.add(ScannedProduct(barcode.data!, barcode.symbology));
    }
    _controller.add(List.unmodifiable(scannedProducts));
  }

  @override
  Brush? brushForRecognizedBarcode(BarcodeCountView view, TrackedBarcode trackedBarcode) {
    return null;
  }

  @override
  Brush? brushForRecognizedBarcodeNotInList(BarcodeCountView view, TrackedBarcode trackedBarcode) {
    return null;
  }

  @override
  void didTapRecognizedBarcode(BarcodeCountView view, TrackedBarcode trackedBarcode) {}

  @override
  void didTapRecognizedBarcodeNotInList(BarcodeCountView view, TrackedBarcode trackedBarcode) {}

  @override
  void didTapFilteredBarcode(BarcodeCountView view, TrackedBarcode filteredBarcode) {}

  @override
  void didCompleteCaptureList(BarcodeCountView view) {}

  @override
  void didTapListButton(BarcodeCountView view) {}

  @override
  void didTapExitButton(BarcodeCountView view) {}

  @override
  void didTapSingleScanButton(BarcodeCountView view) {}

  Future<void> resetSession() async {
    scannedProducts.clear();
    await barcodeCount.clearAdditionalBarcodes();
    await barcodeCount.reset();
    barcodeCount.addListener(this);
  }

  void dispose() {
    _camera?.switchToDesiredState(FrameSourceState.off);
    barcodeCount.removeListener(this);
    dataCaptureContext.removeAllModes();
    _controller.close();
  }
}

class CountPage extends StatefulWidget {
  const CountPage({super.key});

  @override
  State<CountPage> createState() => _CountPageState();
}

class _CountPageState extends State<CountPage> with WidgetsBindingObserver {
  final CountBloc _bloc = CountBloc();
  final List<ScannedProduct> _items = [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _bloc.scanned.listen((items) {
      setState(() {
        _items
          ..clear()
          ..addAll(items);
      });
    });
    _bloc.didResume();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        bottom: false,
        child: BarcodeCountView.forContextWithModeAndStyle(
          _bloc.dataCaptureContext,
          _bloc.barcodeCount,
          BarcodeCountViewStyle.icon,
        )
          ..uiListener = _bloc
          ..listener = _bloc,
      ),
    );
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    switch (state) {
      case AppLifecycleState.resumed:
        _bloc.didResume();
        break;
      default:
        _bloc.didPause();
        break;
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _bloc.dispose();
    super.dispose();
  }
}
