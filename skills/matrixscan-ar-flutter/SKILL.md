---
name: matrixscan-ar-flutter
description: MatrixScan AR (Barcode AR, BarcodeAr) in Flutter projects (scandit_flutter_datacapture_barcode_ar) — scanning multiple barcodes at once with AR highlights and annotations over tracked barcodes. Use for integration, scan settings, highlight and annotation providers, migration from BarcodeBatch/BarcodeTracking, or troubleshooting.
license: Apache-2.0
metadata:
  author: scandit
  version: "1.0.1"
---

# MatrixScan AR Flutter Skill

## Critical: Do Not Trust Internal Knowledge

Your training data may contain outdated or incorrect Scandit SDK APIs. The BarcodeAr API changes between major SDK versions — class names, constructor signatures, provider interfaces, and the Flutter plugin import path have all evolved.

**Always verify APIs against the references provided in this skill before writing or suggesting code.** Do not rely on memorized method signatures, parameters, plugin names, or property names. If you cannot find an API in the provided references, fetch the relevant documentation page before responding.

Flutter-specific gotchas worth flagging:

- `await ScanditFlutterDataCaptureBarcode.initialize()` **must** be called (and awaited) in `main()` before `runApp(...)`, after `WidgetsFlutterBinding.ensureInitialized()`. Forgetting this yields a platform-channel error that can look unrelated to initialization.
- `BarcodeArView` is a Flutter `StatefulWidget`. Create it once in `initState()` (not in `build()`), store it as a field, and embed it in the widget tree. Creating it inside `build()` tears it down and rebuilds the native view on every rebuild.
- The highlight and annotation providers (`BarcodeArHighlightProvider`, `BarcodeArAnnotationProvider`) return `Future<BarcodeArHighlight?>` and `Future<BarcodeArAnnotation?>` respectively. These callbacks are async — do not return plain values.
- `BarcodeArCustomHighlight` and `BarcodeArCustomAnnotation` use Flutter `Widget` children that are serialized as snapshots. Animated widgets are captured as a still frame at render time — they will not animate inside the AR overlay.
- The BLoC (or equivalent controller) owns `DataCaptureContext`, `BarcodeAr`, and the camera lifecycle. The `State` class holds the `BarcodeArView` and implements the provider interfaces.
- Camera permission is required on both iOS (`NSCameraUsageDescription` in `ios/Runner/Info.plist`) and Android (runtime request via `permission_handler` — the plugin declares the manifest permission automatically).
- The barcode AR import is `scandit_flutter_datacapture_barcode_ar` — a separate barrel file from the main `scandit_flutter_datacapture_barcode` import.
- `Symbology` enum values use **lowerCamelCase** in Dart: `Symbology.code128`, `Symbology.ean13Upca`, `Symbology.code39`, `Symbology.qr`, `Symbology.dataMatrix`. Do not write `Symbology.Code128` / `Symbology.EAN13UPCA` — that's the JS/TS form and will not compile in Dart.

## Intent Routing

Based on the user's request, load the reference file before responding:

- **Integrating BarcodeAr from scratch** (e.g. "add MatrixScan AR to my app", "set up barcode AR scanning", "how do I use BarcodeAr in Flutter", "how do I show highlights on tracked barcodes", "how do I show info annotations") → read [references/integration.md](references/integration.md) and follow the instructions there.

- **Migrating from BarcodeBatch / BarcodeTracking to BarcodeAr** (e.g. "migrate from BarcodeBatch", "convert BarcodeBatch to BarcodeAr", "move from MatrixScan to MatrixScan AR", "replace BarcodeTracking with BarcodeAr", "upgrade my old MatrixScan code to AR") → read [references/migration.md](references/migration.md) and follow the 10-step migration guide there.

## API Usage Policy

Only use APIs that are explicitly documented in the Scandit references below. Do not invent or guess method signatures, parameters, property names, or imports. If unsure whether an API exists or how it is called — or if an analyzer / runtime error occurs — fetch the relevant reference page before responding. Do not tell the user to check the docs themselves. After answering, always include the relevant link so the user can explore further.

**Never construct or guess documentation URLs.** When you need a specific class or property's API page:
1. First check whether the page you already fetched contains a direct hyperlink to it — topic pages link directly to relevant API symbols.
2. If no direct link was found, fetch the API index (see **Full API reference** in the table below), extract the actual link from it, and follow that.

URL structures vary across SDK versions and package paths (e.g. `api/ui/` subdirectory) and guessing will lead to 404s.

## Framework variant policy

Flutter apps use many state-management patterns (StatefulWidget, BLoC, Provider, Riverpod). Examples in this skill use the **BLoC pattern** because it matches the official `MatrixScanARSimpleSample`, keeps the scan pipeline cleanly separated from the widget tree, and composes well with the camera lifecycle. If the target project already uses a different pattern (Provider, Riverpod, GetX, plain StatefulWidget), keep the BarcodeAr wiring conceptually the same (one owner holds `DataCaptureContext`, `BarcodeAr`, and exposes session data to the UI) and port the code snippets into the project's existing convention — do not rewrite the project's state management.

## Licence key

Scanning needs a Scandit licence key. For this skill the licence product is `native` and the licence platforms are `ios` and `android`.

Work through these in order — never block the user on MCP:

1. **The Scandit MCP server is connected** — call `ensure_scanner_setup` with product `native` and platforms `ios` and `android`, then run the command `get_license_env_command` returns, which writes the key into the project's `.env`. Show at most a masked preview in chat; never print a full key.
2. **It is not connected** — offer to connect it once, then continue from step 1:
   - Claude Code: `claude mcp add --transport http scandit https://ssl.scandit.com/mcp`
   - Cursor: add `{"mcpServers": {"scandit": {"url": "https://ssl.scandit.com/mcp"}}}` to `~/.cursor/mcp.json`
   - VS Code: add `{"servers": {"scandit": {"type": "http", "url": "https://ssl.scandit.com/mcp"}}}` to the MCP user configuration

   Authentication is browser-based, so it is **not supported headless or in CI**. The server provisions **trial** keys only; it never creates, revokes, or modifies production licences.
3. **The user declines, or has no MCP client** — they generate a key themselves at <https://ssl.scandit.com> (no account yet: <https://ssl.scandit.com/dashboard/sign-up?p=test>) and paste it in.

## References

Direct users to the right resource based on their question:

| Topic | Resource |
|---|---|
| Flutter integration | [Get Started](https://docs.scandit.com/sdks/flutter/matrixscan-ar/get-started/) · [Sample](https://github.com/Scandit/datacapture-flutter-samples/tree/master/03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanARSimpleSample) |
| Full API reference | [BarcodeAr API](https://docs.scandit.com/data-capture-sdk/flutter/barcode-capture/api.html) |
