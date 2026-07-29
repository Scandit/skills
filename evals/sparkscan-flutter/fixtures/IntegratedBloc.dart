// Basic SparkScan integration already in place (Flutter, v8 API, BLoC pattern).
// Evals in this group add features on top of this baseline (custom feedback,
// custom trigger button, UI customization, lifecycle disposal, etc.).

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_spark_scan.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

const String licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

class ScannedProduct {
  final String data;
  final Symbology symbology;
  ScannedProduct(this.data, this.symbology);
}

class HomeBloc implements SparkScanListener {
  final DataCaptureContext dataCaptureContext =
      DataCaptureContext.forLicenseKey(licenseKey);
  late final SparkScan sparkScan;
  late final SparkScanViewSettings sparkScanViewSettings;

  final List<ScannedProduct> scannedProducts = [];
  final StreamController<ScannedProduct> _scansController =
      StreamController<ScannedProduct>.broadcast();

  Stream<ScannedProduct> get scanned => _scansController.stream;

  HomeBloc() {
    final settings = SparkScanSettings()
      ..enableSymbologies({
        Symbology.ean13Upca,
        Symbology.code128,
        Symbology.qr,
      });

    sparkScan = SparkScan(settings: settings);
    sparkScan.addListener(this);

    sparkScanViewSettings = SparkScanViewSettings();
  }

  @override
  Future<void> didScan(
    SparkScan sparkScan,
    SparkScanSession session,
    Future<FrameData> Function() getFrameData,
  ) async {
    final barcode = session.newlyRecognizedBarcode;
    if (barcode == null) return;
    final product = ScannedProduct(barcode.data ?? '', barcode.symbology);
    scannedProducts.add(product);
    _scansController.add(product);
  }

  @override
  Future<void> didUpdateSession(
    SparkScan sparkScan,
    SparkScanSession session,
    Future<FrameData> Function() getFrameData,
  ) async {}
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> with WidgetsBindingObserver {
  final HomeBloc _bloc = HomeBloc();
  final List<ScannedProduct> _items = [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    Permission.camera.request();
    _bloc.scanned.listen((product) {
      setState(() => _items.add(product));
    });
  }

  @override
  Widget build(BuildContext context) {
    final sparkScanView = SparkScanView.forContext(
      _buildBody(),
      _bloc.dataCaptureContext,
      _bloc.sparkScan,
      _bloc.sparkScanViewSettings,
    );

    return Scaffold(
      appBar: AppBar(title: const Text('Scanner')),
      body: SafeArea(child: sparkScanView),
    );
  }

  Widget _buildBody() {
    return ListView.builder(
      itemCount: _items.length,
      itemBuilder: (_, i) => ListTile(title: Text(_items[i].data)),
    );
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }
}
