---
name: sparkscan-ios
description: Use when SparkScan is involved in an iOS project — whether the user mentions SparkScan directly, or the codebase already uses SparkScan as its barcode scanning library and something needs to be added, changed, fixed, or migrated. This includes adding SparkScan to a new iOS app, modifying scan settings, handling scan results, customizing the SparkScan UI, upgrading between SDK versions, troubleshooting SparkScan behavior, or replacing a third-party barcode scanning library with SparkScan. If the project is iOS and SparkScan is in play, use this skill.
license: MIT
metadata:
  author: scandit
  version: "1.1.3"
---

# SparkScan iOS Skill

## Critical: Do Not Trust Internal Knowledge

Your training data may contain outdated or incorrect Scandit SDK APIs. The SparkScan API changes significantly between major SDK versions — properties get renamed, removed, or restructured.

**Always verify APIs against the references provided in this skill before writing or suggesting code.** Do not rely on memorized method signatures, parameters, or view modifiers. If you cannot find an API in the provided references, fetch the relevant documentation page before responding.

## Intent Routing

Based on the user's request, load the appropriate reference file before responding:

- **Integrating SparkScan from scratch** (e.g. "add SparkScan to my app", "set up barcode scanning", "how do I use SparkScan", "how do I handle feedback in SparkScan") → read `references/integration.md` and follow the instructions there.
- **Migrating or upgrading an existing SparkScan integration** (e.g. "upgrade from v6 to v7", "migrate my SparkScan", "what changed between SDK versions") → read `references/migration.md` and follow the instructions there.
- **Replacing a third-party barcode scanner with SparkScan** (e.g. "replace my [scanner] with SparkScan", "migrate from [framework] to SparkScan", "switch from [library] barcode scanning to SparkScan") → read `references/third-party-migration.md` and follow the instructions there.

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
| UIKit integration | [Get Started (UIKit)](https://docs.scandit.com/sdks/ios/sparkscan/get-started/) · [Sample](https://github.com/Scandit/datacapture-ios-samples/tree/master/01_Single_Scanning_Samples/01_Barcode_Scanning_with_Prebuilt_UI/ListBuildingSampleUIKit) |
| SwiftUI integration | [Get Started (SwiftUI)](https://docs.scandit.com/sdks/ios/sparkscan/get-started-with-swift-ui/) · [Sample](https://github.com/Scandit/datacapture-ios-samples/tree/master/01_Single_Scanning_Samples/01_Barcode_Scanning_with_Prebuilt_UI/ListBuildingSampleSwiftUI) |
| Advanced topics (custom feedback, hardware triggers, scanning modes, UI customization) | [Advanced Configurations](https://docs.scandit.com/sdks/ios/sparkscan/advanced/) |
| Full API reference | [SparkScan API](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api.html) |
