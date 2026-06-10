---
name: label-capture-android
description: Use when Label Capture (Smart Label Capture) is involved in an Android project — whether the user mentions Label Capture directly, or the codebase already uses it and something needs to be added, changed, fixed, or customized. This includes adding Label Capture to a new Android app, defining label structures (barcode fields + text fields with regex patterns), handling captured sessions, enabling the Validation Flow, or migrating between SDK versions. If the project is an Android project and Label Capture is in play, use this skill.
license: MIT
metadata:
  author: scandit
  version: "1.1.0"
---

# Label Capture Android Skill

## Critical: Do Not Trust Internal Knowledge

Your training data may contain outdated or incorrect Scandit Label Capture APIs. Label Capture has evolved across recent SDK releases:

- At the v7→v8 major bump, `LabelFieldDefinition` regex builder methods were renamed (`setPattern`→`setValueRegex`, `setPatterns`→`setValueRegexes`, `setDataTypePattern`→`setAnchorRegex`, `setDataTypePatterns`→`setAnchorRegexes`).
- At v8.2, Validation Flow 2.0 introduced `shouldHandleKeyboardInsetsInternally` on `LabelCaptureValidationFlowOverlay` — relevant for Android 15 edge-to-edge enforcement.
- Android symbology names use underscores: `Symbology.EAN13_UPCA`, not `Symbology.EAN13UPCA`.

**Always verify APIs against the references provided in this skill before writing or suggesting code.** Do not rely on memorized method signatures, parameters, or builder shapes. If you cannot find an API in the provided references, fetch the relevant documentation page before responding.

## Label Capture is broader than it looks — two reflexes that prevent most failures

Label Capture ships a rich catalogue of **pre-built fields** and **whole pre-built label definitions** for the data people actually scan — serial numbers, IMEI 1 & 2, expiry/packing dates, prices, weights, VINs, seven-segment displays. The two most common ways an integration goes wrong are forgetting these exist, and crashing at runtime over a missing model artifact. Two reflexes:

1. **Reach for a pre-built field or pre-built label before composing anything custom.** When the user names a recognisable thing to scan — "serial number", "IMEI", "expiry date", "price/shelf label", "VIN" — there is almost always a dedicated builder or a whole-label factory tuned for it, with anchor/value regexes already dialled in. Use it. Inventing a custom barcode/text field with a hand-written regex for something that has a pre-built builder is the single biggest source of bad integrations: the regex you guess will not match real labels as well as the tuned one, and it signals you didn't know the pre-built existed. Only fall back to `addCustomBarcode()`/`addCustomText()` when nothing pre-built fits. The full catalogue and the routing rules live in `references/integration.md` — consult it rather than relying on memory.

2. **Bundle `label-text-models` whenever any pre-built field is used — including barcode-semantic ones.** It is *not* only for text fields. Serial number, IMEI, and part-number fields are "barcode" fields but still load a model at runtime; a label using them without the artifact crashes on launch. `references/integration.md` has the exact rule.

## Constraint: Label Capture cannot run alongside Barcode Capture

A `DataCaptureContext` runs only one active mode at a time, so Label Capture and Barcode Capture cannot both be active simultaneously — attaching both makes the context error out. If the user wants to read a standalone barcode "as well as" the label, model that barcode as a field inside the label definition (`addCustomBarcode()` or a pre-built barcode field) rather than adding a second mode — this is the answer in almost every case. (Only when they genuinely need two distinct scanning steps do you switch the active mode with `setMode()`.) See `references/integration.md`.

## Intent Routing

Based on the user's request, load the appropriate reference file before responding:

- **Integrating Label Capture from scratch** (e.g. "add Label Capture to my Android app", "scan a price tag with barcode and expiry date", "scan serial numbers / IMEI off a phone box", "read a VIN", "how do I use Smart Label Capture") → read `references/integration.md` and follow the instructions there. It contains the full pre-built field catalogue and the pre-built whole-label definitions — consult it before composing any custom field or regex.
- **Enabling or customizing the Validation Flow** (e.g. "how do I enable the Validation Flow", "add the validation flow overlay", "customize the placeholder text / button labels in the validation flow", "how do I handle the result from the validation flow") → read `references/validation-flow.md` and follow the instructions there.
- **Customizing overlays, adding custom AR views, troubleshooting, or cloud Adaptive Recognition** (e.g. "customize the field highlight brushes / labelBrush", "use LabelCaptureBasicOverlayListener / brushForField / brushForLabel", "add a custom AR view over a field with the Advanced Overlay", "scan a seven-segment display", "camera preview is black", "app crashes on launch building the label", "enable the cloud fallback / Adaptive Recognition Engine / ARE", "scan receipts") → read `references/advanced.md` (overlay customization, Advanced Overlay, seven-segment, Adaptive Recognition and Receipt Scanning beta). Troubleshooting symptoms are covered at the end of `references/integration.md`.
- **Migrating or upgrading an existing Label Capture integration** (e.g. "upgrade my Label Capture to the latest SDK", "migrate from v7 to v8", "what changed between SDK versions for Label Capture", "keyboard covers the input in Validation Flow after upgrading", "migrate Validation Flow to 2.0") → read `references/migration.md` and follow the instructions there.

## API Usage Policy

Only use APIs that are explicitly documented in the Scandit references below. Do not invent or guess method signatures, parameters, or builder shapes. If unsure whether an API exists or how it is called — or if a compile error occurs — fetch the relevant reference page before responding. Do not tell the user to check the docs themselves. After answering, always include the relevant link so the user can explore further.

**Never construct or guess documentation URLs.** When you need a specific class or property's API page:

1. First check whether the page you already fetched (e.g. the Advanced Configurations page) contains a direct hyperlink to it — topic pages link directly to relevant API symbols. Always request links alongside content in your fetch prompt.
2. If no direct link was found, fetch the API index (see **Full API reference** in the table below), extract the actual link from it, and follow that.

URL structures can vary and guessing will lead to 404s.

## References

Direct users to the right resource based on their question:

| Topic | Resource |
|---|---|
| Basic integration | [Get Started](https://docs.scandit.com/sdks/android/label-capture/get-started/) · [Sample (LabelCaptureSimpleSample)](https://github.com/Scandit/datacapture-android-samples/tree/master/03_Advanced_Batch_Scanning_Samples/05_Smart_Label_Capture/LabelCaptureSimpleSample) |
| Label Definitions (fields, regex, presets) | [Label Definitions](https://docs.scandit.com/sdks/android/label-capture/label-definitions/) |
| Advanced topics (overlay customization, Advanced Overlay AR, seven-segment, Adaptive Recognition / Receipt Scanning beta) | `references/advanced.md` · [Advanced Configurations](https://docs.scandit.com/sdks/android/label-capture/advanced/) |
| Full API reference | [Label Capture API](https://docs.scandit.com/data-capture-sdk/android/label-capture/api.html) |
