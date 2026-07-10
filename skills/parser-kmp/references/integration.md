# Parser KMP Integration Guide

The Parser turns a raw barcode/RFID data string into named, typed fields. It has no camera, no
UI, and no scanning mode of its own — it is a pure data-transformation component that sits on top
of a `DataCaptureContext`. Typical inputs are `barcode.data` / `barcode.rawData` from a
`BarcodeCapture` or `SparkScan` scan result, but any string or byte array in a supported format
works (e.g. read from a file, pasted by a user, etc.).

Examples below live in a shared `commonMain` Kotlin module and work identically on the Android and
iOS targets — the Parser API has no platform-divergent construction signature the way some UI
components do.

## Prerequisites

- Scandit Data Capture SDK for KMP, version `8.6.0` — add the `core` and `parser` modules.

  Android (Gradle), `shared/build.gradle.kts`:
  ```kotlin
  kotlin {
      sourceSets {
          commonMain.dependencies {
              implementation("com.scandit.datacapture.kmp:core:8.6.0")
              implementation("com.scandit.datacapture.kmp:parser:8.6.0")
          }
      }
  }
  ```

  iOS: consume the published Swift Package `Scandit/datacapture-kmp-spm`. Kotlin/Native
  frameworks are closed worlds, so an app links **exactly one** Kotlin umbrella framework — pick
  the smallest variant that contains `parser`. For pure parsing with no scanning, that's the
  `barcode-parser` variant's `ScanditKmpBarcodeParser` product (`barcode` is pulled in as a
  dependency of the umbrella build even if you never construct `BarcodeCapture`); use `id-barcode-
  parser`'s product instead if you also need ID Capture. Do not add a second Scandit Kotlin
  framework product alongside it.

- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
  - The license key must have the **parser** feature enabled.

- No camera permission is required for pure parsing. If you are also scanning barcodes with
  BarcodeCapture/SparkScan to feed the parser, that mode's own camera setup and runtime permission
  request still apply — see `barcode-capture-kmp` / `sparkscan-kmp` for that half.

## Creating a Parser

Initialize the shared `DataCaptureContext` once (reuse it — do not create a new one per parse),
then create a `Parser` for the specific `ParserDataFormat` you expect:

```kotlin
import com.kmp.datacapture.core.capture.DataCaptureContext
import com.kmp.datacapture.parser.Parser
import com.kmp.datacapture.parser.ParserDataFormat

val dataCaptureContext = DataCaptureContext.initialize("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

val parser = Parser.forFormat(dataCaptureContext, ParserDataFormat.GS1_AI)
```

`ParserDataFormat` supports:

| Value | Format |
|---|---|
| `GS1_AI` | GS1 Application Identifier |
| `GS1_DIGITAL_LINK` | GS1 Digital Link |
| `HIBC` | Health Industry Bar Code |
| `SWISS_QR` | Swiss QR-bill |
| `VIN` | Vehicle Identification Number |
| `IATA_BCBP` | IATA Bar Coded Boarding Pass |
| `EPC` | Electronic Product Code (RFID Tag EPC Memory Bank Contents, SGTIN-96 hex) |

A `Parser` instance is bound to a single data format for its lifetime — create a new `Parser` (or
call `setOptions` again) if the format or its options change; there is no `setFormat` method.

Optionally configure format-specific options with `setOptions`, a plain `Map<String, Any>`:

```kotlin
parser.setOptions(
    mapOf(
        "allowHumanReadableCodes" to true,
        "strictMode" to true,
    ),
)
```

Available keys are format-specific — only GS1 AI, Swiss QR, VIN, and GS1 Digital Link currently
take options (e.g. Swiss QR's `strictMode` / `minimalVersion`, VIN's `strictMode` /
`falsePositiveCompensation`, GS1 Digital Link's `strictMode` / `outputHumanReadableString`). HIBC,
IATA BCBP, and EPC take no options — passing one has no effect. Consult each format's
documentation page for the full, current option set before relying on a specific key.

## Parsing data and reading fields

Call `parseString` for a string payload, or `parseRawData` for raw bytes (e.g. an RFID tag's EPC
memory bank contents):

```kotlin
import com.kmp.datacapture.parser.ParsedData

val parsedData: ParsedData = parser.parseString("0109506000134352")
```

```kotlin
val parsedDataFromBytes: ParsedData = parser.parseRawData(byteArrayOf(/* ... */))
```

`ParsedData` gives you three ways to read the result:

```kotlin
// All fields, in the order they appeared in the input string
val fields = parsedData.fields

// By-name lookup — field names are format-specific
val expiryField = parsedData.fieldsByName["expiryDate"]

// As a JSON string
val json = parsedData.jsonString
```

Each `ParsedField` exposes:

```kotlin
for (field in parsedData.fields) {
    val name: String = field.name
    val parsed: Any? = field.parsed       // runtime type is field-specific
    val rawString: String = field.rawString
    val warnings = field.warnings          // List<ParserIssue>, usually empty
}
```

`field.parsed`'s actual type (string, number, map, list, etc.) depends on which field it is —
consult the data format's field documentation before casting it.

## Combining with a barcode scanning result

Feed the string or raw bytes of a scanned `Barcode` straight into the parser — no conversion step
needed:

```kotlin
// Inside a BarcodeCaptureListener.onBarcodeScanned / SparkScan scan callback:
val barcode = session.newlyRecognizedBarcode // or the equivalent scan-result accessor
val data = barcode.data ?: return
val parsedData = parser.parseString(data)
```

Setting up the camera, the `BarcodeCapture`/`SparkScan` mode, and handling the scan callback
itself is out of scope for this skill — see `barcode-capture-kmp` (low-level, manual UI) or
`sparkscan-kmp` (pre-built scanning UI) for that half of the integration.

## Handling parser issues and errors

`parseString` / `parseRawData` throw on failure — catch `ParserException` specifically to get
structured error information, and fall back to the generic `Exception` for anything unexpected:

```kotlin
import com.kmp.datacapture.parser.ParserException

try {
    val parsedData = parser.parseString(input)
    // use parsedData
} catch (e: ParserException) {
    val code = e.code
    val message = e.message
    val additionalInfo = e.additionalInfo // Map<ParserIssueAdditionalInfoKey, String>
    // surface code/message/additionalInfo to the user or logs
} catch (e: Exception) {
    // unexpected failure
}
```

A successful parse can still carry **warnings** on individual fields — these do not throw, they
show up on `ParsedField.warnings` and are reflected in `ParsedData.fieldsWithIssues`:

```kotlin
val fieldsWithIssues = parsedData.fieldsWithIssues // List<ParsedField>, only fields with warnings

for (field in fieldsWithIssues) {
    for (issue in field.warnings) {
        val code = issue.code       // ParserIssueCode
        val message = issue.message // English description
    }
}
```

`ParserIssueCode` values include `NONE`, `UNSPECIFIED`, `MANDATORY_EPD_MISSING`, `INVALID_DATE`,
`STRING_TOO_SHORT`, `WRONG_STARTING_CHARACTERS`, `INVALID_SEPARATION_BETWEEN_ELEMENTS`,
`UNSUPPORTED_VERSION`, `INCOMPLETE_CODE`, `EMPTY_ELEMENT_CONTENT`, `INVALID_ELEMENT_LENGTH`,
`TOO_LONG_ELEMENT`, `NON_EMPTY_ELEMENT_CONTENT`, `INVALID_CHARSET_IN_ELEMENT`,
`TOO_MANY_ALT_PMT_FIELDS`, `CANNOT_CONTAIN_SPACES`.

## Pitfalls

- **Wrong package root.** Always `com.kmp.datacapture.parser.*` — never
  `com.scandit.datacapture.parser.*` (that's the Android-native or JVM package, not KMP's).
- **No `AAMVA` format.** `ParserDataFormat` has no AAMVA value. Driver's license barcode data is
  decoded by ID Capture, not this Parser — do not try to parse it with `Parser.forFormat`.
- **Catching only `Exception`.** You lose `code` and `additionalInfo` if you don't catch
  `ParserException` specifically before the generic `Exception` fallback.
- **Reusing a `Parser` across formats.** A `Parser` is created for one `ParserDataFormat` — build
  a new one (or reconfigure via `setOptions` for the same format) rather than expecting a single
  instance to parse multiple unrelated formats.
- **Ignoring `fieldsWithIssues`.** A parse can succeed (no exception) while individual fields still
  carry warnings — check `parsedData.fieldsWithIssues` / `field.warnings` rather than assuming a
  non-throwing parse means every field is clean.
- **Casting `field.parsed` blindly.** Its runtime type is field-specific; check the format's field
  docs instead of assuming `String` or `Double` everywhere.
- **Skipping the license/parser feature check.** `Parser.forFormat` throws if the license key used
  to construct the `DataCaptureContext` doesn't have the parser feature enabled — this is a
  licensing issue, not an API misuse bug.
- **Two Scandit Kotlin frameworks on iOS.** Kotlin/Native frameworks can't be mixed — pick the one
  SPM umbrella variant (e.g. `barcode-parser`) that already contains everything you need instead of
  trying to link `parser` and `barcode` as separate products.
