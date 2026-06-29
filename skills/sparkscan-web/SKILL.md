---
name: sparkscan-web
description: Use when SparkScan (Scandit's pre-built high-volume single-scanning UI with a floating trigger button) is involved in a web project — whether the user names SparkScan directly or the codebase already uses it via `@scandit/web-datacapture-barcode` / the `<spark-scan-view>` element. Covers adding SparkScan to a web app (including React, Vite, Next.js), configuring symbologies and scan settings, handling scan results and feedback, customizing or replacing the trigger button, wiring the DataCaptureContext, fixing React-specific problems (React 18 vs 19 property/attribute binding, the context-singleton "works for a second then dies" / StrictMode issue), troubleshooting the camera not opening on a device (HTTPS / secure-context) or cross-origin header (COOP/COEP) problems, and upgrading or migrating between Web SDK versions (v6→v7, v7→v8). If the project is a web app and SparkScan is in play, use this skill. Do not use it for SparkScan on iOS, Android, React Native, Flutter, Capacitor, Cordova, or .NET/MAUI, nor for other Scandit web products (Barcode Capture, MatrixScan, ID Capture, Label Capture).
license: MIT
metadata:
  author: scandit
  version: "1.2.0"
---

# SparkScan Web Skill

## Critical: Do Not Trust Internal Knowledge

Your training data may contain outdated or incorrect Scandit SDK APIs. The SparkScan API changes significantly between major SDK versions — properties get renamed, removed, or restructured.

**Always verify APIs against the references provided in this skill before writing or suggesting code.** Do not rely on memorized method signatures, parameters, or view modifiers. If you cannot find an API in the provided references, fetch the relevant documentation page before responding.

## Intent Routing

Based on the user's request, load the appropriate reference file before responding. More than one may apply (e.g. a React integration that also hits a camera issue) — read all that are relevant:

- **Integrating SparkScan from scratch** (e.g. "add SparkScan to my app", "set up barcode scanning", "how do I use SparkScan", "how do I handle feedback in SparkScan", "I want to build a scanning app") → read `references/integration.md` and follow the instructions there. If the user has no existing project, the guide will direct you to offer the pre-built sample first.
- **The project uses React** (a `react` dependency in `package.json`, `.tsx`/`.jsx` files, hooks, JSX) → also read `references/react.md`. The correct way to bind the `<spark-scan-view>` custom element differs by React major version, so **check the `react` version in `package.json` first** — the guide explains the React 18 vs 19 difference and the context/lifecycle pitfalls. Always consult it before writing React code; the generic `integration.md` example is vanilla TS.
- **Migrating or upgrading an existing SparkScan integration** (e.g. "upgrade from v6 to v7", "migrate my SparkScan", "what changed between SDK versions") → read `references/migration.md` and follow the instructions there.
- **Runtime, camera, or deployment trouble** (e.g. "camera won't open on my phone", "works for a second then dies", cross-origin/COOP/COEP/header issues, "blank preview over a LAN IP") → read `references/troubleshooting.md`. These are environment/hosting issues, not API mistakes, and are easy to misdiagnose as code bugs.

## API Usage Policy

Only use APIs that are explicitly documented in the Scandit references below. Do not invent or guess method signatures, parameters, or view modifiers. If unsure whether an API exists or how it is called — or if a compile error occurs — fetch the relevant reference page before responding. Do not tell the user to check the docs themselves. After answering, always include the relevant link so the user can explore further.

**Never construct or guess documentation URLs.** When you need a specific class or property's API page:

1. First check whether the page you already fetched (e.g. the Advanced Configurations page) contains a direct hyperlink to it — topic pages link directly to relevant API symbols. Always request links alongside content in your fetch prompt.
2. If no direct link was found, fetch the API index (see **Full API reference** in the table below), extract the actual link from it, and follow that.

URL structures can vary (e.g. `api/ui/` subdirectory) and guessing will lead to 404s.

## References

Direct users to the right resource based on their question:

| Topic | Resource |
|---|---|
| Basic integration | [Get Started](https://docs.scandit.com/sdks/web/sparkscan/get-started/) · [Sample](https://github.com/Scandit/datacapture-web-samples/tree/master/01_Single_Scanning_Samples/01_Barcode_Scanning_with_Pre-built_UI/ListBuildingSample) |
| React integration | [Get Started](https://docs.scandit.com/sdks/web/sparkscan/get-started/) · [Sample](https://github.com/Scandit/datacapture-web-samples/tree/master/05_Framework_Integration_Samples/SparkScanReactSample) |
| Advanced topics (custom feedback, hardware triggers, scanning modes, UI customization) | [Advanced Configurations](https://docs.scandit.com/sdks/web/sparkscan/advanced/) |
| Full API reference | [SparkScan API](https://docs.scandit.com/data-capture-sdk/web/barcode-capture/api.html#:~:text=SymbologySettings-,SparkScan,-SparkScan) |
