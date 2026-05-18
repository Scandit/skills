# Scandit Product Catalog

When a product has been identified via the decision guide, use the matching section below to provide details, capabilities, trade-offs, documentation links, and sample apps.

When recommending a product, always include the relevant **docs link** and **sample app link** for the user's platform. These are working examples that serve as the best starting point for implementation.

## Sample Repository Base URLs

| Platform | Repo |
|---|---|
| iOS | `https://github.com/Scandit/datacapture-ios-samples/tree/master/` |
| Android | `https://github.com/Scandit/datacapture-android-samples/tree/master/` |
| Web | `https://github.com/Scandit/datacapture-web-samples/tree/master/` |
| React Native | `https://github.com/Scandit/datacapture-react-native-samples/tree/master/` |
| Flutter | `https://github.com/Scandit/datacapture-flutter-samples/tree/master/` |
| .NET (MAUI) | `https://github.com/Scandit/datacapture-dotnet-samples/tree/master/maui/` |
| Capacitor | `https://github.com/Scandit/datacapture-capacitor-samples/tree/master/` |
| Cordova | `https://github.com/Scandit/datacapture-cordova-samples/tree/master/` |

---

## Single Barcode Scanning

**SparkScan and Barcode Capture share the exact same scanning engine, the same symbology support, and the same AI-powered features.** There is no difference in scanning performance or capability. The choice between them is purely about the UI and integration approach:

- **SparkScan** provides a pre-built, opinionated UI with workflows (single scan, continuous scanning, preview overlay, movable trigger button, micro-interactions) that have been refined through extensive customer testing and user research to optimize ergonomics and usability. Less integration effort, but you accept the SparkScan look and feel.
- **Barcode Capture** gives you full control over the scanning UI — you build everything yourself. More integration effort, but complete freedom over look, feel, and behavior.

### Barcode Capture

- **What it is**: The low-level, fully customizable SDK for integrating single barcode scanning. Same scanning engine as SparkScan — same symbologies, same AI features, same performance — but with no pre-built UI. The developer builds the entire scanning experience.
- **Use when**: The user needs complete control over the scanning UI and experience, or has specific UX requirements that SparkScan's pre-built workflows cannot satisfy.
- **Key traits**: No pre-built UI — maximum flexibility over look and feel. Supports all major symbologies and over 20,000 smart device models. Includes Scandit's AI-powered scanning engine, which prevents unintentional scans, lets users precisely select a barcode in crowded environments, avoids scanning duplicates when not intended, and falls back to OCR when a barcode is too damaged to decode.
- **Limitation**: Scans one barcode at a time. For multiple barcodes, consider a MatrixScan product or Smart Label Capture.
- **Platforms**: iOS, Android, Web, React Native, Flutter, .NET, Capacitor, Cordova
- **Docs**:
  - iOS: https://docs.scandit.com/sdks/ios/barcode-capture/get-started
  - Android: https://docs.scandit.com/sdks/android/barcode-capture/get-started
  - Web: https://docs.scandit.com/sdks/web/barcode-capture/get-started
  - React Native: https://docs.scandit.com/sdks/react-native/barcode-capture/get-started
  - Flutter: https://docs.scandit.com/sdks/flutter/barcode-capture/get-started
  - .NET: https://docs.scandit.com/sdks/net/ios/barcode-capture/get-started
  - Capacitor: https://docs.scandit.com/sdks/capacitor/barcode-capture/get-started
  - Cordova: https://docs.scandit.com/sdks/cordova/barcode-capture/get-started
- **Sample apps** (path relative to repo base):
  - iOS (Swift): `01_Single_Scanning_Samples/02_Barcode_Scanning_with_Low_Level_API/BarcodeCaptureSimpleSampleSwift`
  - iOS (ObjC): `01_Single_Scanning_Samples/02_Barcode_Scanning_with_Low_Level_API/BarcodeCaptureSimpleSampleObjC`
  - Android: `01_Single_Scanning_Samples/02_Barcode_Scanning_with_Low_Level_API/BarcodeCaptureSimpleSample`
  - Web: `01_Single_Scanning_Samples/02_Barcode_Scanning_with_Low-level_API/BarcodeCaptureSimpleSample`
  - React Native: `01_Single_Scanning_Samples/02_Barcode_Scanning_with_Low_Level_API/BarcodeCaptureSimpleSample`
  - Flutter: `01_Single_Scanning_Samples/02_Barcode_Scanning_with_Low_Level_API/BarcodeCaptureSimpleSample`
  - .NET (MAUI): `01_Single_Scanning_Samples/02_Barcode_Scanning_with_Low_Level_API/BarcodeCaptureSimpleSample`
  - Capacitor: `01_Single_Scanning_Samples/02_Barcode_Scanning_with_Low_Level_API/BarcodeCaptureSimpleSample`
  - Cordova: `01_Single_Scanning_Samples/02_Barcode_Scanning_with_Low_Level_API/BarcodeCaptureSimpleSample`

### SparkScan

- **What it is**: A pre-built, high-performance barcode scanning component with a minimalistic floating UI. Same scanning engine as Barcode Capture — same symbologies, same AI features, same performance — but packaged with an opinionated, ready-to-use UI. Integrates in just a few lines of code.
- **Use when**: The user wants fast integration, a polished pre-built scanning experience, or high-volume single-scan workflows (warehouse receiving, retail inventory, proof of delivery). The SparkScan UI has been designed and refined through extensive customer and user testing to optimize ergonomics, usability, and understandability.
- **Key traits**: Pre-built UI overlay with optimized micro-interactions, customizable feedback, hardware trigger support, continuous scanning mode, tap-to-scan, and target/selection mode. The UI includes a movable trigger button, a camera preview overlay, and seamless transitions between scanning modes. Also includes pre-built buttons to switch to advanced modes like Smart Label Capture. Includes the same AI-powered scanning engine as Barcode Capture — prevents unintentional scans, lets users select a specific barcode in crowded environments, avoids duplicate scans when not intended, and falls back to OCR for damaged barcodes.
- **Limitation**: Scans one barcode at a time.
- **Platforms**: iOS, Android, Web, React Native, Flutter, .NET, Capacitor, Cordova
- **Docs**:
  - iOS: https://docs.scandit.com/sdks/ios/sparkscan/intro
  - Android: https://docs.scandit.com/sdks/android/sparkscan/intro
  - Web: https://docs.scandit.com/sdks/web/sparkscan/intro
  - React Native: https://docs.scandit.com/sdks/react-native/sparkscan/intro
  - Flutter: https://docs.scandit.com/sdks/flutter/sparkscan/intro
  - .NET: https://docs.scandit.com/sdks/net/ios/sparkscan/intro
  - Capacitor: https://docs.scandit.com/sdks/capacitor/sparkscan/intro
  - Cordova: https://docs.scandit.com/sdks/cordova/sparkscan/intro
- **Sample apps** (path relative to repo base):
  - iOS (UIKit): `01_Single_Scanning_Samples/01_Barcode_Scanning_with_Prebuilt_UI/ListBuildingSampleUIKit`
  - iOS (SwiftUI): `01_Single_Scanning_Samples/01_Barcode_Scanning_with_Prebuilt_UI/ListBuildingSampleSwiftUI`
  - Android: `01_Single_Scanning_Samples/01_Barcode_Scanning_with_Pre_Built_UI/ListBuildingSample`
  - Web: `01_Single_Scanning_Samples/01_Barcode_Scanning_with_Pre-built_UI/ListBuildingSample`
  - React Native: `01_Single_Scanning_Samples/01_Barcode_Scanning_with_Pre_Built_UI/ListBuildingSample`
  - Flutter: `01_Single_Scanning_Samples/01_Barcode_Scanning_with_Pre_Built_UI/ListBuildingSample`
  - .NET (MAUI): `01_Single_Scanning_Samples/01_Barcode_Scanning_with_Pre_Built_UI/ListBuildingSample`
  - Capacitor: `01_Single_Scanning_Samples/01_Barcode_Scanning_with_Pre_Built_UI/ListBuildingSample`
- **Available skills**: `sparkscan-ios`

---

## Multi-Barcode Scanning

### MatrixScan Batch (BarcodeBatch)

- **What it is**: An SDK that locates, tracks, and decodes multiple barcodes in the camera's field of view simultaneously.
- **Also known as**: BarcodeBatch (renamed in SDK v7+). Legacy name: BarcodeTracking.
- **Use when**: The goal is to capture a list of all barcodes present — no verification against a master list needed. Ideal for proof of delivery, high-volume receiving, and packing.
- **Trade-off**: BarcodeBatch is the general-purpose multi-barcode scanning product. For specialized workflows like counting with manifest verification (BarcodeCount) or AR-guided item search (BarcodeFind), see those products below — but they require contacting support first.
- **Platforms**: iOS, Android, Web, React Native, Flutter, .NET, Capacitor, Cordova
- **Docs**:
  - iOS: https://docs.scandit.com/sdks/ios/matrixscan/intro
  - Android: https://docs.scandit.com/sdks/android/matrixscan/intro
  - Web: https://docs.scandit.com/sdks/web/matrixscan/intro
  - React Native: https://docs.scandit.com/sdks/react-native/matrixscan/intro
  - Flutter: https://docs.scandit.com/sdks/flutter/matrixscan/intro
  - .NET: https://docs.scandit.com/sdks/net/ios/matrixscan/intro
  - Capacitor: https://docs.scandit.com/sdks/capacitor/matrixscan/intro
  - Cordova: https://docs.scandit.com/sdks/cordova/matrixscan/intro
- **Sample apps** (path relative to repo base):
  - iOS: `03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanSimpleSample`
  - Android: `03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanSimpleSample`
  - Web: `03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanSimpleSample`
  - React Native: `03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanSimpleSample`
  - Flutter: `03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanSimpleSample`
  - .NET (MAUI): `03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanSimpleSample`
  - Capacitor: `03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanSimpleSample`
  - Cordova: `03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanSimpleSample`

### MatrixScan AR

- **What it is**: A highly customizable SDK combining high-speed multi-barcode scanning with the ability to overlay custom information, graphics, or interactive elements on items in the live camera view.
- **Use when**: The user needs maximum flexibility to display dynamic information overlaid on scanned barcodes — stock levels, sorting instructions, interactive shopping experiences, custom animations.
- **Pre-built components**: The SDK includes a **BasicOverlay** that provides simple colored highlights on tracked barcodes out of the box, and an **AdvancedOverlay** that lets developers attach fully custom native views (buttons, labels, images, animations) to each barcode. For users who want AR overlays but don't need to build everything from scratch, the BasicOverlay is a quick starting point; the AdvancedOverlay provides full flexibility.
- **Trade-off vs BarcodeBatch**: MatrixScan AR offers full customization of AR overlays, while BarcodeBatch is simpler and focused on list capture without visual overlays.
- **Platforms**: iOS, Android, Web, React Native, Flutter, .NET, Capacitor, Cordova
- **Docs**:
  - iOS: https://docs.scandit.com/sdks/ios/matrixscan-ar/intro
  - Android: https://docs.scandit.com/sdks/android/matrixscan-ar/intro
  - Web: https://docs.scandit.com/sdks/web/matrixscan-ar/intro
  - React Native: https://docs.scandit.com/sdks/react-native/matrixscan-ar/intro
  - Flutter: https://docs.scandit.com/sdks/flutter/matrixscan-ar/intro
  - .NET: https://docs.scandit.com/sdks/net/ios/matrixscan-ar/intro
  - Capacitor: https://docs.scandit.com/sdks/capacitor/matrixscan-ar/intro
  - Cordova: https://docs.scandit.com/sdks/cordova/matrixscan-ar/intro
- **Sample apps** (path relative to repo base):
  - iOS: `03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanARSimpleSample`
  - Android: `03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanARSimpleSample`
  - Web: `03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanARSimpleSample`
  - Flutter: `03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanARSimpleSample`
  - Capacitor: `03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanARSimpleSample`
  - Cordova: `03_Advanced_Batch_Scanning_Samples/01_Batch_Scanning_and_AR_Info_Lookup/MatrixScanARSimpleSample`

### MatrixScan Count (BarcodeCount)

- **What it is**: A pre-built scan-and-count solution that scans multiple items at once and verifies the count against an expected list or manifest.
- **Also known as**: BarcodeCount (new name).
- **Use when**: The workflow involves counting items and verifying against a pre-defined list — receiving goods, cycle counting, full stock takes. It answers "Are all the items here?". Speeds up counting workflows by up to 10x.
- **This is a specialized workflow product.** Recommend the user contact Scandit support at https://support.scandit.com to ensure it fits their specific workflow. However, if the user explicitly wants to start integrating, guide them using the sample app below as the reference implementation — the sample is a working example of the full count-and-verify workflow and the best starting point.
- **Docs**:
  - iOS: https://docs.scandit.com/sdks/ios/matrixscan-count/intro
  - Android: https://docs.scandit.com/sdks/android/matrixscan-count/intro
  - Web: https://docs.scandit.com/sdks/web/matrixscan-count/intro
  - React Native: https://docs.scandit.com/sdks/react-native/matrixscan-count/intro
  - Flutter: https://docs.scandit.com/sdks/flutter/matrixscan-count/intro
  - .NET: https://docs.scandit.com/sdks/net/ios/matrixscan-count/intro
  - Capacitor: https://docs.scandit.com/sdks/capacitor/matrixscan-count/intro
  - Cordova: https://docs.scandit.com/sdks/cordova/matrixscan-count/intro
- **Sample apps** (path relative to repo base):
  - iOS: `03_Advanced_Batch_Scanning_Samples/02_Counting_and_Receiving/MatrixScanCountSimpleSample`
  - Android: `03_Advanced_Batch_Scanning_Samples/02_Counting_and_Receiving/MatrixScanCountSimpleSample`
  - React Native: `03_Advanced_Batch_Scanning_Samples/02_Counting_and_Receiving/MatrixScanCountSimpleSample`
  - Flutter: `03_Advanced_Batch_Scanning_Samples/02_Counting_and_Receiving/MatrixScanCountSimpleSample`
  - .NET (MAUI): `03_Advanced_Batch_Scanning_Samples/02_Counting_and_Receiving/MatrixScanCountSimpleSample`
  - Capacitor: `03_Advanced_Batch_Scanning_Samples/02_Counting_and_Receiving/MatrixScanCountSimpleSample`

### MatrixScan Find (BarcodeFind)

- **What it is**: A pre-built AR component that helps users instantly locate specific items from a predefined list.
- **Also known as**: BarcodeFind (new name).
- **Use when**: The primary goal is to quickly locate one or more specific items among many — in-store order picking (click-and-collect), finding a parcel at a PUDO point, locating specific baggage.
- **This is a specialized workflow product.** Recommend the user contact Scandit support at https://support.scandit.com to ensure it fits their specific workflow. However, if the user explicitly wants to start integrating, guide them using the sample app below as the reference implementation.
- **Docs**:
  - iOS: https://docs.scandit.com/sdks/ios/matrixscan-find/intro
  - Android: https://docs.scandit.com/sdks/android/matrixscan-find/intro
  - Web: https://docs.scandit.com/sdks/web/matrixscan-find/intro
  - React Native: https://docs.scandit.com/sdks/react-native/matrixscan-find/intro
  - Flutter: https://docs.scandit.com/sdks/flutter/matrixscan-find/intro
  - .NET: https://docs.scandit.com/sdks/net/ios/matrixscan-find/intro
  - Capacitor: https://docs.scandit.com/sdks/capacitor/matrixscan-find/intro
  - Cordova: https://docs.scandit.com/sdks/cordova/matrixscan-find/intro
- **Sample apps** (path relative to repo base):
  - iOS: `03_Advanced_Batch_Scanning_Samples/03_Search_and_Find/SearchAndFindSample`
  - Android: `03_Advanced_Batch_Scanning_Samples/03_Search_and_Find/SearchAndFindSample`
  - Web: `03_Advanced_Batch_Scanning_Samples/03_Search_and_Find/SearchAndFindSample`
  - React Native: `03_Advanced_Batch_Scanning_Samples/03_Search_and_Find/SearchAndFindSample`
  - Flutter: `03_Advanced_Batch_Scanning_Samples/03_Search_and_Find/SearchAndFindSample`
  - .NET (MAUI): `03_Advanced_Batch_Scanning_Samples/03_Search_and_Find/SearchAndFindSample`

---

## OCR / Label Scanning

### Smart Label Capture

- **What it is**: Simultaneously captures and parses information from multiple barcodes and multiple fields of printed text (OCR) on a label in a single scan action.
- **Use when**: The user needs to read text AND barcodes from labels — expiry dates, serial/lot numbers, unit prices, weights. If the workflow requires capturing any printed text, Smart Label Capture is the only option.
- **Key traits**: OCR + barcode in one capture. Semantic approach — define what information you need (e.g., "expiry date") and the system finds it across many label layouts without per-layout templates.
- **This is the only Scandit product with OCR capability.** No other product can read printed text. "Text Capture" is **not** a Scandit product — do not propose it under any circumstances. When the user needs OCR but does not have an SLC license and *every* field they need is encoded in a barcode, the only legitimate fallback is **MatrixScan Batch**, with the caveat that the developer must correlate the reads themselves (no schema, no single-frame multi-field guarantee).

#### Pre-built Fields

Match these by name when the user's description fits. Sourced from the live `features.json` feature matrix; verify per-platform support there for exact SDK versions.

| Field | Category | Use case |
|---|---|---|
| `SerialNumberBarcode` | Barcode | Electronics / appliance serial numbers |
| `PartNumberBarcode` | Barcode | Manufacturing & inventory part numbers |
| `ImeiOneBarcode` | Barcode | First IMEI on mobile devices |
| `ImeiTwoBarcode` | Barcode | Second IMEI on dual-SIM devices |
| `UnitPriceText` | Text | Retail / grocery unit price |
| `TotalPriceText` | Text | Retail / grocery total price |
| `WeightText` | Text | Shipping & logistics weight |
| `PackingDateText` | Text | Food & beverage packing date |
| `ExpiryDateText` | Text | Pharma & food expiry / best-before |
| `DateText` | Text | Generic date (configurable via `LabelDateFormat`) |
| `CustomBarcode` | Custom | User-defined symbology + regex |
| `CustomText` | Custom | User-defined regex for arbitrary text |

#### Pre-built Labels

Full label definitions that ship with SLC — drop them in instead of designing a schema from scratch.

| Label | What it captures |
|---|---|
| `Price Label` | Barcode + price text — built for price-checking scenarios |
| `VIN Label` | Vehicle Identification Number (text and/or barcode) |
| `7-Segment Display` | Numeric values from digital scales, meters, displays |
| `Receipt Scanning` | Structured receipt data (store info, payment, line items). Requires the **Adaptive Recognition Engine** |

#### Use-case → pre-built mapping

When the user describes one of these scenarios, name the pre-built definition directly rather than walking through a custom schema:

- **Smartphone box / IMEI + serial** → `ImeiOneBarcode` (+ `ImeiTwoBarcode` for dual-SIM) + `SerialNumberBarcode`, plus the box's product barcode
- **Grocery shelf-edge / unit price** → `Price Label` (or `UnitPriceText` + `TotalPriceText` + product barcode)
- **Vehicle VIN** → `VIN Label`
- **Scale, meter, or digital readout** → `7-Segment Display`
- **Receipt / till slip / POS receipt** → `Receipt Scanning` (call out the Adaptive Recognition Engine requirement)
- **Expiry / best-before / use-by date** → `ExpiryDateText` (or `DateText` with a configured format)
- **Shipping weight on a label** → `WeightText`

#### Language and character-set limitation

SLC's OCR currently recognizes **only** the Latin character set:

```
0123456789 A-Z a-z ( ) - . / : , $ ¶ "
```

Non-Latin scripts — Japanese (hiragana, katakana, kanji), Chinese, Korean, Cyrillic, Arabic, Hebrew, Thai, Devanagari, etc. — and accented Latin characters are **not** supported by the OCR engine. When a user shares an image or describes a label in one of these scripts, surface this limitation up front before recommending SLC.

**Barcodes on the same label remain readable** regardless of the printed script. A Japanese carton's JAN/EAN/QR code is still captured even though kanji on the box is not. If barcodes alone are sufficient for the user's workflow, SLC (or MatrixScan Batch) can still solve it.

For the canonical per-platform version matrix of pre-built fields, labels, and Adaptive Recognition Engine availability, fetch `features.json` from the live data sources listed in `SKILL.md`.

- **Platforms**: iOS, Android, Web, React Native, Flutter, .NET, Capacitor, Cordova
- **Docs**:
  - iOS: https://docs.scandit.com/sdks/ios/label-capture/intro
  - Android: https://docs.scandit.com/sdks/android/label-capture/intro
  - Web: https://docs.scandit.com/sdks/web/label-capture/intro
  - React Native: https://docs.scandit.com/sdks/react-native/label-capture/intro
  - Flutter: https://docs.scandit.com/sdks/flutter/label-capture/intro
  - .NET: https://docs.scandit.com/sdks/net/ios/label-capture/intro
  - Capacitor: https://docs.scandit.com/sdks/capacitor/label-capture/intro
  - Cordova: https://docs.scandit.com/sdks/cordova/label-capture/intro
- **Sample apps** (path relative to repo base):
  - iOS: `03_Advanced_Batch_Scanning_Samples/05_Smart_Label_Capture/LabelCaptureSimpleSample`
  - Android: `03_Advanced_Batch_Scanning_Samples/05_Smart_Label_Capture/LabelCaptureSimpleSample`
  - Web: `03_Advanced_Batch_Scanning_Samples/05_Smart_Label_Capture/LabelCaptureSimpleSample`
  - React Native: `03_Advanced_Batch_Scanning_Samples/05_Smart_Label_Capture/LabelCaptureSimpleSample`
  - Flutter: `03_Advanced_Batch_Scanning_Samples/05_Smart_Label_Capture/LabelCaptureSimpleSample`
  - .NET (MAUI): `03_Advanced_Batch_Scanning_Samples/05_Smart_Label_Capture/LabelCaptureSimpleSample`

---

## Identity Documents

### ID Capture

- **What it is**: Scans and extracts structured data from identity documents — passports, driver's licenses, national ID cards, visas, and more.
- **Use when**: The user needs to capture data from identity documents, verify document authenticity, or extract personal information from IDs for onboarding, compliance, or identity verification flows.

#### Scanning Zones

ID Capture reads data from three distinct zones on identity documents. Which zone(s) to enable depends on the document type:

| Zone | Description | Typical documents |
|---|---|---|
| **MRZ** (Machine Readable Zone) | The standardized 2–3 line code at the bottom of a document. Highly accurate. | Passports, some national ID cards, visas |
| **VIZ** (Visual Inspection Zone) | The human-readable printed text (name, address, etc.). Broadest field coverage. Required to obtain a cropped image of the document. | Driver's licenses, national ID cards, passports |
| **Barcode** | PDF417 or other barcodes, typically on the back. Machine-encoded, very accurate, fast to read. | US/Canada driver's licenses and IDs (AAMVA standard) |

**Zone selection guidance**: For passports → MRZ. For US/Canadian driver's licenses → AAMVA barcode. For European ID cards → MRZ or VIZ. For general driver's licenses outside North America → VIZ. If a cropped image of the ID is needed, the VIZ must be captured.

#### Document Verification

- **Data consistency checks**: Compares data extracted from the VIZ against barcode data to detect mismatches indicating tampering or fraud.
- **Document authenticity checks**: Validates barcode data against the AAMVA specification to detect fake or forged US driver's licenses and IDs.

Note: Verification features require a specific subscription. Authenticity checks are currently available for US driver's licenses and IDs only.

#### Web Integration: ID Bolt vs. Web SDK

For web-based ID scanning, two integration paths exist:

| | **ID Bolt** (recommended default) | **Web SDK** |
|---|---|---|
| **What it is** | Pre-built, fully managed ID scanning experience with built-in UI | Low-level SDK for full control over the scanning experience |
| **UI/UX** | Complete guided capture flow out of the box — user feedback, error handling, device handover (scan via smartphone from desktop). Accessibility compliant. | Minimal scanning UI — you build everything else |
| **Customization** | White-label: colors, fonts, graphics, button styles. AI-assisted theming. | Full control over every aspect |
| **Integration effort** | Minimal — configure in dashboard, copy-paste embed code | Significant — requires building a full capture workflow |
| **Best for** | B2C consumer-facing websites: travel booking, car rental, onboarding, compliance | B2B/B2E applications or scenarios requiring highly custom scanning experiences |

Default to recommending **ID Bolt** for web applications, especially consumer-facing ones. Only suggest the **Web SDK** if the user explicitly needs deep control over the scanning UX.

- **Platforms**: iOS, Android, Web (ID Bolt or Web SDK), React Native, Flutter, .NET, Capacitor, Cordova
- **Docs**:
  - iOS: https://docs.scandit.com/sdks/ios/id-capture/intro
  - Android: https://docs.scandit.com/sdks/android/id-capture/intro
  - Web: https://docs.scandit.com/sdks/web/id-capture/intro
  - React Native: https://docs.scandit.com/sdks/react-native/id-capture/intro
  - Flutter: https://docs.scandit.com/sdks/flutter/id-capture/intro
  - .NET: https://docs.scandit.com/sdks/net/ios/id-capture/intro
  - Capacitor: https://docs.scandit.com/sdks/capacitor/id-capture/intro
  - Cordova: https://docs.scandit.com/sdks/cordova/id-capture/intro
  - ID Bolt: https://docs.scandit.com/hosted/id-bolt/overview/
- **Sample apps** (path relative to repo base):
  - `02_ID_Scanning_Samples/IdCaptureSimpleSample` — basic ID scanning and data extraction (all platforms)
  - `02_ID_Scanning_Samples/IdCaptureSettingsSample` — interactive exploration of all configuration options (iOS, Android, Web, Flutter, Cordova)

---

## No-Code Integration Path

### Scandit Express

- **What it is**: A no-code way to access Scandit's scanning capabilities without modifying your existing application. It's a standalone app (iOS and Android) that injects scanned data directly into any existing website, app, or system — via keyboard wedge (typing into text fields), Android intents, or connection to a web application running on a separate device.
- **Use when**: The user cannot or does not want to modify their existing application code, but still needs enterprise-grade scanning. This is the primary reason to choose Express over SDK integration.
- **Key point**: Scandit Express is not a separate product with different capabilities — it provides access to the same Scandit scanning features available through the SDK, just without requiring code changes. It is an alternative integration path, not a lesser option.

#### Available Workflows

All major Scandit scanning workflows are available in Express:

- **Inventory count** — scan and count multiple items
- **Find items from a picklist** — AR-guided search for specific items
- **Scan from keyboard** — keyboard wedge into text fields
- **Send data via intents** — send scan data to other Android applications
- **Read ID documents** — capture identity document data
- **Scan labels** — read barcodes and text from labels

#### Data Output Methods

- **Keyboard wedge** — types scanned data directly into any focused text field in any app
- **Android intents** — sends scan data to other applications programmatically
- **Web app connection** — connects Scandit Express to a separate device running a web application
- **Customizable input/output** — configure input and output data for each mode; use your own picklist in CSV format or from a Google Sheet

- **Platforms**: iOS (12.0+), Android (9.0+)
- **Docs**: https://docs.scandit.com/hosted/express/overview
- **Download**: Available on the App Store and Google Play
