// SOURCE: https://github.com/roddhc/caloriecode/blob/19443cb347330434fc017c1753359b101b5f3ca6/lib/screens/scanner_screen.dart
// LICENSE: MIT
// PLUGIN: mobile_scanner ^7.2.0
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:provider/provider.dart';
// STUBBED: ../models/product.dart, ../providers/food_code_provider.dart, ../services/openfoodfacts_service.dart, ../utils/design_colors.dart, result_screen.dart -> stubs/CalorieCodeScannerScreen_stubs.dart
import 'stubs/CalorieCodeScannerScreen_stubs.dart';

class ScannerScreen extends StatefulWidget {
  const ScannerScreen({super.key});

  @override
  State<ScannerScreen> createState() => _ScannerScreenState();
}

class _ScannerScreenState extends State<ScannerScreen> {
  final MobileScannerController cameraController = MobileScannerController();
  bool _isNavigating = false;
  bool _isGlowing = false;

  void _onDetect(BarcodeCapture capture) async {
    if (_isNavigating) return;

    final foodCodeProvider = Provider.of<FoodCodeProvider>(context, listen: false);
    if (foodCodeProvider.activeFoodCode == null) {
      setState(() {
        _isNavigating = true;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Please select a Food Code first.')),
        );
      }
      Future.delayed(const Duration(seconds: 2), () {
        if (mounted) {
          setState(() {
            _isNavigating = false;
          });
        }
      });
      return;
    }

    final List<Barcode> barcodes = capture.barcodes;
    if (barcodes.isNotEmpty && barcodes.first.rawValue != null) {
      final String barcode = barcodes.first.rawValue!;

      // Trigger glow and haptic
      setState(() {
        _isGlowing = true;
        _isNavigating = true;
      });
      HapticFeedback.lightImpact();

      Future.delayed(const Duration(milliseconds: 100), () {
        if (mounted) {
          setState(() {
            _isGlowing = false;
          });
        }
      });

      cameraController.stop();

      // Fetch product
      final offService = OpenFoodFactsService();
      Product? product;
      try {
        product = await offService.fetchProduct(barcode);
      } catch (e) {
        if (mounted) {
          _showErrorModal('Couldn\'t fetch product details. Check your internet and try again.');
          return;
        }
      }

      if (product == null && mounted) {
        _showNotFoundModal(barcode);
        return;
      }

      if (mounted && product != null) {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => ResultScreen(barcode: barcode, product: product!),
          ),
        ).then((_) {
          // When coming back, resume camera
          if (mounted) {
            setState(() {
              _isNavigating = false;
            });
            cameraController.start();
          }
        });
      }
    }
  }

  void _showErrorModal(String message) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: const Text('Error'),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              setState(() {
                _isNavigating = false;
              });
              cameraController.start();
            },
            child: const Text('Back to Scan'),
          ),
        ],
      ),
    );
  }

  void _showNotFoundModal(String barcode) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: const Text('Product Not Found'),
        content: const Text('Product not found in database. Do you want to manually enter details?'),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              setState(() {
                _isNavigating = false;
              });
              cameraController.start();
            },
            child: const Text('No'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.pop(context);
              // TODO: Navigate to manual entry screen
              setState(() {
                _isNavigating = false;
              });
              cameraController.start();
            },
            child: const Text('Yes'),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    cameraController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          MobileScanner(
            controller: cameraController,
            onDetect: _onDetect,
            errorBuilder: (context, error) {
              return Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.error,
                      color: DesignColors.getDangerRed(context),
                      size: 64,
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Camera error: ${error.errorCode}',
                      style: TextStyle(color: DesignColors.getDangerRed(context)),
                    ),
                  ],
                ),
              );
            },
          ),
          // Barcode detection guide overlay
          Center(
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 100),
              width: 250,
              height: 250,
              decoration: BoxDecoration(
                border: Border.all(
                  color: _isGlowing ? Colors.white : Colors.white.withOpacity(0.5),
                  width: _isGlowing ? 4 : 2,
                ),
                borderRadius: BorderRadius.circular(16),
                boxShadow: _isGlowing
                    ? [
                        BoxShadow(
                          color: Colors.white.withOpacity(0.8),
                          blurRadius: 20,
                          spreadRadius: 5,
                        )
                      ]
                    : null,
              ),
            ),
          ),
        ],
      ),
      bottomSheet: BottomSheet(
        onClosing: () {},
        builder: (context) {
          return Container(
            width: double.infinity,
            padding: const EdgeInsets.all(24.0),
            decoration: BoxDecoration(
              color: DesignColors.getPrimaryBlue(context).withOpacity(0.1),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.05),
                  blurRadius: 10,
                  offset: const Offset(0, -2),
                ),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  '🧬 Code: Cut Mode',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: DesignColors.getPrimaryBlue(context),
                  ),
                ),
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  height: 48, // 48pt+ touch target
                  child: FilledButton.icon(
                    style: FilledButton.styleFrom(
                      backgroundColor: DesignColors.getPrimaryBlue(context),
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                    onPressed: () {
                      HapticFeedback.lightImpact();
                      // Manual scan logic or feedback if needed
                    },
                    icon: const Icon(Icons.search, size: 20),
                    label: const Text(
                      'Scan Food',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'or tap to search',
                  style: TextStyle(
                    fontSize: 14,
                    color: DesignColors.getTextSecondaryColor(context),
                  ),
                ),
                // Add some bottom padding for the safe area if needed
                const SizedBox(height: 8),
              ],
            ),
          );
        },
      ),
    );
  }
}
