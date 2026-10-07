// Stubs for citizenwallet/app theme/delay/border painter (no scanning code).
import 'package:flutter/cupertino.dart';
export 'package:flutter/material.dart' show Theme, ThemeData;
import 'package:flutter/material.dart';

class CWColors {
  final CupertinoDynamicColor danger = const CupertinoDynamicColor.withBrightness(
      color: Color(0xFFFF0000), darkColor: Color(0xFFFF0000));
  final CupertinoDynamicColor transparent = const CupertinoDynamicColor.withBrightness(
      color: Color(0x00000000), darkColor: Color(0x00000000));
  final CupertinoDynamicColor uiBackground = const CupertinoDynamicColor.withBrightness(
      color: Color(0xFFFFFFFF), darkColor: Color(0xFF000000));
  final CupertinoDynamicColor uiBackgroundAlt = const CupertinoDynamicColor.withBrightness(
      color: Color(0xFFEEEEEE), darkColor: Color(0xFF111111));
  final CupertinoDynamicColor touchable = const CupertinoDynamicColor.withBrightness(
      color: Color(0xFF0000FF), darkColor: Color(0xFF0000FF));
  final Color white = const Color(0xFFFFFFFF);
}

extension CWThemeData on ThemeData {
  CWColors get colors => CWColors();
}

Future<void> delay(Duration duration) => Future.delayed(duration);

class BorderPainter extends CustomPainter {
  BorderPainter({required this.color});
  final Color color;
  @override
  void paint(Canvas canvas, Size size) {}
  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
