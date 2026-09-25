---
name: matrixscan-ar-capacitor
description: Capacitor MatrixScan AR (Barcode AR, BarcodeAr) — scanning multiple barcodes at once with AR highlights and annotations, BarcodeArView attached to a DOM element, in Capacitor iOS/Android apps (not the plain-web sibling). Use for integration, symbology configuration, highlight and annotation providers, session handling, migration from BarcodeBatch/BarcodeTracking, or troubleshooting.
license: Apache-2.0
metadata:
  author: scandit
  version: "1.0.1"
---

# MatrixScan AR Capacitor Skill

## Critical: Do Not Trust Internal Knowledge

Your training data may contain outdated or incorrect Scandit SDK APIs. The BarcodeAr API is new in Capacitor 8.2 — there is no prior Capacitor history to reference. Properties, constructor signatures, provider interfaces, and view attachment patterns may differ from other platforms or from general knowledge.

**Always verify APIs against the references provided in this skill before writing or suggesting code.** Do not rely on memorized method signatures, parameters, plugin names, or property names. If you cannot find an API in the provided references, fetch the relevant documentation page before responding.

Capacitor-specific gotchas worth flagging:

- `ScanditCaptureCorePlugin.initializePlugins()` **must** be called (and awaited) before any other Scandit API — including `DataCaptureContext` construction. Forgetting this produces runtime errors that look unrelated to initialization.
- `npx cap sync` must be run after every plugin version change to propagate native artifacts into iOS/Android. Skipping it yields a web/native version mismatch at runtime.
- **BarcodeArView requires a DOM element.** Unlike SparkScan, BarcodeArView is not a floating native overlay; it mirrors its size and position from a DOM element. You must call `await barcodeArView.connectToElement(element)` to attach it to the `<div id="barcode-ar-view">` container in the HTML.
- **Minimum SDK version is 8.2** for BarcodeAr on Capacitor. There is no v6 or v7 history to migrate from on this platform.
- `BarcodeAr` is constructed with `new BarcodeAr(settings)` — the context is wired separately via `BarcodeArView`, not passed to the mode constructor.
- Camera is set up explicitly via `BarcodeAr.createRecommendedCameraSettings()`, `Camera.withSettings(cameraSettings)`, and `context.setFrameSource(camera)` — BarcodeArView manages the camera lifecycle once running.
- The `highlightProvider` and `annotationProvider` are plain objects with async methods, set as properties on the `BarcodeArView` instance.
- iOS requires `NSCameraUsageDescription` in `Info.plist`. Android handles camera permissions automatically.

## Intent Routing

Based on the user's request, load the appropriate reference file before responding:

- **Integrating MatrixScan AR from scratch** (e.g. "add MatrixScan AR to my app", "set up Barcode AR", "how do I use BarcodeArView in Capacitor", "how do I show annotations", "how do I highlight barcodes") → read [references/integration.md](references/integration.md) and follow the instructions there.

- **Migrating from BarcodeBatch / BarcodeTracking to BarcodeAr** (e.g. "migrate my BarcodeBatch code", "replace BarcodeTracking with BarcodeAr", "upgrade from MatrixScan to BarcodeAr", the target file imports `BarcodeBatch`, `BarcodeBatchBasicOverlay`, `BarcodeBatchAdvancedOverlay`, `TrackedBarcodeView`, or contains `context.setMode(` with a BarcodeBatch instance) → read [references/migration.md](references/migration.md) and follow the 10-step migration process there.

## API Usage Policy

Only use APIs that are explicitly documented in the Scandit references below. Do not invent or guess method signatures, parameters, property names, or imports. If unsure whether an API exists or how it is called — or if a TypeScript / runtime error occurs — fetch the relevant reference page before responding. Do not tell the user to check the docs themselves. After answering, always include the relevant link so the user can explore further.

**Never construct or guess documentation URLs.** When you need a specific class or property's API page:
1. First check whether the page you already fetched (e.g. the Get Started page) contains a direct hyperlink to it — topic pages link directly to relevant API symbols. Always request links alongside content in your fetch prompt.
2. If no direct link was found, fetch the API index (see **Full API reference** in the table below), extract the actual link from it, and follow that.

URL structures vary across SDK versions and plugin paths (e.g. `api/ui/` subdirectory) and guessing will lead to 404s.

## Framework variant policy

Capacitor is a WebView-based framework. Examples in this skill use **plain JavaScript (ES modules)**. TypeScript projects can use the same imports and APIs verbatim — just add types — but this skill does not assume a TypeScript project by default. If the target project is clearly TypeScript (`.ts` files, `tsconfig.json`), adapt the final output to TypeScript syntax; otherwise stay in plain JS.

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
| Capacitor integration | [Get Started](https://docs.scandit.com/sdks/capacitor/matrixscan-ar/get-started/) · [Sample](https://github.com/Scandit/datacapture-capacitor-samples/tree/master/03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanARSimpleSample) |
| Full API reference | [BarcodeAr API](https://docs.scandit.com/data-capture-sdk/capacitor/barcode-capture/api.html) |
