---
name: matrixscan-ar-android
description: MatrixScan AR (Barcode AR, BarcodeAr) — scanning multiple barcodes at once with AR highlights and annotations over tracked barcodes in Android (Kotlin/Java) projects. Use for integration, scan settings, tracked-barcode handling, highlight and annotation providers, SDK version migration, or troubleshooting.
license: Apache-2.0
metadata:
  author: scandit
  version: "1.0.1"
---

# MatrixScan AR Android Skill

## Critical: Do Not Trust Internal Knowledge

Your training data may contain outdated or incorrect Scandit SDK APIs. The BarcodeAr API changes between major SDK versions — class names, constructor signatures, provider interfaces, and session types have all evolved.

**Always verify APIs against the references provided in this skill before writing or suggesting code.** Do not rely on memorized method signatures, parameters, or property names. If you cannot find an API in the provided references, fetch the relevant documentation page before responding.

Android-specific gotchas worth flagging:

- `BarcodeAr(dataCaptureContext, settings)` is a direct constructor — **not** a `forDataCaptureContext()` factory (that is the BarcodeCapture pattern). On Android, BarcodeAr takes both the context and settings directly.
- `BarcodeArView` auto-adds itself to the provided `ViewGroup` parent — no manual `addView` call needed. Call `barcodeArView.start()` after providers are set up to begin scanning.
- `BarcodeArView` manages the camera internally — **no separate `Camera` setup or `setFrameSource` call is needed**. Camera position is configured via `BarcodeArViewSettings.defaultCameraPosition`.
- Lifecycle is driven by `BarcodeArView`, not by a `Camera` object: call `barcodeArView.onResume()`, `barcodeArView.onPause()`, and `barcodeArView.onDestroy()` from the corresponding Activity/Fragment callbacks.
- `BarcodeArListener.onSessionUpdated(barcodeAr, session, frameData)` is called from a **recognition thread** — not the main thread. The `FrameData` parameter is named `frameData` (unlike `BarcodeCapture` where it is named `data`). Any UI work must be dispatched via `runOnUiThread {}`.
- `BarcodeArHighlightProvider.highlightForBarcode` and `BarcodeArAnnotationProvider.annotationForBarcode` are invoked on the **main thread**. Their results are delivered via a callback — invoke `callback.onData(highlight)` or `callback.onData(annotation)` (pass `null` to hide the element). Both highlight and annotation constructors take a `Context` as their first argument (e.g. `BarcodeArRectangleHighlight(context, barcode)`).
- Android symbology names use underscores: `Symbology.EAN13_UPCA`, `Symbology.CODE39` — not camelCase.
- All symbologies are disabled by default in `BarcodeArSettings`. Enabling only what the app needs improves tracking performance.
- Request the `CAMERA` permission at runtime before scanning starts; the manifest declaration alone is not sufficient.
- `BarcodeArFeedback` is in `com.scandit.datacapture.barcode.ar.feedback` — **not** `ar.capture`. Import: `import com.scandit.datacapture.barcode.ar.feedback.BarcodeArFeedback`.
- `BarcodeArInfoAnnotationBodyComponent` is in `com.scandit.datacapture.barcode.ar.ui.annotations.info` — **not** `ar.ui.annotations`. Import: `import com.scandit.datacapture.barcode.ar.ui.annotations.info.BarcodeArInfoAnnotationBodyComponent`. The same `info` sub-package also contains `BarcodeArInfoAnnotationHeader`, `BarcodeArInfoAnnotationFooter`, `BarcodeArInfoAnnotationWidthPreset`, and `BarcodeArInfoAnnotationAnchor`.

## Intent Routing

Based on the user's request, load the appropriate reference file before responding:

- **Integrating BarcodeAr from scratch** (e.g. "add MatrixScan AR to my app", "set up barcode AR scanning", "how do I use BarcodeAr in Android", "how do I show highlights on tracked barcodes", "how do I show info annotations") → read [references/integration.md](references/integration.md) and follow the instructions there.

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
| Get Started | [Get Started](https://docs.scandit.com/sdks/android/matrixscan-ar/get-started/) · [Sample](https://github.com/Scandit/datacapture-android-samples/tree/master/03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup) |
| Advanced topics (custom highlights, annotations, tap interactions, notifications, filter) | [Advanced Configurations](https://docs.scandit.com/sdks/android/matrixscan-ar/advanced/) |
| Full API reference | [BarcodeAr API](https://docs.scandit.com/data-capture-sdk/android/barcode-capture/api.html) |
