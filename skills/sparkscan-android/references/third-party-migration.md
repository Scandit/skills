# Third-Party Barcode Scanner → SparkScan Migration

## Before Anything Else

Read the existing code. Do not ask the user to describe what their scanner does. Identify:
- Which framework is in use (read the imports)
- Which symbologies are enabled
- What result handling logic exists (deduplication, filtering, accumulation)
- What data models are defined
- How the scanner is launched (Activity, Fragment, intent-based, embedded view)

---

## Remove

- The old framework's imports and dependencies
- The scanner class instance and all its setup code
- The old callback or listener conformance
- Any UI code specific to the old scanner (e.g. intent launch, dialog, overlay)

---

## Integrate SparkScan

Follow `references/integration.md`. When configuring `SparkScanSettings`, map the symbologies from the old scanner.

---

## Preserve

- Custom data models — keep as-is
- Result accumulation and deduplication logic — move verbatim into the `onBarcodeScanned` callback
- Any downstream business logic triggered on scan result

---

When done, show only what changed. Do not list APIs that were unchanged.
