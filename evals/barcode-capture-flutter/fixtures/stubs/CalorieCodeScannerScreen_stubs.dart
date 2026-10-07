// Stubs for roddhc/caloriecode local models/providers/services (no scanning code).
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

class Product {}

class FoodCodeProvider extends ChangeNotifier {
  String? activeFoodCode;
}

class OpenFoodFactsService {
  Future<Product?> fetchProduct(String barcode) async => null;
}

class DesignColors {
  static Color getDangerRed(BuildContext context) => Colors.red;
  static Color getPrimaryBlue(BuildContext context) => Colors.blue;
  static Color getTextSecondaryColor(BuildContext context) => Colors.grey;
}

class ResultScreen extends StatelessWidget {
  const ResultScreen({super.key, required this.barcode, required this.product});
  final String barcode;
  final Product product;
  @override
  Widget build(BuildContext context) => const SizedBox.shrink();
}
