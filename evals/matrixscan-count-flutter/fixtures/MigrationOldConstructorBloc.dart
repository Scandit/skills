// MatrixScan Count BLoC using the pre-7.6 async factory constructor.
// This fixture is the input for migration eval 1: upgrade to the
// BarcodeCount(settings) constructor introduced in Flutter SDK 7.6.

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

class CountBloc implements BarcodeCountListener {
  late DataCaptureContext dataCaptureContext;
  late BarcodeCount barcodeCount;
  Camera? _camera;

  final List<ScannedProduct> scannedProducts = [];
  final StreamController<List<ScannedProduct>> _controller =
      StreamController<List<ScannedProduct>>.broadcast();

  Stream<List<ScannedProduct>> get scanned => _controller.stream;

  // Pre-7.6 pattern: async initialisation via the factory constructor.
  // BarcodeCount.forDataCaptureContext automatically registers the mode
  // with the context — no explicit setMode() call is needed.
  Future<void> init() async {
    dataCaptureContext =
        DataCaptureContext.forLicenseKey(licenseKey);

    _camera = Camera.defaultCamera;
    if (_camera != null) dataCaptureContext.setFrameSource(_camera!);

    final settings = BarcodeCountSettings()
      ..enableSymbologies({
        Symbology.ean13Upca,
        Symbology.ean8,
        Symbology.code128,
      });

    // Old async factory: must be awaited; context passed as first argument.
    barcodeCount = await BarcodeCount.forDataCaptureContext(
        dataCaptureContext, settings);
    barcodeCount.addListener(this);
  }

  void didResume() {
    barcodeCount.isEnabled = true;
    Permission.camera.request().then((status) {
      if (status.isGranted) _camera?.switchToDesiredState(FrameSourceState.on);
    });
  }

  void didPause() {
    _camera?.switchToDesiredState(FrameSourceState.off);
  }

  @override
  Future<void> didScan(
    BarcodeCount barcodeCount,
    BarcodeCountSession session,
    Future<FrameData> Function() getFrameData,
  ) async {
    for (final barcode in session.recognizedBarcodes) {
      if (barcode.data == null) continue;
      scannedProducts.add(ScannedProduct(barcode.data!, barcode.symbology));
    }
    _controller.add(List.unmodifiable(scannedProducts));
  }

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
  bool _ready = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _bloc.init().then((_) {
      setState(() => _ready = true);
      _bloc.didResume();
    });
    _bloc.scanned.listen((items) {
      setState(() {
        _items
          ..clear()
          ..addAll(items);
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    if (!_ready) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        bottom: false,
        child: BarcodeCountView.forContextWithModeAndStyle(
          _bloc.dataCaptureContext,
          _bloc.barcodeCount,
          BarcodeCountViewStyle.icon,
        ),
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
