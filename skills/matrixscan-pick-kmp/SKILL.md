---
name: matrixscan-pick-kmp
description: MatrixScan Pick (BarcodePick) in Kotlin Multiplatform (KMP) projects — com.scandit.datacapture.kmp Maven artifacts, com.kmp.datacapture.barcode.pick imports. Pick/put verification workflows shared across Android/iOS — BarcodePickView (Compose composable or platform view), product provider, highlight styles, pick/unpick confirmation. Use for integration, settings configuration, listener wiring, highlight styling, or troubleshooting pick workflows.
license: MIT
metadata:
  author: scandit
  version: "1.0.1"
---

# MatrixScan Pick KMP Skill

## Critical: Do Not Trust Internal Knowledge

Your training data very likely predates Scandit's Kotlin Multiplatform (KMP) SDK entirely — it is a new SDK (first released at version 8.6) with its own API surface (`com.kmp.datacapture.*`) that does **not** mirror the native Android (`com.scandit.datacapture.*`) or iOS APIs one-to-one. Names, parameter labels, and even which listener owns which callback differ from both native SDKs and from what you may expect by analogy.

**Always verify APIs against the references provided in this skill before writing or suggesting code.** Do not rely on memorized method signatures, parameters, or class names — including ones you know from native Android/iOS Scandit SDKs. If you cannot find an API in the provided references, fetch the relevant documentation page before responding.

## Scope

This skill is scoped to the **MatrixScan Pick picking workflow on KMP**: `DataCaptureContext`, the `BarcodePick` mode, `BarcodePickSettings`, `BarcodePickView` (base module, `toAndroidView()` / `toUIView()`), the `barcode-compose` `BarcodePickView` composable, the product provider (`BarcodePickAsyncMapperProductProvider`), state-aware highlights (built-in styles and `CustomView`), the finish button, action/session listeners, and the `selectItemWithData` / `confirmActionForItemWithData` / `cancelActionForItemWithData` explicit-selection API.

## Intent Routing

Based on the user's request, load the appropriate reference file before responding:

- **Setting up or adjusting the MatrixScan Pick picking flow** (e.g. "add MatrixScan Pick to my KMP app", "set up the product list", "show/hide the finish button", "mute the beep", "track what's been picked", "use the Compose BarcodePickView") → read `references/integration.md` and follow the instructions there. If the project already has MatrixScan Pick wired up, do not re-create the context, mode, view, or lifecycle — locate the existing ones (grep for `BarcodePickView`, then `BarcodePick.forContext`) and change only what the user asked for. Determine whether the project uses the base `com.kmp.datacapture.barcode.pick.BarcodePickView` (host builds and drives the platform view itself, e.g. `AndroidView`/`UIViewRepresentable`) or the `com.kmp.datacapture.barcode.compose` `BarcodePickView` composable, and follow the matching pattern.
- **Customizing the highlights drawn over barcodes** (e.g. "change the highlight color per state", "use a rectangle instead of a dot", "show an icon / status badge on picked items", "draw a custom view over each barcode", "style the to-pick vs picked highlight") → read `references/highlights.md`. This assumes the basic integration is already in place; it covers the five highlight styles and the per-state brush / icon / status-icon / custom-view APIs.

## API Usage Policy

Only use APIs that are explicitly documented in the Scandit references below. Do not invent or guess class names, method signatures, or parameters — including by analogy with the native Android/iOS SDKs, which frequently differ from the KMP surface (e.g. KMP's `BarcodePickSettings.soundEnabled` has no `is` prefix, and KMP's finish-button callback is `BarcodePickViewUiListener`, not a UI delegate). If unsure whether an API exists or how it is called — or if a compile error occurs — fetch the relevant reference page before responding. Do not tell the user to check the docs themselves. After answering, always include the relevant link so the user can explore further.

**Never construct or guess documentation URLs.** When you need a specific class or property's API page:
1. First check whether the page you already fetched contains a direct hyperlink to it — topic pages link directly to relevant API symbols. Always request links alongside content in your fetch prompt.
2. If no direct link was found, fetch the API index (see **Full API reference** in the table below), extract the actual link from it, and follow that.

URL structures can vary and guessing will lead to 404s.

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

Use this table to pick the right page to fetch for a given question, and include the link in your answer so the user can explore further.

| Topic | Resource |
|---|---|
| KMP integration (commonMain + Android/iOS hosts) | [Intro](https://docs.scandit.com/sdks/kmp/matrixscan-pick/intro/) · [Get Started](https://docs.scandit.com/sdks/kmp/matrixscan-pick/get-started/) |
| Advanced (highlight styles, async providers) | [Advanced Configurations](https://docs.scandit.com/sdks/kmp/matrixscan-pick/advanced/) · `references/highlights.md` |
| Core concepts (context, camera, views) | [Core Concepts](https://docs.scandit.com/sdks/kmp/core-concepts/) |
