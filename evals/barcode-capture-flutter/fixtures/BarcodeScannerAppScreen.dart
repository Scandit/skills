// SOURCE: https://github.com/HackErSEx3/barcode_scanner_app/blob/a22151f8444c57803dd6f4c08f709a0b99731d28/lib/screens/barcode_scanner_screen.dart
// LICENSE: MIT
// PLUGIN: google_mlkit_barcode_scanning ^0.10.0 + camera ^0.10.5+5
import 'dart:io';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_mlkit_barcode_scanning/google_mlkit_barcode_scanning.dart';

// STUBBED: ../models/{barcode_format_config,scanned_barcode}.dart, ../services/barcode_cache_service.dart, ../widgets/scanner_overlay.dart, history_screen.dart, settings_screen.dart -> stubs/BarcodeScannerAppScreen_stubs.dart
import 'stubs/BarcodeScannerAppScreen_stubs.dart';

class BarcodeScannerScreen extends StatefulWidget {
  final BarcodeFormatConfig formatConfig;

  const BarcodeScannerScreen({super.key, required this.formatConfig});

  @override
  State<BarcodeScannerScreen> createState() => _BarcodeScannerScreenState();
}

class _BarcodeScannerScreenState extends State<BarcodeScannerScreen>
    with WidgetsBindingObserver {
  // ── camera ─────────────────────────────────────────────────────────────────
  CameraController? _cameraController;
  bool _isCameraInitialized = false;
  String? _initError;

  // ── ML Kit ─────────────────────────────────────────────────────────────────
  late BarcodeScanner _barcodeScanner;
  bool _isProcessing = false;
  DateTime? _lastProcessTime;

  // ── state ──────────────────────────────────────────────────────────────────
  List<Barcode> _currentBarcodes = [];
  bool _showingResult = false;

  // ── constants ──────────────────────────────────────────────────────────────
  static const _processingInterval = Duration(milliseconds: 300);
  static const _overlapThreshold = 0.70;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initScanner();
  }

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (_cameraController == null || !_cameraController!.value.isInitialized) {
      return;
    }
    if (state == AppLifecycleState.inactive) {
      _stopStream();
    } else if (state == AppLifecycleState.resumed) {
      _initCamera(_cameraController!.description);
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _stopStream();
    _cameraController?.dispose();
    _barcodeScanner.close();
    super.dispose();
  }

  // ---------------------------------------------------------------------------
  // Initialisation
  // ---------------------------------------------------------------------------

  Future<void> _initScanner() async {
    // Create ML Kit scanner with correct formats
    final formats = widget.formatConfig.allowedFormats;
    _barcodeScanner = BarcodeScanner(formats: formats);

    final cameras = await availableCameras();
    if (cameras.isEmpty) {
      setState(() => _initError = 'No cameras found on this device.');
      return;
    }

    // Prefer back camera
    final backCamera = cameras.firstWhere(
      (c) => c.lensDirection == CameraLensDirection.back,
      orElse: () => cameras.first,
    );

    await _initCamera(backCamera);
  }

  Future<void> _initCamera(CameraDescription camera) async {
    final controller = CameraController(
      camera,
      ResolutionPreset.high,
      enableAudio: false,
      imageFormatGroup: Platform.isAndroid
          ? ImageFormatGroup.nv21
          : ImageFormatGroup.bgra8888,
    );

    try {
      await controller.initialize();
      await controller.setFocusMode(FocusMode.auto);
      if (!mounted) return;

      setState(() {
        _cameraController = controller;
        _isCameraInitialized = true;
      });

      controller.startImageStream(_onCameraImage);
    } catch (e) {
      setState(() => _initError = 'Camera initialisation error: $e');
    }
  }

  void _stopStream() {
    if (_cameraController?.value.isStreamingImages == true) {
      _cameraController!.stopImageStream();
    }
  }

  // ---------------------------------------------------------------------------
  // Image processing
  // ---------------------------------------------------------------------------

  void _onCameraImage(CameraImage image) {
    if (_isProcessing || _showingResult) return;

    final now = DateTime.now();
    if (_lastProcessTime != null &&
        now.difference(_lastProcessTime!) < _processingInterval) return;
    _lastProcessTime = now;

    _processImage(image);
  }

  Future<void> _processImage(CameraImage image) async {
    _isProcessing = true;
    try {
      if (!_isImageQualityGood(image)) return;

      final inputImage = _toInputImage(image);
      if (inputImage == null) return;

      final barcodes = await _barcodeScanner.processImage(inputImage);

      if (!mounted) return;
      setState(() => _currentBarcodes = barcodes);

      if (barcodes.isEmpty) return;

      for (final barcode in barcodes) {
        if (_isBarcodeAccepted(barcode)) {
          await _onBarcodeAccepted(barcode);
          break;
        }
      }
    } catch (_) {
      // Swallow individual frame errors
    } finally {
      _isProcessing = false;
    }
  }

  // ---------------------------------------------------------------------------
  // Quality & alignment helpers
  // ---------------------------------------------------------------------------

  bool _isImageQualityGood(CameraImage image) {
    final bytes = image.planes.first.bytes;
    if (bytes.isEmpty) return false;

    int sum = 0;
    const step = 10;
    int count = 0;
    for (int i = 0; i < bytes.length && count < 100; i += step, count++) {
      sum += bytes[i];
    }
    final avg = count == 0 ? 0 : sum / count;
    return avg > 50 && avg < 220;
  }

  InputImage? _toInputImage(CameraImage image) {
    final camera = _cameraController?.description;
    if (camera == null) return null;

    final rotation =
        InputImageRotationValue.fromRawValue(camera.sensorOrientation) ??
            InputImageRotation.rotation0deg;

    final format = InputImageFormatValue.fromRawValue(image.format.raw);
    if (format == null) return null;

    final plane = image.planes.first;
    return InputImage.fromBytes(
      bytes: plane.bytes,
      metadata: InputImageMetadata(
        size: Size(image.width.toDouble(), image.height.toDouble()),
        rotation: rotation,
        format: format,
        bytesPerRow: plane.bytesPerRow,
      ),
    );
  }

  Rect _buildScanBox(Size screenSize) {
    final boxW = screenSize.width * 0.75;
    final boxH = screenSize.height * 0.28;
    return Rect.fromCenter(
      center: Offset(screenSize.width / 2, screenSize.height / 2),
      width: boxW,
      height: boxH,
    );
  }

  bool _isBarcodeAccepted(Barcode barcode) {
    // Format filter
    if (!widget.formatConfig.accepts(barcode.format)) return false;

    // Alignment
    final box = barcode.boundingBox;
    if (box == null) return false;

    final screenSize = MediaQuery.of(context).size;
    final scanBox = _buildScanBox(screenSize);

    final ix = (box.right.clamp(scanBox.left, scanBox.right) -
            box.left.clamp(scanBox.left, scanBox.right))
        .abs();
    final iy = (box.bottom.clamp(scanBox.top, scanBox.bottom) -
            box.top.clamp(scanBox.top, scanBox.bottom))
        .abs();
    final intersectionArea = ix * iy;
    final barcodeArea = box.width * box.height;
    if (barcodeArea == 0) return false;

    return intersectionArea / barcodeArea >= _overlapThreshold;
  }

  // ---------------------------------------------------------------------------
  // Barcode accepted
  // ---------------------------------------------------------------------------

  Future<void> _onBarcodeAccepted(Barcode barcode) async {
    setState(() => _showingResult = true);
    _stopStream();

    HapticFeedback.mediumImpact();

    final scannedBarcode = ScannedBarcode(
      value: barcode.displayValue ?? barcode.rawValue ?? '',
      format: _formatName(barcode.format),
      scannedAt: DateTime.now(),
      rawBytes: barcode.rawBytes != null
          ? String.fromCharCodes(barcode.rawBytes!)
          : null,
    );

    final error =
        await BarcodeCacheService.instance.save(scannedBarcode);

    if (!mounted) return;
    _showResultDialog(scannedBarcode, error);
  }

  void _showResultDialog(ScannedBarcode barcode, String? cacheError) {
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            Icon(
              cacheError == null ? Icons.check_circle : Icons.info,
              color: cacheError == null ? Colors.green : Colors.orange,
            ),
            const SizedBox(width: 8),
            Text(cacheError == null ? 'Barcode Detected' : 'Already Scanned'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (cacheError != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text(cacheError,
                    style: const TextStyle(color: Colors.orange)),
              ),
            _InfoRow(label: 'Value', value: barcode.value),
            _InfoRow(label: 'Format', value: barcode.format),
            _InfoRow(
                label: 'Time',
                value: _formatTime(barcode.scannedAt)),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              setState(() => _showingResult = false);
              _cameraController?.startImageStream(_onCameraImage);
            },
            child: const Text('Scan Next'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              Navigator.pushReplacement(
                context,
                MaterialPageRoute(builder: (_) => const HistoryScreen()),
              );
            },
            child: const Text('View History'),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  String _formatName(BarcodeFormat format) {
    switch (format) {
      case BarcodeFormat.qrCode:
        return 'QR Code';
      case BarcodeFormat.code128:
        return 'Code 128';
      case BarcodeFormat.code39:
        return 'Code 39';
      case BarcodeFormat.code93:
        return 'Code 93';
      case BarcodeFormat.codabar:
        return 'Codabar';
      case BarcodeFormat.ean13:
        return 'EAN-13';
      case BarcodeFormat.ean8:
        return 'EAN-8';
      case BarcodeFormat.upca:
        return 'UPC-A';
      case BarcodeFormat.upce:
        return 'UPC-E';
      case BarcodeFormat.itf:
        return 'ITF';
      case BarcodeFormat.dataMatrix:
        return 'Data Matrix';
      case BarcodeFormat.pdf417:
        return 'PDF417';
      case BarcodeFormat.aztec:
        return 'Aztec';
      default:
        return 'Unknown';
    }
  }

  String _formatTime(DateTime dt) {
    return '${dt.hour.toString().padLeft(2, '0')}:'
        '${dt.minute.toString().padLeft(2, '0')}:'
        '${dt.second.toString().padLeft(2, '0')}';
  }

  Set<String> get _allowedFormatNames {
    if (widget.formatConfig.allowedFormats
        .contains(BarcodeFormat.all)) {
      return {};
    }
    return widget.formatConfig.allowedFormats
        .map(_formatName)
        .toSet();
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    if (_initError != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Scanner')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(_initError!, style: const TextStyle(color: Colors.red)),
          ),
        ),
      );
    }

    if (!_isCameraInitialized) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    final screenSize = MediaQuery.of(context).size;
    final scanBox = _buildScanBox(screenSize);

    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () => Navigator.pop(context),
        ),
        title: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          decoration: BoxDecoration(
            color: Colors.black54,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            'Mode: ${widget.formatConfig.presetLabel}',
            style: const TextStyle(color: Colors.white, fontSize: 13),
          ),
        ),
      ),
      body: Stack(
        children: [
          // ── camera preview ─────────────────────────────────────────────────
          SizedBox.expand(
            child: CameraPreview(_cameraController!),
          ),

          // ── overlay ────────────────────────────────────────────────────────
          ScannerOverlay(
            scanBox: scanBox,
            barcodes: _currentBarcodes,
            allowedFormats: _allowedFormatNames,
          ),

          // ── instruction bar ────────────────────────────────────────────────
          Positioned(
            top: MediaQuery.of(context).padding.top + kToolbarHeight + 8,
            left: 0,
            right: 0,
            child: Center(
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                decoration: BoxDecoration(
                  color: Colors.black54,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: const Text(
                  'Align barcode within the green box',
                  style: TextStyle(color: Colors.white, fontSize: 13),
                ),
              ),
            ),
          ),

          // ── bottom controls ────────────────────────────────────────────────
          Positioned(
            bottom: 32,
            left: 0,
            right: 0,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _BottomAction(
                  icon: Icons.history,
                  label: 'History',
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                        builder: (_) => const HistoryScreen()),
                  ),
                ),
                _BottomAction(
                  icon: Icons.settings,
                  label: 'Settings',
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                        builder: (_) => const SettingsScreen()),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Helper widgets
// ─────────────────────────────────────────────────────────────────────────────

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;

  const _InfoRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 56,
            child: Text('$label:',
                style: const TextStyle(fontWeight: FontWeight.bold)),
          ),
          Expanded(child: Text(value, softWrap: true)),
        ],
      ),
    );
  }
}

class _BottomAction extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _BottomAction({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
        decoration: BoxDecoration(
          color: Colors.black54,
          borderRadius: BorderRadius.circular(24),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: Colors.white, size: 18),
            const SizedBox(width: 6),
            Text(label,
                style:
                    const TextStyle(color: Colors.white, fontSize: 13)),
          ],
        ),
      ),
    );
  }
}
