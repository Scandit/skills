// Stubs for 0xteamCookie/echo AuthService, AppState, UserRole and BeaconColors (no scanning code).
import 'package:flutter/material.dart';

enum UserRole { user, rescuer }

class AppState {
  static final AppState _instance = AppState._();
  AppState._();
  factory AppState() => _instance;
  final ValueNotifier<UserRole> role = ValueNotifier<UserRole>(UserRole.user);
}

class AuthService {
  static Future<bool> verifyAndSaveToken(String token) async => true;
}

class BeaconColors {
  static const Color background = Color(0xFF000000);
}
