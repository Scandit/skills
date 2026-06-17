# Label Capture iOS Integration Guide

Label Capture (Smart Label Capture) extracts multiple fields from a single label in one scan — e.g. a barcode, an expiry date, and a total price on a grocery label. You declare the structure of the label (which fields, required/optional, barcode symbologies or text regex) and the SDK returns all matched fields per frame.

> **Label Capture reads printed text only.** Handwritten text is not supported by the on-device OCR engine or by ARE. If the user's label contains handwritten values, tell them upfront so they can plan a manual-entry fallback (the Validation Flow's manual input field is the standard option).

## Starting from zero? Use the pre-built sample

If the user has no existing app yet, offer the official iOS sample as the fastest path to a working integration — it already has the correct project structure, dependencies, and best practices in place:

- **LabelCaptureSimpleSample (iOS):** <https://github.com/Scandit/datacapture-ios-samples/tree/master/03_Advanced_Batch_Scanning_Samples/05_Smart_Label_Capture/LabelCaptureSimpleSample>

Tell the user to clone the repo and open the sample's Xcode project. Once they have it open, help them:

1. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` (in `ScanViewController.swift`) with their key from <https://ssl.scandit.com>
2. Adjust the label definition to match their use case (fields, symbologies, regex patterns)
3. Build and run on a real device (the simulator has no camera)

Only proceed to the manual integration steps below if the user already has an existing project they need to add Label Capture to.

---

## Prerequisites

- Scandit Data Capture SDK for iOS — add via Swift Package Manager (URL: `https://github.com/Scandit/datacapture-spm`). The SPM products required depend on which field types the label uses:

  | Product | When to add | Why |
  |---|---|---|
  | `ScanditCaptureCore` | **Always** | SDK runtime, camera, `DataCaptureView`. |
  | `ScanditBarcodeCapture` | **Always** | Label Capture has an internal barcode dependency even when no barcode field is declared. |
  | `ScanditLabelCapture` | **Always** | The `LabelCapture` mode, settings, overlays. |
  | `ScanditLabelCaptureText` | **If the label has any text field** — `ExpiryDateText`, `PackingDateText`, `DateText`, `WeightText`, `UnitPriceText`, `TotalPriceText`, `CustomText` — **or any *data-typed/semantic barcode* field** — `SerialNumberBarcode`, `PartNumberBarcode`, `IMEIOneBarcode`, `IMEITwoBarcode`. | Bundles the on-device text/OCR models **and the barcode-semantics models** (`ocr_barcode_semantics_*`, `barcode_label_localization_*`) that the data-typed barcode builders rely on. |
  | `ScanditPriceLabel` | **If the label has a price field** — `UnitPriceText` or `TotalPriceText`. | Bundles the specialised price-text recognizer used in addition to the general text recognizer. Required *in addition to* `ScanditLabelCaptureText`, not instead of it. |

  If a required product is missing at runtime, the `DataCaptureView` surfaces a visible error along the lines of *"Scandit SDK is missing a required resource to operate"* — it does not fail silently. That's the symptom the user will see in the app if you under-recommend the SPM products.

  > **⚠️ Semantic barcode fields need `ScanditLabelCaptureText` even with no text field.** This is the most common SPM under-recommendation. The data-typed barcode builders (`SerialNumberBarcode`, `PartNumberBarcode`, `IMEIOneBarcode`, `IMEITwoBarcode`) are *declared* in `ScanditLabelCapture`, but their recognition models ship in `ScanditLabelCaptureText` — verified in the resolved SDK: `ScanditLabelCapture` bundles no models, while `ScanditLabelCaptureText` carries `ocr_barcode_semantics_default_model`, `barcode_semantics_ocr_detector_default_model`, and `barcode_label_localization_mslc_model_*`. So an IMEI / serial-number / part-number label that links only the three core products hits the missing-resource error at launch. A **plain `CustomBarcode`** with no data-type pattern does **not** need it — only the semantic/data-typed barcode builders do.

  After the user picks fields in Question A below, list exactly which products to add. Rules of thumb: a label whose only barcode is a **plain `CustomBarcode`** (no text field) gets the first three; a label with **any text field** adds `ScanditLabelCaptureText`; a label with **any data-typed/semantic barcode builder** (`SerialNumberBarcode` / `IMEIOneBarcode` / `IMEITwoBarcode` / `PartNumberBarcode`) **also** adds `ScanditLabelCaptureText` even if it has no text field; and a label with `UnitPriceText` / `TotalPriceText` adds both `ScanditLabelCaptureText` and `ScanditPriceLabel`.

- A valid Scandit license key:
  - Sign in at <https://ssl.scandit.com> to generate one.
  - No account yet? Sign up at <https://ssl.scandit.com/dashboard/sign-up?p=test>.
- `NSCameraUsageDescription` in `Info.plist`

## Interactive Label Definition

Before writing any code, walk the user through their label. Ask one question at a time.

> **Do not show code as part of the Q&A round for Questions A and B (the field-definition questions).** That includes "preview" snippets, illustrative DSL examples, sample `LabelCaptureSettings { … }` blocks, or skeleton view-controller code. The Minimal Integration section below is reference material for **after** the user answers A and B — not for quoting during the field-definition questions. Showing code up front pre-supposes field choices the user hasn't made and turns the questions into rhetorical prompts. Ask the field questions first; then write the code. (The overlay decision below is *not* a blocking question — see Question C.)

**Step 0 — Is the *whole label* a pre-built definition?** Before composing fields one by one, check whether the user's label matches one of the pre-built *whole-label* factory definitions. When it does, use the factory — it ships its own fixed field set with anchor/value regexes already tuned, and out-performs anything you hand-assemble from individual builders.

| User's label | iOS factory (Swift) | Since |
|---|---|---|
| "retail **price label**", "shelf label", "price tag", "price check" (barcode + price text) | `LabelDefinition.priceCapture(withName: "price-label")` | 7.4.0 |
| "**VIN**", "vehicle identification number" label | `LabelDefinition.vinLabelDefinition(withName: "vehicle-vin")` | 7.4.0 |
| "**seven-segment** display", LCD/LED meter/scale readout, digital gauge | `LabelDefinition.sevenSegmentDisplay(withName: "display")` | 7.5.0 |

These factory methods live on `LabelDefinition` and slot straight into either initializer form:

```swift
// v8.1+ result-builder DSL
let settings = try LabelCaptureSettings {
    LabelDefinition.priceCapture(withName: "price-label")
}

// v8.0 array initializer
let settings = try LabelCaptureSettings(
    labelDefinitions: [LabelDefinition.priceCapture(withName: "price-label")]
)
```

**Don't guess the field names of a pre-built definition.** A factory ships its own fixed field set — the name you pass in (`"price-label"`) is just the *label's* name, not the field names. Hardcoding a guessed field name silently returns nothing. The field names are fixed by the SDK:

- `priceCapture(withName:)` → `"SKU"` (barcode field, `.ean13UPCA` + `.code128`) and `"priceText"` (price text field). Read them by name or iterate `label.fields`:

  ```swift
  for field in capturedLabel.fields {
      switch field.name {
      case "SKU":       let barcode = field.barcode?.data
      case "priceText": let price = field.text
      default: break
      }
  }
  ```

- `vinLabelDefinition(withName:)` → an optional `text` field and an optional `barcode` field, both matching `[A-Z0-9]{17}`.
- `sevenSegmentDisplay(withName:)` → a single `weight` text field tuned for 7-segment glyphs (it tolerates the common `O`/`0`, `Q`/`0`, `B`/`8` confusions).

> **Pre-built whole-label definitions are NOT Validation-Flow compatible.** `LabelDefinition.priceCapture(withName:)`, `vinLabelDefinition(withName:)`, and `sevenSegmentDisplay(withName:)` are documented as not intended for use with the Validation Flow — using them inside the VF "may result in incorrect data being captured." For these factories, use the **Basic Overlay** (or Advanced Overlay) path, not `LabelCaptureValidationFlowOverlay`. If the user needs the VF guided experience for a price/VIN/seven-segment use case, build an equivalent custom `LabelDefinition` from `CustomBarcode` + the relevant pre-built text fields instead. `priceCapture` additionally requires the **`ScanditPriceLabel`** SPM product (its `priceText` field uses the specialised price recogniser), in addition to `ScanditLabelCaptureText`.

If no whole-label factory fits, build the label from individual fields below — preferring the pre-built field builders.

**Question A — What's on your label?** Present this checklist of supported field types and ask the user to pick everything that applies.

> **Always prefer pre-built field builders over custom ones.** If the user's use case matches a pre-built type (e.g. expiry date, weight, price, IMEI, serial number, part number), use that builder — it ships with tuned regex patterns and anchor text optimised for that field type. Only reach for `CustomText` when no pre-built type covers the field, and only use `CustomBarcode` when none of the pre-built barcode types (`IMEIOneBarcode`, `PartNumberBarcode`, etc.) apply. Do not propose a custom regex up front if a pre-built builder exists for the field type — that's a customer-facing regression in accuracy and a needless maintenance burden.

*Barcode fields:*

- `CustomBarcode(name:symbologies:)` — any barcode, user chooses symbologies
- `IMEIOneBarcode(name:)` — IMEI 1 (typically for smartphone boxes)
- `IMEITwoBarcode(name:)` — IMEI 2
- `PartNumberBarcode(name:)` — part number
- `SerialNumberBarcode(name:)` — serial number

*Text fields (preset recognisers):*

- `ExpiryDateText(name:)` — expiry date (with configurable date format)
- `PackingDateText(name:)` — packing date
- `DateText(name:labelDateFormat:)` — generic date (the `LabelDateFormat` is required)
- `WeightText(name:)` — weight
- `UnitPriceText(name:)` — unit price
- `TotalPriceText(name:)` — total price

> **Language limitation:** predefined text field builders ship with hardcoded `anchorRegex` keyword values in **English, French, and German** only (e.g. "EXP", "BBE", "DLC", "Poids", "Gewicht"). If the label uses anchor text in another language, the predefined builder will not match it. The workaround is to override the defaults via `.anchorRegexes(...)`:
>
> - **Clear all defaults:** `.anchorRegexes([])` — the builder falls back to `valueRegex` alone.
> - **Override with a target-language keyword:** `.anchorRegexes(["<keyword>"])`.
> - **Falling back to `CustomText`:** use `CustomText(name:)` with a custom `anchorRegex` in the target language when none of the above fits.
>
> The `valueRegex` defaults are language-independent (they validate the value format, not the keyword), so they generally work across languages.

*Text fields (custom):*

- `CustomText(name:)` — any text, user provides a regex. Supports any language since both `anchorRegex` and `valueRegex` are fully user-defined.

> **Exclusion rule — data-typed barcode + data-typed text cannot coexist in one `LabelDefinition`.** The SDK refuses to build settings that have data-type patterns (anchor regexes) on *both* a barcode field and a text field of the same definition. Construction throws `SDCLabelCaptureSettingsErrorDomain` code 0: *"Unsupported use of data type patterns for both text and barcode fields. Data type patterns can not be used on both text and barcode label fields."* The data-typed builders involved on each side are:
>
> - *Barcode side (has a built-in data-type pattern):* `SerialNumberBarcode`, `PartNumberBarcode`, `IMEIOneBarcode`, `IMEITwoBarcode`.
> - *Text side (has a built-in anchor regex):* `ExpiryDateText`, `PackingDateText`, `DateText`, `WeightText`, `UnitPriceText`, `TotalPriceText`.
>
> When the user's label has fields of both kinds (e.g. a serial-number barcode **and** an expiry-date text), pick one of these workarounds — never co-emit both data-typed builders unmodified:
>
> - **Preferred — replace the data-typed barcode with `CustomBarcode`.** Ask the user (or infer) which symbology encodes the serial/part number, and use `CustomBarcode(name: "Serial Number", symbologies: [.code128])` (or whichever symbology applies). The data-typed text builder keeps its tuned anchor + value regex, which is where most of the recognition quality lives.
> - **Alternative — call `.anchorRegexes([])` on the data-typed text builder.** This clears the text-side anchor pattern (the language-specific keyword like `EXP`, `BBE`, …) while keeping the `valueRegex` defaults intact, so the conflict goes away. Use this only when the user explicitly wants to keep the data-typed barcode builder and the label's value format is reliable enough on its own. Tell the user it relaxes anchor matching.
>
> Both workarounds are surfaced in the SDK's own unit test for this constraint; the second is what the SDK team uses to assert the build now succeeds after the conflict is cleared.
>
> *Version note:* this exclusion is present on all currently shipped SDKs (through 8.4.x). It is lifted in 8.5.0+ (the engine now allows data-type patterns on both a barcode and a text field in the same label). Apply the workarounds for any release the user is actually on today; only skip them if the project is pinned to 8.5.0 or later.

**Question B — For each selected field:**

- Is it **required** or **optional**?
  - **Required** (default): the label is not considered captured until this field is successfully read. In the Validation Flow, a required field also blocks the user from completing the flow — they must either scan it or type it in manually before the `didCaptureLabelWith:` delegate callback fires.
  - **Optional** (call `.optional(true)` on the builder): the field is captured if found, but its absence does not block capture or the Validation Flow submission. The user can complete the flow without it.
- For `CustomBarcode`: which **symbologies**? Mention to the user that enabling only the symbologies they actually need improves scanning performance and accuracy. iOS symbology enum values use camelCase: `.ean13UPCA`, `.code128`, `.gs1DatabarExpanded`, `.qr`, `.dataMatrix`, etc. — never the Android-style underscore form `.EAN13_UPCA`.
- For `CustomText`: what **regex pattern** should the text match? See the regex notes below.

> **Regex engine limits — keep patterns simple.** The SDK's value/anchor regex engine is built on the standard library `std::regex` (ECMAScript grammar), **not** PCRE/PCRE2. It supports standard character classes (`\d`, `[A-Z]`), quantifiers (`{2}`, `+`, `*`, `?`), alternation (`a|b`), and capture/non-capture groups. It does **not** support **lookbehind** (`(?<= …)` / `(?<! …)`), **named groups** (`(?<name> …)`), or **Unicode property escapes** (`\p{L}`, `\p{Nd}`) — those throw at pattern compilation and the field will silently never match. Lookahead (`(?= …)`) and backreferences (`\1`) happen to compile, but prefer to avoid them too: keep value/anchor regexes to the simple subset above. If a user pastes a complex regex from another engine (Python, PCRE, .NET), rewrite it without those constructs.
- For `ExpiryDateText` / `PackingDateText`: does the user need a specific date format? If so, pass `.labelDateFormat(LabelDateFormat(componentFormat: .MDY, acceptPartialDates: false))` (substitute the component order and partial-date flag for the user's case). Optional — these builders ship with a sensible default.
- For `DateText`: a `LabelDateFormat` is **required** at construction. Pass it directly to the initializer: `DateText(name: "Date", labelDateFormat: LabelDateFormat(componentFormat: .MDY, acceptPartialDates: false))`.

**Question C — Overlay choice (NOT a blocking question).** Do not ask the user upfront. Pick the overlay yourself using this policy, ship the code, and offer the alternatives at the end of your response so the user can swap if they need to.

| Option | When to use |
|---|---|
| **Validation Flow** *(default — write this unless the user has explicitly signalled otherwise)* | Guided scanning experience: a persistent checklist shows which fields have been captured and which are still missing, users can manually type a value when OCR fails, and the result is confirmed before being handed back. This is the right choice for most production integrations — it provides a tested, accessible UX out of the box. Generate VF code per `references/validation-flow.md` (or the Quick swap-in at the end of this file). |
| **Basic Overlay** | Fully automated scanning with live AR highlights rendered directly on the camera feed; no confirmation step and no manual-entry fallback. Pick this **only** when the user has explicitly asked for fully automated scanning, said they don't want a confirmation step, or asked for live AR highlights on the camera feed. The Minimal Integration example below is the Basic Overlay scaffold. |
| **Advanced Overlay** | The app needs a fully custom UI — drawing its own views on top of the camera feed with full control over position, style, and animations. Only choose this when the user has explicitly asked for a fully custom AR / UI experience; flag the significant implementation cost up front. |

**Default behaviour when the user is silent on overlay:** write the Validation Flow integration. Don't ask Question C; don't block. End your response with a short offer so the user can switch if they need to, e.g.:

> I went with the **Validation Flow** — the recommended default for production: a guided checklist, manual-entry fallback when OCR misses a field, and confirmation before the result is handed back. If you want **fully automated scanning with live AR highlights and no confirmation step**, ask me to swap in the **Basic Overlay**; if you need **fully custom AR rendering with your own views**, ask for the **Advanced Overlay**.

**When to ask Question C upfront instead:** only if the user has explicitly asked "which overlay should I use?", "what are the differences between overlays?", or otherwise opened the trade-off discussion themselves. In that case, walk them through the table above and wait for their pick — that's a different intent (advisory) from the default (build it).

> **When advising, always enumerate ALL THREE overlays — even if the user only named two.** If the user asks "Validation Flow or Basic Overlay?", do not answer only on those two: explain both, then also surface **Advanced Overlay** as the third option for cases needing fully custom AR/UI control. Flag its significant implementation cost so the user understands the trade-off. Omitting Advanced Overlay leaves the user uninformed about a real option Scandit supports and is the most common Question-C failure mode. The mention can be brief ("and there's also the Advanced Overlay for fully custom AR — much more implementation cost, only reach for it if VF and Basic aren't flexible enough visually") but it must be present.

**Question D — Which file should the integration code go in?** Then write the code directly into that file. Do not just show it in chat.

## Minimal Integration (Swift / UIKit)

Once the user has answered Questions A and B (fields + required/optional + symbology), generate the integration code. Substitute the placeholder field and label names based on the user's answers. Fields marked optional should call `.optional(true)`; required fields can omit the call (required is the default).

> **Overlay default: Validation Flow.** This Minimal Integration example uses the **Basic Overlay** as the simplest, most-readable scaffold — but per Question C above, the **default overlay you should write is the Validation Flow** unless the user has explicitly asked for fully automated scanning. To produce a VF integration, start from this scaffold and apply the **Quick swap-in** in the "Validation Flow (optional upgrade)" section near the end of this file (or use `references/validation-flow.md` directly): replace `LabelCaptureBasicOverlay` with `LabelCaptureValidationFlowOverlay`, adopt `LabelCaptureValidationFlowDelegate` instead of `LabelCaptureListener`, and drop the `labelCapture.isEnabled = true/false` toggles from `viewWillAppear` / `viewWillDisappear` (the VF overlay manages capture lifecycle internally; the camera lifecycle stays).

> **SDK version check before writing settings code.** The result-builder DSL (`LabelCaptureSettings { LabelDefinition("...") { ... } }`) was introduced in v8.1. On v8.0 it does not exist — fall back to the array initializer `LabelCaptureSettings(labelDefinitions: [LabelDefinition(name:fields:)])`. Read `Package.resolved` for the resolved `datacapture-spm` version before deciding which form to emit. If `Package.resolved` is missing or unreadable and the user has not mentioned a version, default to the v8.1+ DSL — it is the canonical shape for current SDKs — and note the assumption to the user so they can flag it if they're still on v8.0. The example below shows the DSL (v8.1+); see the array-initializer variant immediately after.

```swift
import ScanditBarcodeCapture
import ScanditLabelCapture
import UIKit

class ScanViewController: UIViewController {

    private var context: DataCaptureContext!
    private var camera: Camera?
    private var labelCapture: LabelCapture!
    private var captureView: DataCaptureView!

    @IBOutlet weak var containerView: UIView!

    override func viewDidLoad() {
        super.viewDidLoad()
        try? setupRecognition()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        camera?.switch(toDesiredState: .on)
        labelCapture.isEnabled = true
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        camera?.switch(toDesiredState: .off)
        labelCapture.isEnabled = false
    }

    private func setupRecognition() throws {
        let settings = try LabelCaptureSettings {
            LabelDefinition("Perishable Product") {
                CustomBarcode(
                    name: "Barcode",
                    symbologies: [.ean13UPCA, .code128]
                )

                ExpiryDateText(name: "Expiry Date")

                TotalPriceText(name: "Total Price")
                    .optional(true)
            }
        }

        // Enter your Scandit License key here.
        DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
        context = DataCaptureContext.shared

        if let camera = Camera.default {
            self.camera = camera
            context.setFrameSource(camera, completionHandler: nil)
            camera.apply(LabelCapture.recommendedCameraSettings)
        }

        labelCapture = LabelCapture(context: context, settings: settings)
        labelCapture.addListener(self)

        captureView = DataCaptureView(context: context, frame: containerView.bounds)
        captureView.autoresizingMask = [.flexibleHeight, .flexibleWidth]
        containerView.insertSubview(captureView, at: 0)

        let basicOverlay = LabelCaptureBasicOverlay(labelCapture: labelCapture)
        captureView.addOverlay(basicOverlay)
    }
}

extension ScanViewController: LabelCaptureListener {
    func labelCapture(
        _ labelCapture: LabelCapture,
        didUpdate session: LabelCaptureSession,
        frameData: FrameData
    ) {
        guard let capturedLabel = session.capturedLabels.first else { return }

        let barcodeData = capturedLabel.fields
            .first(where: { $0.name == "Barcode" })?.barcode?.data
        let expiryDate: LabelDateResult? = capturedLabel.fields
            .first(where: { $0.name == "Expiry Date" })?.asDate()

        labelCapture.isEnabled = false

        DispatchQueue.main.async {
            // Process barcodeData and expiryDate on the main thread.
            // expiryDate is a LabelDateResult, NOT a Foundation Date — see below.
        }
    }
}
```

> **`asDate()` returns `LabelDateResult?`, not `Foundation.Date`.** This is the single most common iOS Label Capture mistake: passing the result of `asDate()` straight into `DateFormatter.localizedString(from:)` fails with `Cannot convert value of type 'LabelDateResult' to expected argument type 'Date'`. `LabelDateResult` is a parsed-components struct, but the **Swift type of its numeric components depends on the SDK version**:
>
> | SDK version | `day`, `month`, `year` | Sentinel for missing components |
> |---|---|---|
> | **v8.4+** | `Int?` | `nil` |
> | **pre-v8.4** (v8.0–v8.3) | `Int` (non-optional) | `-1` |
>
> The `dayString`, `monthString`, `yearString` properties are non-optional `String` in **every** version and always carry the raw matched substring — use them for display when you don't need a real `Date`.
>
> **Check `Package.resolved` for the resolved `datacapture-spm` version before generating date-conversion code.** Same rule as the DSL-vs-array decision earlier: read the resolved version, emit the correct shape; if the file is missing, default to v8.4+ and flag the assumption.
>
> ### v8.4+ — `Int?` components
>
> ```swift
> extension LabelDateResult {
>     /// Returns a Foundation.Date if day, month, and year were all parsed; otherwise nil.
>     func toDate(calendar: Calendar = .current) -> Date? {
>         guard let day, let month, let year else { return nil }
>         return calendar.date(from: DateComponents(year: year, month: month, day: day))
>     }
> }
> ```
>
> ### pre-v8.4 — non-optional `Int` with `-1` sentinel
>
> ```swift
> extension LabelDateResult {
>     /// Returns a Foundation.Date if day, month, and year were all parsed (none is the -1 sentinel); otherwise nil.
>     func toDate(calendar: Calendar = .current) -> Date? {
>         guard day != -1, month != -1, year != -1 else { return nil }
>         return calendar.date(from: DateComponents(year: year, month: month, day: day))
>     }
> }
> ```
>
> ### Usage (same in both versions)
>
> ```swift
> if let date = expiryDate?.toDate() {
>     let formatted = DateFormatter.localizedString(from: date, dateStyle: .medium, timeStyle: .none)
> }
> ```
>
> ### Display-only path (works everywhere)
>
> ```swift
> let display = "\(result.dayString)/\(result.monthString)/\(result.yearString)"
> ```
>
> **Mistakes the agent will drift into if you let it improvise — don't:**
>
> - **`expiryDate?.day.map(String.init)` on a pre-v8.4 SDK** — fails compilation with `Value of type 'Int' has no member 'map'` because `.map` only exists on `Optional`. To stringify a pre-v8.4 component, use `String(result.day)` or just `result.dayString`. On v8.4+ where `day` is `Int?`, the `.map` call compiles, but you should still prefer the explicit `guard let` + `DateComponents(...)` pattern shown above so the code remains readable.
> - **`if let`/`guard let` on a pre-v8.4 `Int` component** — fails compilation; pre-v8.4 needs the `!= -1` sentinel check instead.
> - **Force-unwrap (`!`)** of the numeric components — wrong on both versions (pre-v8.4 there's nothing optional to unwrap; v8.4+ it crashes on partial dates).
> - **Three nested `Int?.map` closures** building a `DateComponents` — produces a `Date???` and is unusable. Use the flat extension above.
> - **Inventing a custom date parser** from the `*String` fields when you actually need a `Date` — unnecessary. `Calendar.date(from:DateComponents)` is the right tool; the SDK already parsed the components for you.
>
> When in doubt, paste the version-matched `toDate()` extension verbatim and call `expiryDate?.toDate()`. If the agent gets a build error after a "fix", the most likely cause is it emitted the wrong-version pattern — point it back at this section instead of letting it iterate.

### v8.0 array-initializer variant

If `Package.resolved` pins `datacapture-spm` to a v8.0.x release, the result-builder DSL is not yet available. Build the same settings via the array initializer:

```swift
let labelDefinition = LabelDefinition(
    name: "Perishable Product",
    fields: [
        CustomBarcode(name: "Barcode", symbologies: [.ean13UPCA, .code128]),
        ExpiryDateText(name: "Expiry Date"),
        TotalPriceText(name: "Total Price").optional(true),
    ]
)
let settings = try LabelCaptureSettings(labelDefinitions: [labelDefinition])
```

Everything else in the `setupRecognition()` body (context, camera, view, overlay, listener) is identical. The `Symbology` cases on v8.0 also need to be boxed as `NSNumber` if you hit a bridge error — see the migration guide §2(b).

Notes when generating this code:

- Import ONLY the field types the user actually selected. Do not include `CustomBarcode` if the user picked `IMEIOneBarcode`, and so on.
- The result-builder DSL is `LabelCaptureSettings { LabelDefinition("name") { Field1; Field2; ... } }` (v8.1+). Inside the inner closure, list the fields one per line — no commas, no `.add…` method calls. This is the iOS-specific shape; Android uses a fluent `.addLabel().addCustomBarcode()...buildFluent("...")` chain.
- On v8.0, emit the array initializer shown above instead of the DSL — the DSL types do not exist.
- iOS symbology enum values use camelCase: `.ean13UPCA`, `.code128`, `.gs1DatabarExpanded`, `.qr`, `.dataMatrix`, etc. Do NOT use the Android underscore form (`.EAN13_UPCA`).
- For `CustomBarcode`, the symbologies are passed as a `Set<Symbology>` via the constructor: `CustomBarcode(name: "Barcode", symbologies: [.ean13UPCA, .code128])`.
- For `CustomText`, use `.valueRegex("pattern")` or `.valueRegexes(["p1", "p2"])`. Do NOT use `.setPattern` / `.setPatterns` — those names were renamed in v8 and no longer exist.
- For `ExpiryDateText` / `PackingDateText`, optionally call `.labelDateFormat(LabelDateFormat(componentFormat: .MDY, acceptPartialDates: false))` to control date parsing. `LabelDateComponentFormat` values: `.MDY`, `.DMY`, `.YMD`, etc.
- For `DateText`, the `LabelDateFormat` is **not** optional — pass it in the initializer: `DateText(name: "Date", labelDateFormat: LabelDateFormat(componentFormat: .MDY, acceptPartialDates: false))`. There is no single-argument initializer.
- `labelCapture(_:didUpdate:frameData:)` is called on a background thread. Dispatch any UI updates to the main thread.
- Set `labelCapture.isEnabled = false` synchronously inside the delegate (before dispatching UI work to the main thread) so the next frame doesn't fire another `didUpdate` with the same captured label. Dispatching the disable to the main queue first leaves a 30+-frame window where duplicates can leak through.
- Re-enable the mode (e.g. `labelCapture.isEnabled = true`) when the user is ready to scan again.

## SwiftUI variant

If the user's app is SwiftUI rather than UIKit, follow Scandit's [official SwiftUI guide](https://docs.scandit.com/sdks/ios/label-capture/get-started-with-swift-ui/). Scandit does not ship a native SwiftUI `DataCaptureView` — wrap the UIKit `DataCaptureView` in a `UIViewRepresentable` and hold all SDK objects (context, mode, camera, overlay) on the representable's `Coordinator` so they survive SwiftUI view updates. The Coordinator itself adopts `LabelCaptureListener`.

```swift
import SwiftUI
import ScanditBarcodeCapture
import ScanditCaptureCore
import ScanditLabelCapture

struct LabelCaptureView: UIViewRepresentable {
    let labelDefinitions: [LabelDefinition]
    var onLabelCaptured: ([CapturedLabel]) -> Void

    func makeCoordinator() -> Coordinator {
        Coordinator(labelDefinitions: labelDefinitions, onLabelCaptured: onLabelCaptured)
    }

    func makeUIView(context: Context) -> UIView {
        let coordinator = context.coordinator

        if let camera = Camera.default {
            camera.apply(LabelCapture.recommendedCameraSettings)
            coordinator.dataCaptureContext.setFrameSource(camera)
            camera.switch(toDesiredState: .on)
            coordinator.camera = camera
        }

        coordinator.labelCapture.isEnabled = true

        let captureView = DataCaptureView(context: coordinator.dataCaptureContext, frame: .zero)
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]

        coordinator.overlay = LabelCaptureBasicOverlay(
            labelCapture: coordinator.labelCapture,
            view: captureView
        )

        return captureView
    }

    func updateUIView(_ uiView: UIView, context: Context) {
        // Refresh the callback so the latest closure captured by SwiftUI is used.
        context.coordinator.onLabelCaptured = onLabelCaptured
    }

    static func dismantleUIView(_ uiView: UIView, coordinator: Coordinator) {
        coordinator.labelCapture.isEnabled = false
        coordinator.camera?.switch(toDesiredState: .off)
    }

    final class Coordinator: NSObject, LabelCaptureListener {
        let dataCaptureContext: DataCaptureContext
        let labelCapture: LabelCapture
        var overlay: LabelCaptureBasicOverlay?
        var camera: Camera?
        var onLabelCaptured: ([CapturedLabel]) -> Void

        init(
            labelDefinitions: [LabelDefinition],
            onLabelCaptured: @escaping ([CapturedLabel]) -> Void
        ) {
            DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
            dataCaptureContext = DataCaptureContext.shared
            self.onLabelCaptured = onLabelCaptured

            guard let settings = try? LabelCaptureSettings(labelDefinitions: labelDefinitions) else {
                fatalError("Invalid label definitions")
            }
            labelCapture = LabelCapture(context: dataCaptureContext, settings: settings)
            super.init()
            labelCapture.addListener(self)
        }

        nonisolated func labelCapture(
            _ labelCapture: LabelCapture,
            didUpdate session: LabelCaptureSession,
            frameData: FrameData
        ) {
            let capturedLabels = session.capturedLabels
            guard !capturedLabels.isEmpty else { return }

            // Disable synchronously before hopping to the main thread so the next frame
            // doesn't fire another didUpdate with the same captured label.
            labelCapture.isEnabled = false

            DispatchQueue.main.async { [onLabelCaptured] in
                onLabelCaptured(capturedLabels)
            }
        }
    }
}
```

Hosting view:

```swift
struct ContentView: View {
    private let labelDefinitions: [LabelDefinition] = [
        // Build with the same DSL used in the UIKit example above.
        // (The result-builder DSL produces `[LabelDefinition]` when consumed at the top level.)
        LabelDefinition("Perishable Product") {
            CustomBarcode(name: "Barcode", symbologies: [.ean13UPCA, .code128])
            ExpiryDateText(name: "Expiry Date")
        }
    ]

    var body: some View {
        LabelCaptureView(labelDefinitions: labelDefinitions) { labels in
            // Handle the captured labels on the main thread.
        }
        .ignoresSafeArea()
    }
}
```

Notes for the SwiftUI variant:

- The Coordinator persists across SwiftUI view updates — that's why all SDK objects live on it, not on the `UIViewRepresentable` struct (which is recreated on every `body` evaluation).
- `dismantleUIView` is SwiftUI's signal that the view is being removed from the hierarchy — disable the mode and switch the camera off there. There's no `onAppear` / `onDisappear` wiring needed for lifecycle.
- `updateUIView` refreshes the callback closure on the Coordinator so changes to the parent view's state are reflected in the next capture.
- Disable the mode synchronously inside the listener callback before dispatching to the main thread (same reasoning as the UIKit example above). Skipping this lets duplicate `didUpdate` callbacks fire on subsequent frames before the main-queue work runs.
- The Validation Flow swap-in: change `overlay`'s declared type and assignment to `LabelCaptureValidationFlowOverlay(labelCapture:view:)`, and have the Coordinator adopt `LabelCaptureValidationFlowDelegate` instead of (or in addition to) `LabelCaptureListener`. Drop the manual `isEnabled = false` — the VF overlay manages the capture lifecycle internally. The full-screen requirement still applies — present `LabelCaptureView` via `.fullScreenCover` or as the root of a `NavigationStack` covering the whole screen, not inside a sheet or partial-screen container.

## anchorRegex vs valueRegex

Every text field definition has two kinds of regex:

- **`anchorRegex`** — identifies the *context* of the field on the label. It matches the keyword or phrase near the value (e.g. `"EXP"`, `"BBE"`, `"Best Before"`). The SDK uses this to locate which part of the label contains this field, especially when multiple fields could otherwise match the same value pattern.
- **`valueRegex`** — validates the *content* of the field. It matches the actual data to extract (e.g. `"\\d{2}/\\d{2}/\\d{4}"` for a date).

**Pre-built field builders ship with default anchor and value regexes** tuned for their field type and the supported languages (English, French, German). You can override them with `.anchorRegex("pattern")` / `.anchorRegexes(["p1", "p2"])` and `.valueRegex("pattern")` / `.valueRegexes(["p1", "p2"])`.

**Clearing or overriding the default anchorRegex** — pass an explicit array to `.anchorRegexes(...)`. Use this when the label has no consistent anchor keyword near the field, or when the keyword is in a language other than English/French/German:

```swift
ExpiryDateText(name: "Expiry Date")
    .anchorRegexes([])                // clear defaults entirely, rely on valueRegex
    .valueRegex("\\d{2}/\\d{2}/\\d{4}")

WeightText(name: "Weight")
    .anchorRegexes(["Peso"])          // override with a target-language keyword
```

This works on every pre-built text builder (`ExpiryDateText`, `PackingDateText`, `WeightText`, `UnitPriceText`, `TotalPriceText`) and is the recommended pattern.

**Keep regexes simple.** The SDK regex engine is the standard library `std::regex` (ECMAScript grammar), **not** PCRE/PCRE2. It supports standard character classes (`\d`, `[A-Z]`), quantifiers (`{2}`, `+`, `*`, `?`), alternation (`a|b`), and groups (`(...)`). **Lookbehind assertions (`(?<= ...)` / `(?<! ...)`), named groups (`(?<name> ...)`), and Unicode property escapes (`\p{...}`) are not supported** — they throw at pattern compilation, so the field silently never matches. Lookahead (`(?= ...)`) and backreferences (`\1`) do compile, but prefer to avoid them — stick to the simple subset above. If a user pastes a complex regex from a different engine (Python, PCRE, .NET), rewrite it without those constructs.

## Supported characters

Smart Label Capture's on-device OCR engine reads **printed Latin characters**: `A–Z` (uppercase and lowercase), digits `0–9`, and common punctuation (`. , / : ; - ( ) % $ £ € + *`). It does **not** read:

- **Handwriting** — neither the on-device engine nor ARE recognises handwritten text. If the label has handwritten values, fall back to the Validation Flow's manual input.
- **Non-Latin scripts** — Cyrillic, Greek, CJK (Chinese/Japanese/Korean), Arabic, Hebrew, etc. are not currently supported.
- **Heavily stylised fonts, low-contrast text, or worn/damaged labels** — accuracy degrades sharply. Recommend ARE (see below) for difficult labels.

## Label Capture cannot run alongside Barcode Capture (single active mode)

A `DataCaptureContext` is associated with **one capture mode at a time** — `LabelCapture` and `BarcodeCapture` (or `SparkScan`, `BarcodeCount`, etc.) **cannot both be active on the same context**. This is a core-SDK constraint, not a Label Capture quirk: `context.setMode(_:)` *replaces* the current mode, and if more than one mode is associated with a context "the context will not process any frames and report an error." (See [DataCaptureContext](https://docs.scandit.com/data-capture-sdk/ios/core/api/data-capture-context.html) — `setMode(_:)`, `addMode(_:)`, `removeMode(_:)`, `removeAllModes()`.)

So if a user wants to *also* read a separate barcode (e.g. a shelf-edge barcode in addition to the label), do **not** spin up a second `BarcodeCapture` mode alongside `LabelCapture`. Two patterns:

- **Preferred — model the extra barcode as a label field.** Add a `CustomBarcode` (or a pre-built barcode field like `SerialNumberBarcode`) to the `LabelDefinition`. The label engine then returns that barcode in the same captured label, no second mode needed. This is the right answer whenever the barcode is part of, or read together with, the label.
- **Genuinely separate steps — switch the active mode.** If the two scans are distinct workflow stages (scan a barcode on one screen, a label on another), keep one mode active at a time and call `context.setMode(_:)` to swap between a `BarcodeCapture` and a `LabelCapture` instance when the user moves between steps. Disable the outgoing mode before switching.

> This is distinct from the *"data-typed barcode + data-typed text can't coexist in one `LabelDefinition`"* exclusion rule above: that one is about field combinations *within* a label; this one is about capture *modes* on a context.

## Overlay Integration

### Validation Flow (default overlay — write this unless the user has explicitly asked for something else)

The Validation Flow gives users a guided scanning experience: a persistent checklist shows which fields have been captured and which are still missing, and users can manually type a value when OCR fails. **This is the default overlay the skill writes when the user has not explicitly chosen one** — see Question C in the Interactive Label Definition section above. Skip this section only if the user has explicitly asked for fully automated scanning (Basic Overlay) or fully custom AR (Advanced Overlay).

> **The Validation Flow must be implemented full screen.** Do not embed it inside a card, popover, sheet, or partial-screen container — it will not work correctly. Push the scanning view controller onto the navigation stack, present it modally full-screen, or otherwise dedicate the whole screen to it for the duration of the capture.

For the full Validation Flow integration — overlay setup, delegate methods (including the optional `didSubmitManualInputFor:` v8.1+ and `didUpdateResult:` v8.2+), SDK-version-aware advice, customisation (what's customisable, what's locked, product reasoning), mandatory/optional semantics, coexisting with a `LabelCaptureBasicOverlay` for custom brushes, and capturing the frame image — read `references/validation-flow.md`.

Quick swap-in if you already have the minimal integration above: replace `LabelCaptureBasicOverlay(labelCapture: labelCapture)` + `captureView.addOverlay(basicOverlay)` with:

```swift
let validationFlowOverlay = LabelCaptureValidationFlowOverlay(
    labelCapture: labelCapture,
    view: captureView
)

// v8.2+: per-field placeholder hint shown in the manual-entry input.
let validationFlowSettings = LabelCaptureValidationFlowSettings()
validationFlowSettings.setPlaceholderText("MM/DD/YYYY", forLabelDefinition: "Expiry Date")
validationFlowOverlay.apply(validationFlowSettings)

validationFlowOverlay.delegate = self
```

…and adopt `LabelCaptureValidationFlowDelegate` instead of `LabelCaptureListener`. The only **required** delegate method is `labelCaptureValidationFlowOverlay(_:didCaptureLabelWith:)`. On v8.1+/v8.2+ there are two **optional** methods worth surfacing to the user even if you don't implement them — show their signatures so the user can opt in:

```swift
// Optional (v8.1+) — user manually submitted/corrected a value through the VF UI
func labelCaptureValidationFlowOverlay(_ overlay: LabelCaptureValidationFlowOverlay,
    didSubmitManualInputFor field: LabelField,
    replacingValue oldValue: String?, withValue newValue: String) { }

// Optional (v8.2+) — progressive result update during the flow; carries FrameData?
func labelCaptureValidationFlowOverlay(_ overlay: LabelCaptureValidationFlowOverlay,
    didUpdateResult type: LabelResultUpdateType, asyncId: Int,
    fields: [LabelField], frameData: FrameData?) { }
```

See `references/validation-flow.md` for full version-aware guidance. **Also drop the `labelCapture.isEnabled = true/false` toggles from `viewWillAppear` / `viewWillDisappear`** — the Validation Flow overlay manages the capture lifecycle internally, and leaving the toggles in place fights the overlay. Keep the `camera?.switch(toDesiredState:)` lifecycle calls (the overlay does not control the camera). Then go to `validation-flow.md` for everything else.

### Basic Overlay

Use `LabelCaptureBasicOverlay` when fully automated scanning is sufficient and no confirmation step is needed. It renders AR highlights over detected fields directly in the camera feed.

```swift
let basicOverlay = LabelCaptureBasicOverlay(labelCapture: labelCapture)
captureView.addOverlay(basicOverlay)
```

**How the overlay highlights fields:**

The Basic Overlay draws two layers per detected label:

1. A *label box* around the whole captured label, drawn with `labelBrush`.
2. A *field box* around each field inside the label, drawn with `capturedFieldBrush` (for fields that matched the regex this frame) or `predictedFieldBrush` (for fields the SDK predicts will appear but hasn't fully matched yet).

You can override the defaults globally (the `.clear` `labelBrush` below is an *intentional* override — hiding the whole-label box while keeping field highlights; this is not the same as blanket-clearing every brush "to be safe", which the Advanced Overlay section warns against):

```swift
basicOverlay.labelBrush = Brush(fill: .clear, stroke: .clear, strokeWidth: 0)
basicOverlay.capturedFieldBrush = Brush(
    fill: UIColor.green.withAlphaComponent(0.3),
    stroke: .green,
    strokeWidth: 2
)
basicOverlay.predictedFieldBrush = Brush(
    fill: UIColor.yellow.withAlphaComponent(0.2),
    stroke: .yellow,
    strokeWidth: 2
)
```

**Per-field / per-label brushes via `LabelCaptureBasicOverlayDelegate`:**

```swift
basicOverlay.delegate = self
```

```swift
extension ScanViewController: LabelCaptureBasicOverlayDelegate {
    func labelCaptureBasicOverlay(
        _ overlay: LabelCaptureBasicOverlay,
        brushFor field: LabelField,
        of label: CapturedLabel
    ) -> Brush? {
        // Return a Brush for a specific field, or nil to use the default
        if field.name == "Expiry Date" {
            return Brush(fill: UIColor.red.withAlphaComponent(0.3), stroke: .red, strokeWidth: 2)
        }
        return nil
    }

    func labelCaptureBasicOverlay(
        _ overlay: LabelCaptureBasicOverlay,
        brushFor label: CapturedLabel
    ) -> Brush? {
        // Return a Brush for the whole label bounding box, or nil to use the default
        return nil
    }

    func labelCaptureBasicOverlay(
        _ overlay: LabelCaptureBasicOverlay,
        didTap label: CapturedLabel
    ) {
        // Optional: react to taps on a captured label
    }
}
```

Return `nil` from `brushFor field:` or `brushFor label:` to keep the default brush for that element.

`Brush` is imported from `ScanditCaptureCore` and takes a fill `UIColor`, stroke `UIColor`, and stroke width.

### Advanced Overlay

Use `LabelCaptureAdvancedOverlay` only when the app needs fully custom AR rendering — drawing its own `UIView` subclasses (floating pins, badges, callouts) on top of the camera feed with full positional control. This requires significantly more implementation work than the Basic Overlay. See the [Advanced Configurations](https://docs.scandit.com/sdks/ios/label-capture/advanced/) page for the authoritative reference.

> **Before hand-rolling an Advanced Overlay, re-check Step 0.** Choosing the Advanced Overlay is a *rendering* decision; it does **not** change the label-definition decision. If the user's label is a price/shelf label, VIN, or seven-segment display, you must still build it from the pre-built whole-label factory (`LabelDefinition.priceCapture(withName:)`, `vinLabelDefinition(withName:)`, `sevenSegmentDisplay(withName:)`) rather than hand-composing `CustomBarcode` + `TotalPriceText`. The factory ships tuned anchor/value regexes and out-performs anything you assemble by hand. A common failure mode is reaching for the Advanced Overlay and silently dropping back to a custom definition — don't. (Unlike the Validation Flow, these factories *are* compatible with the Basic and Advanced overlays.)

**The Advanced Overlay is its own delegate-driven AR path — you do not need a `LabelCaptureListener`.** The overlay asks its delegate for a view, an anchor, and an offset **once per newly tracked label** (keyed internally by tracking id) and then caches and repositions that view itself across frames. Do all your work in the delegate; do not attach a separate `LabelCaptureListener` to drive captures, and do not build a per-frame state store. Adding a listener on top leads to per-frame flicker (rebuilding views every frame) and duplicated work — the overlay already does the lifecycle management for you.

**Construct it with the `view:` initializer — which auto-registers the overlay.** Passing the `DataCaptureView` to the initializer adds the overlay to that view for you. Calling `captureView.addOverlay(advancedOverlay)` afterwards is redundant — do not call it.

```swift
// `view:` auto-adds the overlay — do NOT also call captureView.addOverlay(...)
let advancedOverlay = LabelCaptureAdvancedOverlay(labelCapture: labelCapture, view: captureView)
advancedOverlay.delegate = self
```

**Delegate — validate on the spot, no caching.** Because the delegate fires once per newly tracked label, validate the label's fields right there and return a freshly built view. There is no need to cache results in a dictionary or recompute every frame:

```swift
extension ScanViewController: LabelCaptureAdvancedOverlayDelegate {
    // Build the custom view for a newly tracked label. Validate inline from the
    // captured fields — no state store, no LabelCaptureListener.
    func labelCaptureAdvancedOverlay(
        _ overlay: LabelCaptureAdvancedOverlay,
        viewFor capturedLabel: CapturedLabel
    ) -> UIView? {
        let state = validate(capturedLabel)          // pure function of the label's fields
        emitFeedbackOnce(for: capturedLabel)         // once-per-label feedback — see Feedback below
        return StatusPinView(state: state)           // a fresh view; the overlay caches it
    }

    // Where the view is pinned ON the label. The view is CENTERED on the anchor point.
    // For a pin that sits above the label with its tail pointing down at it, use .topCenter
    // (NOT .bottomCenter — that drops the pin onto the bottom edge, away from the content).
    func labelCaptureAdvancedOverlay(
        _ overlay: LabelCaptureAdvancedOverlay,
        anchorFor capturedLabel: CapturedLabel
    ) -> Anchor {
        return .topCenter
    }

    // Fine-tune placement relative to the anchor. Because the view is centered on the
    // anchor point, a zero offset leaves the pin half-overlapping the label box. Lift it
    // by half its own height so the tail tip lands exactly on the label's top edge.
    // `.fraction` is relative to the VIEW's own size; negative y is up.
    func labelCaptureAdvancedOverlay(
        _ overlay: LabelCaptureAdvancedOverlay,
        offsetFor capturedLabel: CapturedLabel
    ) -> PointWithUnit {
        return PointWithUnit(
            x: FloatWithUnit(value: 0, unit: .fraction),
            y: FloatWithUnit(value: -0.5, unit: .fraction)
        )
    }
}
```

> **Anchor semantics — the view is centered on the anchor point.** The `Anchor` you return is a point *on the tracked label/field*, and the overlay centers your view on that point. `.topCenter` therefore centers the view on the top edge of the label; the visible badge then sits above the edge and the tail points down at it. `.bottomCenter` would center it on the bottom edge — usually not what a "pin pointing at the label" wants. The nine cases are `.topLeft`, `.topCenter`, `.topRight`, `.centerLeft`, `.center`, `.centerRight`, `.bottomLeft`, `.bottomCenter`, `.bottomRight`.

> **Offset is in `.fraction` of the view's own size (not the screen).** A zero offset (`PointWithUnit(x: .zero, y: .zero)`) leaves the centered view straddling the anchor, so a downward-pointing pin overlaps the label box by half its height. Returning `y: -0.5` in `.fraction` lifts it by exactly half its height so the tail tip lands on the edge. The y-axis sign isn't pinned in the docs — negative is up per Scandit's samples; if it pushes the pin the wrong way on-device, flip the sign.

**Per-field views.** The delegate also has optional per-field variants — `labelCaptureAdvancedOverlay(_:viewFor:of:)`, `labelCaptureAdvancedOverlay(_:anchorFor:of:)`, and `labelCaptureAdvancedOverlay(_:offsetFor:of:)`, each taking a `LabelField` **and** its parent `CapturedLabel` (`viewFor field: LabelField, of capturedLabel: CapturedLabel`) — when you want to pin a separate view to an individual field (e.g. a badge on just the price field) rather than the whole label. Same anchor/offset semantics apply.

**Pairing with a Basic Overlay for the box.** A common pattern is a Basic Overlay drawing the state-coloured box around a field *and* an Advanced Overlay drawing a floating pin — they coexist on the same `DataCaptureView`. When you do this, only override the brushes you actually need. **Do not blanket-set `labelBrush` / `capturedFieldBrush` / `predictedFieldBrush` to `.clear`** unless you specifically want those elements invisible — clearing them "to be safe" just hides the AR highlights you're paying for. Override a brush only when you have a concrete reason (e.g. you want a per-field colour via `brushFor field:`), and leave the rest at their defaults.

### Feedback (sound & vibration)

`LabelCapture` ships a built-in `LabelCaptureFeedback` whose `success` feedback (beep + vibration) fires on **every successful-capture event** — i.e. repeatedly, frame after frame, while a label stays in view. With the Validation Flow this is fine (capture is confirmed once), but with the **Basic or Advanced Overlay** the result is continuous beeping/vibrating as long as the label is on screen.

For automated/AR overlays where you want feedback **once per captured label**, silence the built-in feedback and emit it yourself:

```swift
// 1. Silence the mode's built-in repeating feedback (do this in setup).
let silentFeedback = LabelCaptureFeedback()
silentFeedback.success = Feedback(vibration: nil, sound: nil)
labelCapture.feedback = silentFeedback

// 2. Emit once per newly tracked label, keyed by tracking id.
private var feedbackEmittedFor = Set<Int>()

private func emitFeedbackOnce(for label: CapturedLabel) {
    guard !feedbackEmittedFor.contains(label.trackingId) else { return }
    feedbackEmittedFor.insert(label.trackingId)
    Feedback.default.emit()   // default beep + vibration, fired exactly once
}
```

Call `emitFeedbackOnce(for:)` from whatever fires once per label in your integration:

- **Advanced Overlay** — from `viewFor` (it already fires once per newly tracked label; the `trackingId` guard is then just belt-and-braces).
- **Basic Overlay** — from your `LabelCaptureListener.labelCapture(_:didUpdate:frameData:)` (iterate `session.capturedLabels` and gate on `trackingId`), or from `brushFor field:` / `brushFor label:` if you've set a `LabelCaptureBasicOverlayDelegate`. The "no `LabelCaptureListener`" rule above is specific to the Advanced Overlay path — a Basic Overlay integration that already uses a listener to read results is the natural place to emit.

`Feedback` and `Feedback.default` come from `ScanditCaptureCore`. Do **not** leave the default `LabelCaptureFeedback` in place and *also* emit your own — you'll get both the repeating built-in beeps and your one-shot. This manual once-per-label recipe is **only** for the Basic and Advanced overlays; the Validation Flow confirms capture once, so leave its feedback alone.

## Capturing the scanned frame image

When users want to store or display the image of the frame alongside the captured label data, convert the `FrameData` to a `UIImage` via the buffer's `.image` property. The approach differs depending on which overlay is in use.

**With Basic Overlay** — use `labelCapture(_:didUpdate:frameData:)`:

```swift
extension ScanViewController: LabelCaptureListener {
    func labelCapture(
        _ labelCapture: LabelCapture,
        didUpdate session: LabelCaptureSession,
        frameData: FrameData
    ) {
        // `didUpdate` fires on EVERY frame (~30 fps). Guard on a non-empty
        // capturedLabels FIRST so we never encode a JPEG on empty frames.
        guard !session.capturedLabels.isEmpty else { return }
        let capturedLabel = session.capturedLabels.first!

        // Disable the mode so scanning stops before we read the frame
        labelCapture.isEnabled = false

        // Only reached after the guard above — jpegData is never called per-frame unconditionally.
        let image = frameData.imageBuffers.first?.image
        let jpeg = image?.jpegData(compressionQuality: 0.3)

        DispatchQueue.main.async {
            // Hand the JPEG + captured fields back to the UI
            self.storeScanResult(jpeg: jpeg, fields: capturedLabel.fields)
        }
    }
}
```

`didUpdate` fires on every camera frame (~30 times per second), so guard on `session.capturedLabels` being non-empty and disable the mode before reading the buffer — otherwise you'll thrash JPEG encoding on every frame.

**JPEG is the fastest encoding** for the cached image — `.jpegData(compressionQuality: 0.3)` is a good default (small file, low CPU). PNG is significantly slower because of the lossless compression. Only reach for PNG if the customer specifically needs a lossless screenshot of the label.

**With Validation Flow** — the VF's required delegate callback `labelCaptureValidationFlowOverlay(_:didCaptureLabelWith:)` does **not** receive a `FrameData`. To capture the frame image alongside a VF result you have two options, depending on the SDK version:

- v8.2+: implement the optional `didUpdateResult:asyncId:fields:frameData:` delegate method — it fires during the flow with `FrameData?`.
- pre-v8.2: attach a `LabelCaptureBasicOverlay` alongside the VF (they can coexist) and capture the frame via `LabelCaptureListener` as shown above; cache the most recent JPEG and hand it back when `didCaptureLabelWith:` confirms the final result.

Full code in `references/validation-flow.md`.

---

## ARE — Adaptive Recognition Engine

ARE is Scandit's cloud-based fallback for on-device text recognition. When the on-device OCR engine cannot confidently read a text field, ARE sends the frame to the cloud for processing and returns the result. This improves accuracy on difficult labels (low contrast, unusual fonts, worn text) without requiring a custom model.

**Important constraints — tell the user all of these before they try to enable it:**

- **Validation Flow only.** ARE works exclusively with the Validation Flow overlay (`LabelCaptureValidationFlowOverlay`). It does not work with `LabelCaptureBasicOverlay` or `LabelCaptureAdvancedOverlay`.
- **Requires a license key with the ARE feature flag.** The standard license key does not include ARE. Trial license keys can be issued with ARE enabled for evaluation — direct the user to <support@scandit.com> to request one.
- **For production use, contact Scandit.** ARE is in Beta and requires explicit enablement on the production license key. Tell the user to contact <support@scandit.com> to get it enabled for their production key before going live.
- **Handwriting is still unsupported.** ARE improves accuracy on printed text in adverse conditions; it does not enable handwritten-character recognition.

Enable ARE by setting `.adaptiveRecognition(.auto)` on the label definition:

```swift
let settings = try LabelCaptureSettings {
    LabelDefinition("Perishable Product") {
        CustomBarcode(name: "Barcode", symbologies: [.ean13UPCA])
        ExpiryDateText(name: "Expiry Date")
    }
    .adaptiveRecognition(.auto)
}
```

With `.auto`, the SDK decides when to invoke the cloud fallback. Results arrive through the same Validation Flow callback — no additional handling is needed.

Mention ARE only if the user asks about improving OCR accuracy or mentions difficulty reading certain labels. Do not enable it by default.

## Receipt Scanning (Beta — built on ARE)

If the user wants to extract structured data from a **whole receipt** (store, totals, line items) rather than a few fields off a printed label, that's **Receipt Scanning** — a separate ARE-powered feature available on iOS since SDK 7.6.0. It is **Beta** and, like ARE generally, requires a license key with the Adaptive Recognition Engine enabled. Flag this up front and direct the user to <support@scandit.com> to get it enabled on their subscription before they try to use it. Do not present it as generally available.

Receipt Scanning does **not** use the standard label-capture overlays or a `LabelDefinition`. It uses a different integration pattern:

- The overlay is **`LabelCaptureAdaptiveRecognitionOverlay`** (instead of `LabelCaptureBasicOverlay` / `LabelCaptureValidationFlowOverlay`).
- Results arrive through a **`LabelCaptureAdaptiveRecognitionDelegate`**, whose recognition callback delivers a **`ReceiptScanningResult`**. (The iOS Swift name is `…Delegate`; "Listener" is the cross-platform name and does **not** exist on iOS.)

`ReceiptScanningResult` carries the parsed receipt — all fields are optional because not every receipt prints every value:

| Field | Type | Description |
|---|---|---|
| `storeName` | `String?` | Store / merchant name |
| `storeAddress` | `String?` | Full store address |
| `storeCity` | `String?` | City |
| `date` | `String?` | Transaction date |
| `time` | `String?` | Transaction time |
| `paymentPreTaxTotal` | `NSDecimalNumber?` | Balance before taxes |
| `paymentTax` | `NSDecimalNumber?` | Total tax |
| `paymentTotal` | `NSDecimalNumber?` | Total paid |
| `loyaltyNumber` | `NSNumber?` | Loyalty program identifier |
| `lineItems` | `[ReceiptScanningLineItem]` | Each item carries `name` (`String`), `unitPrice` / `discount` / `totalPrice` (`NSDecimalNumber?`), and `quantity` (`NSDecimalNumber`) |

> The monetary fields are `NSDecimalNumber?` and `loyaltyNumber` is `NSNumber?` (not Swift `Float?` / `Int?`) — code written against `Float?` / `Int?` will not compile. Bridge with `.doubleValue` / `.intValue` (or use `NSDecimalNumber` directly for exact currency math).

> **Verify the exact delegate selector before writing the delegate.** The Receipt Scanning overlay and delegate are Beta, and the receipt callback's precise Swift signature is not pinned in the integration references here. Fetch the [Advanced Configurations](https://docs.scandit.com/sdks/ios/label-capture/advanced/) page (Receipt Scanning section) and the linked API page for `LabelCaptureAdaptiveRecognitionDelegate` before emitting the delegate method — don't guess the selector. The overlay type (`LabelCaptureAdaptiveRecognitionOverlay`), the delegate type (`LabelCaptureAdaptiveRecognitionDelegate` — `NS_SWIFT_NAME` confirmed in `SDCLabelCaptureAdaptiveRecognitionOverlay.h`), and the result type (`ReceiptScanningResult`) above are confirmed; the delegate method name is not, so look it up.

## Setup Checklist

After the integration code and overlay choice are in place, show this checklist:

1. Add the SPM package `https://github.com/Scandit/datacapture-spm` and link the products required by the field types in this label (see Prerequisites table for the full rule):
   - **Always:** `ScanditCaptureCore`, `ScanditBarcodeCapture`, `ScanditLabelCapture`.
   - **If the label has any text field** (e.g. `ExpiryDateText`, `DateText`, `WeightText`, `UnitPriceText`, `TotalPriceText`, `CustomText`): also link `ScanditLabelCaptureText`.
   - **If the label has a data-typed/semantic barcode field** (`SerialNumberBarcode`, `PartNumberBarcode`, `IMEIOneBarcode`, `IMEITwoBarcode`): also link `ScanditLabelCaptureText` **even if there is no text field** — these builders' models ship in that product (see the ⚠️ note in Prerequisites). A plain `CustomBarcode` does not need it.
   - **If the label has a price field** (`UnitPriceText` or `TotalPriceText`): also link `ScanditPriceLabel` (in addition to `ScanditLabelCaptureText`, not instead of it).
   - List only the products this specific label needs. `ScanditLabelCaptureText` is *not* needed for a plain-`CustomBarcode` barcode-only label, but it **is** required for a semantic-barcode (IMEI / serial / part-number) label or any text/price label. A missing text/price/semantics product is a common failure: the `DataCaptureView` reports a missing-resource error, or text/semantic fields produce no result.
2. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your license key from <https://ssl.scandit.com>.
3. Add `NSCameraUsageDescription` to your `Info.plist` with a user-facing reason string.
4. Add a `UIView` outlet named `containerView` to your view controller (or replace `containerView` with `view` to use the whole VC's view).
5. Build and run on a real device — the simulator has no camera.

## Where to Go Next

After the core integration is running, point the user at the right resource for follow-ups:

- [Label Definitions](https://docs.scandit.com/sdks/ios/label-capture/label-definitions/) — full catalogue of pre-built text/barcode field types and how to tune their regex anchors and value patterns.
- [Advanced Configurations](https://docs.scandit.com/sdks/ios/label-capture/advanced/) — Validation Flow customisation, adaptive recognition, custom overlays.
- [LabelCaptureSimpleSample](https://github.com/Scandit/datacapture-ios-samples/tree/master/03_Advanced_Batch_Scanning_Samples/05_Smart_Label_Capture/LabelCaptureSimpleSample) — working reference sample.
