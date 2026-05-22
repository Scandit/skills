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
| `barcode-capture-{framework}` | [BarcodeCapture](https://docs.scandit.com/sdks/ios/barcode-capture/intro/) (single-barcode scanning) integration & migration — `BarcodeCaptureSettings`, listener wiring, `DataCaptureView` + `BarcodeCaptureOverlay`, camera lifecycle, plus 6→7 and 7→8 deltas. Available for `android`, `web`, `cordova`, `capacitor`, `flutter`, `rn` (React Native). |
| `matrixscan-ar-{framework}` | [MatrixScan AR](https://docs.scandit.com/sdks/ios/matrixscan-ar/intro/) (Barcode AR) integration & BarcodeBatch → BarcodeAr migration. Available for `android`, `web`, `cordova`, `capacitor`, `flutter`, `rn` (React Native). |
| `matrixscan-count-{framework}` | [MatrixScan Count](https://docs.scandit.com/sdks/ios/matrixscan-count/intro/) (BarcodeCount) integration — counting against a list, status overlays, capture-list and not-in-list workflows, plus pre-7.6 → 7.6 constructor migration. Available for `cordova`, `capacitor`, `flutter`, `rn` (React Native). |
| `matrixscan-batch-{framework}` | [MatrixScan Batch](https://docs.scandit.com/sdks/ios/matrixscan/intro/) (BarcodeBatch, formerly BarcodeTracking) integration — tracking sessions, basic-overlay brushes, and per-barcode AR annotations via the advanced overlay. Available for `android`, `ios`, `web`, `cordova`, `capacitor`, `flutter`, `rn` (React Native). |
| `label-capture-{framework}` | [Smart Label Capture](https://docs.scandit.com/sdks/ios/label-capture/intro/) integration & migration (regex renames v7.6→v8.0, Validation Flow redesign v8.1→v8.2, optional update callback v8.2→v8.4). Available for `android`, `ios`, `web`, `cordova`, `capacitor`, `flutter`, `rn` (React Native). |

## Installation

### Skills CLI (45+ agents)

The [`skills`](https://github.com/vercel-labs/skills) CLI from Vercel installs skills into any supported agent (Claude Code, Codex, Cursor, Antigravity, GitHub Copilot, Cline, Continue, Windsurf, and 35+ others). Run it and follow the interactive prompts to pick agent and skills:

```bash
npx skills add scandit/skills
```

The CLI does **not** auto-update installed skills. We ship updates as Scandit adds new products, frameworks, and SDK versions — re-run periodically to pull the latest:

```bash
npx skills update scandit/skills
```

(Or `npx skills update` to refresh every installed skill at once.)

### Claude Code plugin

Claude Code can also install the skills as a plugin from the marketplace. Run the commands one at a time:

```bash
/plugin marketplace add scandit/skills
```

```bash
/plugin install scandit-sdk@scandit-plugins
```

Auto-update is off by default for third-party marketplaces, so we recommend turning it on: open `/plugin` → **Marketplaces** → select `scandit-plugins` → **Enable auto-update**. See the [Claude Code plugins docs](https://code.claude.com/docs/en/discover-plugins) for details.

### Cursor plugin

Install the official Scandit plugin in Cursor with one click from the [Cursor marketplace](https://cursor.com/marketplace/scandit). Cursor manages plugin updates automatically — installed plugins are kept current through the marketplace without manual action.

### GitHub Copilot CLI plugin

[GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli) can also install the skills as a plugin from the marketplace:

```bash
copilot plugin marketplace add scandit/skills
```

```bash
copilot plugin install scandit-sdk@scandit-plugins
```

Copilot CLI does not auto-update plugins — re-run periodically to pull the latest skills:

```bash
copilot plugin update scandit-sdk
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
