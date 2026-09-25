# Third-Party Barcode Scanner → SparkScan Migration

## Before Anything Else

Read the existing code. Do not ask the user to describe what their scanner does. Identify:
- Which framework is in use (read the imports)
- Which symbologies are enabled
- What result handling logic exists (deduplication, filtering, accumulation)
- What data models are defined
- How the scanner is presented (modal, embedded, full-screen)

---

## Remove

- The old framework's imports
- The scanner/detector class instance and all its setup code
- The old delegate or callback conformance
- Any UI presentation code specific to the old scanner (e.g. modal presentation)

---

## Integrate SparkScan

Follow `references/integration.md`. When configuring `SparkScanSettings`, map the symbologies from the old scanner.

---

## Preserve

- Custom data models — keep as-is
- Result accumulation and deduplication logic — move verbatim into the `SparkScanListener` callback
- Any downstream business logic triggered on scan result

---

When done, show only what changed. Do not list APIs that were unchanged.
