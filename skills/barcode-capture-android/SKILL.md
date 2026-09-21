---
name: barcode-capture-android
description: Scandit Barcode Capture (`BarcodeCapture`) in native Android (Kotlin/Java) projects — the low-level, full-control single-barcode scanning mode (BarcodeCapture + DataCaptureView + overlay), without the pre-built SparkScan UI. Use for integration, symbology and scan settings, result handling, overlay customization, SDK version migration (v6→v7→v8), replacing third-party scanners (ZXing, ML Kit), or troubleshooting.
license: Apache-2.0
metadata:
  author: scandit
  version: "1.0.1"
---

# BarcodeCapture Android Skill

## Critical: Do Not Trust Internal Knowledge

Your training data may contain outdated or incorrect Scandit SDK APIs. The BarcodeCapture API changes significantly between major SDK versions — properties get renamed, removed, or restructured.

**Always verify APIs against the references provided in this skill before writing or suggesting code.** Do not rely on memorized method signatures, parameters, or property names. If you cannot find an API in the provided references, fetch the relevant documentation page before responding.

Android-specific gotchas worth flagging:
- `Camera.getDefaultCamera(BarcodeCapture.createRecommendedCameraSettings())` passes the recommended camera settings directly into the `getDefaultCamera()` call — there is no separate `applySettings` call needed.
- `codeDuplicateFilter` is a `TimeInterval` — **not** an `Int` or `Double`. Use `TimeInterval.millis(500)` (import `com.scandit.datacapture.core.time.TimeInterval`). Writing `codeDuplicateFilter = 0.5` or `codeDuplicateFilter = 500` is a type error.
- The listener callback on Android is `onBarcodeScanned(barcodeCapture, session, data)` — not `didScan` (that is the Flutter/iOS name). You must also implement `onSessionUpdated`, `onObservationStarted`, and `onObservationStopped`. The `FrameData` parameter is named `data`, not `frameData`.
- `onBarcodeScanned` is called on a background thread. Any UI update must be dispatched via `runOnUiThread {}`.
- Call `barcodeCapture.isEnabled = false` at the top of `onBarcodeScanned` before doing any work to prevent duplicate or racing scans. Re-enable with `barcodeCapture.isEnabled = true` when the app is ready to scan again.
- Android symbology names use underscores: `Symbology.EAN13_UPCA`, `Symbology.CODE39`, `Symbology.INTERLEAVED_TWO_OF_FIVE` — not camelCase.
- Turn the camera off in `onPause()` and re-enable in `onResume()`. The camera must not be active while the app is backgrounded.
- Request the `CAMERA` permission at runtime before the first scan; the manifest declaration alone is not sufficient.
- `DataCaptureView.newInstance(this, dataCaptureContext)` creates the camera preview widget. In an Activity, pass it to `setContentView(dataCaptureView)`. In a Fragment, add it to the view hierarchy programmatically.

## Intent Routing

Based on the user's request, load the appropriate reference file before responding:

- **Integrating BarcodeCapture from scratch, configuring settings, customizing feedback, adding a viewfinder, handling scans, or doing async work after a scan** (e.g. "add BarcodeCapture to my app", "set up barcode scanning", "how do I use BarcodeCapture in Android", "filter duplicate scans", "suppress the beep", "add a viewfinder", "disable scanning while I look up the barcode") → read [references/integration.md](references/integration.md) and follow the instructions there.
- **Migrating or upgrading an existing BarcodeCapture integration** (e.g. "upgrade from v6 to v7", "migrate my BarcodeCapture", "bump the Scandit SDK to v8", "what changed between SDK versions") → read [references/migration.md](references/migration.md) and follow the instructions there.
- **Replacing a third-party barcode scanner with BarcodeCapture** (e.g. "replace my ZXing scanner with BarcodeCapture", "migrate from ML Kit barcode scanning to Scandit", "switch from [library] to BarcodeCapture") → read [references/third-party-migration.md](references/third-party-migration.md) and follow the instructions there.

## API Usage Policy

Only use APIs that are explicitly documented in the Scandit references below. Do not invent or guess method signatures, parameters, or property names. If unsure whether an API exists or how it is called — or if a compile error occurs — fetch the relevant reference page before responding. Do not tell the user to check the docs themselves. After answering, always include the relevant link so the user can explore further.

**Never construct or guess documentation URLs.** When you need a specific class or property's API page:
1. First check whether the page you already fetched contains a direct hyperlink to it — topic pages link directly to relevant API symbols. Always request links alongside content in your fetch prompt.
2. If no direct link was found, fetch the API index (see **Full API reference** in the table below), extract the actual link from it, and follow that.

URL structures can vary (e.g. `api/ui/` subdirectory) and guessing will lead to 404s.

## Licence key

Scanning needs a Scandit licence key. For this skill the licence product is `native` and the licence platform is `android`.

Work through these in order — never block the user on MCP:

1. **The Scandit MCP server is connected** — call `ensure_scanner_setup` with product `native` and platforms `android`, then run the command `get_license_env_command` returns, which writes the key into the project's `.env`. Show at most a masked preview in chat; never print a full key.
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
| Get Started | [Get Started](https://docs.scandit.com/sdks/android/barcode-capture/get-started/) · [Sample](https://github.com/Scandit/datacapture-android-samples/tree/master/01_Single_Scanning_Samples/02_Barcode_Scanning_with_Low_Level_API/BarcodeCaptureSimpleSample) |
| Advanced topics (custom feedback, viewfinders, location selection, scan intention, composite codes) | [Advanced Configurations](https://docs.scandit.com/sdks/android/barcode-capture/advanced/) |
| Migration between major SDK versions | [6 → 7](https://docs.scandit.com/sdks/android/migrate-6-to-7/) · [7 → 8](https://docs.scandit.com/sdks/android/migrate-7-to-8/) |
| Full API reference | [BarcodeCapture API](https://docs.scandit.com/data-capture-sdk/android/barcode-capture/api.html) |
