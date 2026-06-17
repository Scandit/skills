---
name: label-capture-ios
description: Use when Label Capture (Smart Label Capture) is involved in an iOS project — whether the user mentions Label Capture directly, or the codebase already uses it and something needs to be added, changed, fixed, or customized. This includes adding Label Capture to a new iOS app, defining label structures (barcode fields + text fields with regex patterns), handling captured sessions, enabling the Validation Flow, or migrating between SDK versions. If the project is an iOS project and Label Capture is in play, use this skill.
license: MIT
metadata:
  author: scandit
  version: "1.0.0"
---

# Label Capture iOS Skill

## Critical: Do Not Trust Internal Knowledge

Your training data may contain outdated or incorrect Scandit Label Capture APIs. Label Capture has evolved across recent SDK releases:

- At the v7→v8 major bump, the `LabelFieldDefinition` regex builder methods were renamed (`setPattern`→`valueRegex`, `setPatterns`→`valueRegexes`, `setDataTypePattern`→`anchorRegex`, `setDataTypePatterns`→`anchorRegexes`).
- In v8.1, the Swift result-builder DSL (`LabelCaptureSettings { LabelDefinition("...") { ... } }`) was introduced and `Symbology` enum auto-bridging removed the need for `NSNumber` boxing. v8.0 integrations use the array initializer `LabelCaptureSettings(labelDefinitions: [...])`. The optional VF delegate method `didSubmitManualInputFor:replacingValue:withValue:` was also added in v8.1.
- In v8.2, the Validation Flow UI was redesigned. `LabelCaptureValidationFlowSettings.setPlaceholderText(_:forLabelDefinition:)` and the optional delegate method `didUpdateResult:asyncId:fields:frameData:` were added.
- iOS symbology enum values use camelCase: `.ean13UPCA`, `.gs1DatabarExpanded`, `.code128` (not the Android underscore form `EAN13_UPCA`).
- The iOS label settings use a Swift result-builder DSL (v8.1+) or array initializer (v8.0), not the fluent `.addLabel().buildFluent(...)` style used by Android.

**Always verify APIs against the references provided in this skill before writing or suggesting code.** Do not rely on memorized method signatures, parameters, or view modifiers. If you cannot find an API in the provided references, fetch the relevant documentation page before responding.

## Operational constraints

These are runtime/licensing facts about Label Capture — not API versioning — and they affect what you can promise the user before any code is written.

**Label Capture reads printed text only.** Handwritten text is not supported. The on-device OCR engine and ARE both target machine-printed characters (latin letters, digits, common punctuation). If the user asks about scanning handwritten values, say so explicitly and propose a manual-entry fallback (e.g. the Validation Flow's manual input field).

**ARE (Adaptive Recognition Engine)** is Scandit's cloud-based OCR fallback — enabled via `.adaptiveRecognition(.auto)` on the `LabelDefinition`. It is currently in Beta, works **only with the Validation Flow overlay**, and requires a license key with the ARE feature flag enabled. Trial keys can be issued for evaluation; production keys require contacting <support@scandit.com>. Do not enable it by default.

## Intent Routing

Based on the user's request, load the appropriate reference file before responding:

- **Questions about other Scandit products or scanning modes** (e.g. SparkScan, Barcode Capture, MatrixScan, ID Capture, or general SDK setup questions not specific to Label Capture) → hand off to the `data-capture-sdk` skill. Do not attempt to answer questions about other capture modes from memory — the dedicated skill has the correct and up-to-date references.

- **Integrating Label Capture from scratch** (e.g. "add Label Capture to my iOS app", "scan a price tag with barcode and expiry date", "scan a price/shelf label", "read a VIN", "read a seven-segment display / digital scale", "how do I use Smart Label Capture", "I want to build a label scanning app", "which overlay should I use", "what is ARE", "scan a whole receipt", "how do I improve OCR accuracy", "how do I capture the scanned image with the Basic Overlay", "build a fully custom AR overlay / floating pins / draw my own views on the camera feed", "use the Advanced Overlay", "anchor / position / offset a custom view on a tracked label", "stop the repeated capture beep / emit feedback once per label", "scan a barcode AND a label / use Barcode Capture and Label Capture together / why does adding a second mode stop scanning", "which SPM products / why does my IMEI or serial-number label crash at launch") → read `references/integration.md` and follow the instructions there. It contains the pre-built whole-label factory definitions (price capture, VIN, seven-segment) and the Beta Receipt Scanning path — consult it before composing custom fields. If the user has no existing project, the guide will direct you to offer the pre-built sample first.
- **Enabling or customising the Validation Flow** (e.g. "how do I enable the Validation Flow", "add the validation flow overlay", "customise the placeholder text / button labels in the validation flow", "how do I handle the result from the validation flow", "why is the Validation Flow not configurable", "what can I change in the VF", "how do I capture the frame image during the Validation Flow", "can I embed the Validation Flow in a card or sheet") → read `references/validation-flow.md` and follow the instructions there. Also read `references/integration.md` first if the user does not yet have a baseline Label Capture integration in place — the Validation Flow is a swap-in for the Basic Overlay, not a from-scratch flow.
- **Migrating or upgrading an existing Label Capture integration** (e.g. "upgrade my Label Capture to the latest SDK", "migrate from v7 to v8", "what changed between SDK versions for Label Capture") → read `references/migration.md` and follow the instructions there.

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
| Basic integration | [Get Started](https://docs.scandit.com/sdks/ios/label-capture/get-started/) · [Sample (LabelCaptureSimpleSample)](https://github.com/Scandit/datacapture-ios-samples/tree/master/03_Advanced_Batch_Scanning_Samples/05_Smart_Label_Capture/LabelCaptureSimpleSample) |
| Label Definitions (fields, regex, presets) | [Label Definitions](https://docs.scandit.com/sdks/ios/label-capture/label-definitions/) |
| Advanced topics (Validation Flow customization, adaptive recognition, custom overlays) | [Advanced Configurations](https://docs.scandit.com/sdks/ios/label-capture/advanced/) |
| Full API reference | [Label Capture API](https://docs.scandit.com/data-capture-sdk/ios/label-capture/api.html) |
