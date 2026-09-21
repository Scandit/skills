---
name: matrixscan-batch-android
description: MatrixScan Batch (MatrixScan, BarcodeBatch, legacy BarcodeTracking) — tracking and scanning multiple barcodes at once in Android (Kotlin/Java) projects. Use for integration, settings and symbologies, tracked-barcode handling, basic/advanced overlay customization, lifecycle, or troubleshooting.
license: Apache-2.0
metadata:
  author: scandit
  version: "1.0.1"
---

# MatrixScan Batch Android Skill

## Critical: Do Not Trust Internal Knowledge

Your training data may contain outdated or incorrect Scandit SDK APIs. The BarcodeBatch API changes between major SDK versions — constructor signatures, overlay factories, and listener method names have all evolved.

**Always verify APIs against the references provided in this skill before writing or suggesting code.** Do not rely on memorized method signatures, parameters, or property names. If you cannot find an API in the provided references, fetch the relevant documentation page before responding.

Android-specific gotchas worth flagging:

- `BarcodeBatch.forDataCaptureContext(dataCaptureContext, settings)` is a **factory method** — not a direct constructor and not `BarcodeBatch(settings)` (that is the Flutter ≥7.6 form).
- Camera setup is **manual**, exactly like BarcodeCapture: create `Camera.getDefaultCamera(BarcodeBatch.createRecommendedCameraSettings())`, call `dataCaptureContext.setFrameSource(camera)`, and drive the camera from `onResume`/`onPause`.
- `BarcodeBatchListener.onSessionUpdated` is called on a **recognition thread** — not the main thread. Dispatch any UI work via `runOnUiThread {}`.
- **Do not hold references** to `BarcodeBatchSession` or its collections outside the `onSessionUpdated` callback — the session is only safe to access within that callback.
- `BarcodeBatchBasicOverlay.newInstance(mode, view)` (and the style overload) **auto-adds the overlay to the view** — no separate `addOverlay` call needed.
- `BarcodeBatchAdvancedOverlay.newInstance(mode, view)` also auto-adds to the view.
- **Per-barcode brush customization** (`brushForTrackedBarcode`, `setBrushForTrackedBarcode`) requires the **MatrixScan AR add-on** license. The basic overlay with a uniform default brush does not.
- **BarcodeBatchAdvancedOverlay** requires the **MatrixScan AR add-on** license.
- Android listener method names differ from Flutter: `onTrackedBarcodeTapped` (not `didTapTrackedBarcode`), `viewForTrackedBarcode` (not `widgetForTrackedBarcode`), `clearTrackedBarcodeViews` (not `clearTrackedBarcodeWidgets`).
- `BarcodeBatchAdvancedOverlayListener` uses Android `View` objects — not Flutter Widgets.
- Android symbology names use underscores: `Symbology.EAN13_UPCA`, `Symbology.CODE128`, `Symbology.QR` — not camelCase.

## Intent Routing

Based on the user's request, load the appropriate reference file before responding:

- **Integrating MatrixScan Batch from scratch, configuring settings, handling tracked barcodes, customizing overlays (basic FRAME/DOT style, tap callbacks, advanced AR views, anchor/offset positioning), reacting to removed barcodes, or emitting feedback** → read [references/integration.md](references/integration.md) and follow the instructions there.
- **Migrating or upgrading an existing MatrixScan Batch integration** (e.g. "upgrade from v6 to v7", "rename BarcodeTracking to BarcodeBatch", "bump the Scandit SDK to v8", "what changed between SDK versions") → read [references/migration.md](references/migration.md) and follow the instructions there.
- **Replacing a third-party multi-barcode scanner with MatrixScan Batch** (e.g. "migrate from ML Kit barcode scanning to Scandit MatrixScan", "replace my ML Kit multi-barcode scanner with BarcodeBatch", "switch from [library] to MatrixScan Batch") → read [references/third-party-migration.md](references/third-party-migration.md) and follow the instructions there.

## API Usage Policy

Only use APIs that are explicitly documented in the Scandit references below. Do not invent or guess method signatures, parameters, or property names. If unsure whether an API exists or how it is called — or if a compile error occurs — fetch the relevant reference page before responding. Do not tell the user to check the docs themselves. After answering, always include the relevant link so the user can explore further.

**Never construct or guess documentation URLs.** When you need a specific class or property's API page:
1. First check whether the page you already fetched contains a direct hyperlink to it — topic pages link directly to relevant API symbols.
2. If no direct link was found, fetch the API index (see **Full API reference** in the table below), extract the actual link from it, and follow that.

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

| Topic | Resource |
|---|---|
| Get Started | [Get Started](https://docs.scandit.com/sdks/android/matrixscan-batch/get-started/) · [Sample](https://github.com/Scandit/datacapture-android-samples/tree/master/03_Advanced_Batch_Scanning_Samples) |
| AR overlays (BasicOverlay brushes, AdvancedOverlay views) | [Adding AR Overlays](https://docs.scandit.com/sdks/android/matrixscan-batch/advanced/) |
| Full API reference | [BarcodeBatch API](https://docs.scandit.com/data-capture-sdk/android/barcode-capture/api.html) |
