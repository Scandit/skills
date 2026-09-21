---
name: sparkscan-flutter
description: SparkScan single-barcode scanning with the pre-built scanning UI (`SparkScanView` widget) in Flutter (Dart) projects. Use for integration, scan settings, result handling, UI customization, SDK version migration, or troubleshooting.
license: Apache-2.0
metadata:
  author: scandit
  version: "1.0.1"
---

# SparkScan Flutter Skill

## Critical: Do Not Trust Internal Knowledge

Your training data may contain outdated or incorrect Scandit SDK APIs. The SparkScan API changes significantly between major SDK versions — properties get renamed, removed, or restructured, and the Flutter plugin surface (imports, plugin initialization, pub packages) has also evolved.

**Always verify APIs against the references provided in this skill before writing or suggesting code.** Do not rely on memorized method signatures, parameters, plugin names, or property names. If you cannot find an API in the provided references, fetch the relevant documentation page before responding.

Flutter-specific gotchas worth flagging:
- `await ScanditFlutterDataCaptureBarcode.initialize()` **must** be called (and awaited) in `main()` before `runApp(...)`, after `WidgetsFlutterBinding.ensureInitialized()`. Forgetting this yields a platform-channel error that can look unrelated to initialization.
- `SparkScanView` is a Flutter `StatefulWidget` that **wraps** a child widget — it is not a pure native overlay. The child widget renders underneath the native scanning controls. Do not instruct users to stack `SparkScanView` separately from their normal widget tree.
- `flutter pub get` must be run after every package version change. On iOS, the Podfile resolves transitively — no manual pod install needed unless the user has a custom setup.
- Camera permission is required on both iOS (`NSCameraUsageDescription` in `ios/Runner/Info.plist`) and Android (runtime request via `permission_handler` — the plugin declares the manifest permission automatically).

## Intent Routing

Based on the user's request, load the appropriate reference file before responding:

- **Integrating SparkScan from scratch** (e.g. "add SparkScan to my app", "set up barcode scanning", "how do I use SparkScan in Flutter", "how do I handle feedback in SparkScan") → read [references/integration.md](references/integration.md) and follow the instructions there.
- **Migrating or upgrading an existing SparkScan integration** (e.g. "upgrade from v6 to v7", "migrate my SparkScan", "bump the Scandit packages to v8", "what changed between SDK versions") → read [references/migration.md](references/migration.md) and follow the instructions there.

## API Usage Policy

Only use APIs that are explicitly documented in the Scandit references below. Do not invent or guess method signatures, parameters, property names, or imports. If unsure whether an API exists or how it is called — or if an analyzer / runtime error occurs — fetch the relevant reference page before responding. Do not tell the user to check the docs themselves. After answering, always include the relevant link so the user can explore further.

**Never construct or guess documentation URLs.** When you need a specific class or property's API page:
1. First check whether the page you already fetched (e.g. the Advanced Configurations page) contains a direct hyperlink to it — topic pages link directly to relevant API symbols. Always request links alongside content in your fetch prompt.
2. If no direct link was found, fetch the API index (see **Full API reference** in the table below), extract the actual link from it, and follow that.

URL structures vary across SDK versions and package paths (e.g. `api/ui/` subdirectory) and guessing will lead to 404s.

## Framework variant policy

Flutter apps use many state-management patterns (StatefulWidget, BLoC, Provider, Riverpod). Examples in this skill use the **BLoC pattern** because it matches the official `ListBuildingSample`, keeps the scan pipeline cleanly separated from the widget tree, and composes well with the camera lifecycle. If the target project already uses a different pattern (Provider, Riverpod, GetX, plain StatefulWidget), keep the SparkScan wiring conceptually the same (one owner holds `DataCaptureContext`, `SparkScan`, and exposes scan events to the UI) and port the code snippets into the project's existing convention — do not rewrite the project's state management.

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
| Flutter integration | [Get Started](https://docs.scandit.com/sdks/flutter/sparkscan/get-started/) · [Sample](https://github.com/Scandit/datacapture-flutter-samples/tree/master/01_Single_Scanning_Samples/01_Barcode_Scanning_with_Pre_Built_UI/ListBuildingSample) |
| Advanced topics (custom feedback, hardware triggers, scanning modes, UI customization) | [Advanced Configurations](https://docs.scandit.com/sdks/flutter/sparkscan/advanced/) |
| Migration between major SDK versions | [6 → 7](https://docs.scandit.com/sdks/flutter/migrate-6-to-7/) · [7 → 8](https://docs.scandit.com/sdks/flutter/migrate-7-to-8/) |
| Full API reference | [SparkScan API](https://docs.scandit.com/data-capture-sdk/flutter/barcode-capture/api.html) |
