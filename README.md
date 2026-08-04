# Agent Skills for the Scandit SDK

[![Install via skills.sh](https://img.shields.io/badge/skills.sh-install-green)](https://skills.sh/scandit/skills)
[![Install in Cursor](https://img.shields.io/badge/Install%20in-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/marketplace/scandit)

AI agent skills for integrating the [Scandit Data Capture SDK](https://docs.scandit.com).

Each skill teaches your coding assistant how to integrate a specific Scandit SDK correctly. Instead of pasting docs snippets into your AI editor, install a skill once and your agent follows Scandit's recommended patterns whenever you ask it to add a Scandit feature.

## What you get

Each integration skill is specific to a product and a framework. Each skill bundles:

- The recommended integration code for that product + framework (e.g. SparkScan iOS)
- Up-to-date setup, permissions, and license-key wiring
- Common customization recipes (modes, callbacks, UI tweaks)
- Links back to the relevant Scandit documentation

## Not sure which product you need?

If you're new to Scandit and don't yet know whether your use case fits SparkScan, Barcode Capture, MatrixScan, Smart Label Capture, or ID Capture, start with the `data-capture-sdk` skill. It's an advisor — it asks a few questions about your workflow, recommends the right product, and then points you at the matching implementation skill for your platform.

Install it the same way as any other skill (see [Installation](#installation) below), then just chat with your agent like you would with anyone else — ask open-ended questions, describe your app, paste a screenshot of the screen you want to add scanning to, or drop in a photo of the label, package, or ID you need to capture. The skill will use that context to narrow down the right product. For example:

```
# Example 1
/data-capture-sdk I need to scan barcodes in a warehouse app — which Scandit product should I use?

# Example 2
/data-capture-sdk here's a photo of the labels we want to capture — what fits best?
```

The skill will also be picked up automatically from prompts like _"help me choose a Scandit product"_ or _"which Scandit SDK fits my use case?"_, no explicit invocation needed. Once you've landed on a product and platform, the advisor hands you off to the right product-framework skill (e.g. `barcode-capture-flutter`) from the table below.

## Available skills

| Skill | Description |
| --- | --- |
| `data-capture-sdk` | Product-selection advisor — recommends the right Scandit product for your use case and hands off to the matching implementation skill. |
| `sparkscan-{framework}` | [SparkScan](https://docs.scandit.com/sdks/ios/sparkscan/intro/) integration & migration. Available for `android`, `ios`, `web`, `cordova`, `capacitor`, `flutter`, `rn` (React Native). |
| `barcode-capture-{framework}` | [BarcodeCapture](https://docs.scandit.com/sdks/ios/barcode-capture/intro/) (single-barcode scanning) integration & migration — `BarcodeCaptureSettings`, listener wiring, `DataCaptureView` + `BarcodeCaptureOverlay`, camera lifecycle, plus 6→7 and 7→8 deltas. Available for `android`, `ios`, `web`, `cordova`, `capacitor`, `flutter`, `rn` (React Native). |
| `matrixscan-ar-{framework}` | [MatrixScan AR](https://docs.scandit.com/sdks/ios/matrixscan-ar/intro/) (Barcode AR) integration & BarcodeBatch → BarcodeAr migration. Available for `android`, `web`, `cordova`, `capacitor`, `flutter`, `rn` (React Native). |
| `matrixscan-count-{framework}` | [MatrixScan Count](https://docs.scandit.com/sdks/ios/matrixscan-count/intro/) (BarcodeCount) integration — counting against a list, status overlays, capture-list and not-in-list workflows, plus pre-7.6 → 7.6 constructor migration. Available for `cordova`, `capacitor`, `flutter`, `rn` (React Native). |
| `matrixscan-count-{framework}` | [MatrixScan Count](https://docs.scandit.com/sdks/ios/matrixscan-count/intro/) (BarcodeCount) native integration — bulk counting with the built-in AR counting UI, the explicitly-managed camera lifecycle, highlight customization (Icon/Dot styles), status mode, clustering, and scanning against a capture list (progress, not-in-list accept/reject). Available for `ios`, `android`. |
| `matrixscan-batch-{framework}` | [MatrixScan Batch](https://docs.scandit.com/sdks/ios/matrixscan/intro/) (BarcodeBatch, formerly BarcodeTracking) integration — tracking sessions, basic-overlay brushes, and per-barcode AR annotations via the advanced overlay. Available for `android`, `ios`, `web`, `cordova`, `capacitor`, `flutter`, `rn` (React Native). |
| `matrixscan-pick-ios` | [MatrixScan Pick](https://docs.scandit.com/sdks/ios/matrixscan-pick/intro/) (BarcodePick) integration — guided picking against a list of products and quantities, resolving scanned barcodes against a product database, plus highlight styling. Available for `ios`. |
| `label-capture-{framework}` | [Smart Label Capture](https://docs.scandit.com/sdks/ios/label-capture/intro/) integration & migration (regex renames v7.6→v8.0, Validation Flow redesign v8.1→v8.2, optional update callback v8.2→v8.4). Available for `android`, `ios`, `web`, `cordova`, `capacitor`, `flutter`, `rn` (React Native). |
| `id-capture-{framework}` | [ID Capture](https://docs.scandit.com/sdks/ios/id-capture/intro/) (identity-document scanning — passports, driver's licenses, ID cards, MRZ/VIZ/barcode/mobile documents) integration & v7→v8 migration (`scannerType`→`scanner` wrapper, `AamvaBarcodeVerifier` removal), plus the three add-on capability modules (voided-ID detection, European driving-license decoding, AAMVA barcode verification). Available for `web`, `flutter`, `cordova`, `rn` (React Native), `capacitor`. |
| `id-bolt` | [ID Bolt](https://docs.scandit.com/hosted/id-bolt/api-overview/) — Scandit's hosted, drop-in ID scanning for websites (a thin wrapper around ID Capture that runs in a Scandit-hosted pop-up, so you don't build a UI workflow). `IdBoltSession.create(...)` + `start()`, `DocumentSelection`, scanner/validators/anonymization, `onCompletion`/`onCancellation`, theming & localization. Uses `@scandit/web-id-bolt` (not the ID Capture SDK). Web only. |

## Installation

Install the plugin. One command, and your agent gets all 74 skills:

```bash
npx plugins add scandit/skills
```

It detects which coding agents you have and installs into each of them. Re-run the same command to pull the latest skills.

Or install from your agent's own marketplace:

| Agent | Install | Updates |
| --- | --- | --- |
| Codex / ChatGPT App | [One click install](https://chatgpt.com/plugins/plugins_6a6c6b6440a08191987ecc241e8660f7), or search **Scandit SDK** in the [plugin directory](https://learn.chatgpt.com/docs/plugins?surface=app#plugin-directory-in-the-codex-app) | Automatic |
| Claude Code | `/plugin marketplace add scandit/skills`<br>`/plugin install scandit-sdk@scandit-plugins` | `/plugin` → **Marketplaces** → `scandit-plugins` → **Enable auto-update** |
| Cursor | [One click install](https://cursor.com/marketplace/scandit), or `/add-plugin scandit-sdk` in the editor | Automatic |
| Codex CLI | `codex plugin marketplace add scandit/skills`<br>`codex plugin add scandit-sdk@scandit-plugins` | `codex plugin marketplace upgrade scandit-plugins` |
| Copilot CLI | `copilot plugin marketplace add scandit/skills`<br>`copilot plugin install scandit-sdk@scandit-plugins` | `copilot plugin update scandit-sdk` |
| Everyone else | `npx skills add scandit/skills` | `npx skills update scandit/skills` |

**Just one skill?** Your agent only loads the skills your prompt needs, so the full bundle is usually the right choice. To install a single one:

```bash
npx skills add scandit/skills --skill sparkscan-ios
```

## Using a skill

Two ways the skill is invoked:

- **Slash command.** Call the skill explicitly:

  ```
  /sparkscan-ios use the skill to help me integrate the barcode scanner in my application
  ```

- **Automatic pickup.** Most agents read the skill's description and load it automatically when your prompt matches relevant keywords. With `sparkscan-ios` installed, asking _"add a SparkScan view to the home screen"_ pulls in the skill without explicit invocation.

## Contributing

We welcome feedback that improves the quality of these skills:

- **Report issues.** File bugs, outdated SDK patterns, or incorrect guidance in the [issue tracker](https://github.com/scandit/skills/issues).
- **Request new skills.** If a Scandit product, framework, or workflow you need isn't covered, open a feature request.

## License

See the [LICENSE](./LICENSE) file for licensing information.
