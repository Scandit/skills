// Stubs for lachouettecoop/InventoryCoop local widgets (no scanning code).
import 'package:flutter/material.dart';

class ScannerErrorWidget extends StatelessWidget {
  const ScannerErrorWidget({super.key, required this.error});
  final Object error;
  @override
  Widget build(BuildContext context) => const SizedBox.shrink();
}

class ToggleFlashlightButton extends StatelessWidget {
  const ToggleFlashlightButton({super.key, required this.controller});
  final Object controller;
  @override
  Widget build(BuildContext context) => const SizedBox.shrink();
}

class SwitchCameraButton extends StatelessWidget {
  const SwitchCameraButton({super.key, required this.controller});
  final Object controller;
  @override
  Widget build(BuildContext context) => const SizedBox.shrink();
}
