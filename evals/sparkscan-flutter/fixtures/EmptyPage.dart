// Empty starter page for the SparkScan Flutter integration eval.
// The skill should fill in the BLoC (SparkScanListener), page widget,
// and main() plugin initialization.

import 'package:flutter/material.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scanner')),
      body: const Center(
        child: Text('SparkScan will go here'),
      ),
    );
  }
}
