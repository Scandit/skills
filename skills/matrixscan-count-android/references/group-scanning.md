# MatrixScan Count Android — Group Scanning

Group scanning lets the user split one long counting session into several **groups** — for example one
group per pallet or per box — using extra on-screen controls. It assumes the basic integration is already
in place (see `integration.md`); here we only enable it.

> **Group scanning vs. clustering.** Group scanning splits one counting session into separate batches the
> user advances through (Next Group / Redo). If instead you want to group barcodes that physically belong
> together (e.g. a multi-pack) into one highlight within a single count, that is **clustering** — see
> `clustering.md`.

## Enable group scanning

Set `groupScanningEnabled` on `BarcodeCountSettings` **before** constructing the `BarcodeCount` mode:

```kotlin
val settings = BarcodeCountSettings()
settings.setSymbologyEnabled(Symbology.EAN13_UPCA, true)
// … enable your other symbologies …
settings.groupScanningEnabled = true

val barcodeCount = BarcodeCount.forDataCaptureContext(dataCaptureContext, settings)
```

When enabled, the built-in UI shows two extra controls (they take the place of the Clear Screen button):

- **Next Group** — finishes the current group and starts a fresh one.
- **Redo** — discards the current group.

## Results are still a flat list

Group scanning is a **UI / workflow aid only** — it does **not** change how results are delivered. There
is **no grouped-result callback**: the scanned barcodes still come back as a **flat list** through the
normal `BarcodeCountListener.onScan(barcodeCount, session, data)` (`session.recognizedBarcodes`), exactly
as in the base integration. If you need per-group bookkeeping, track it in your own app logic (e.g. in
the `onNextGroup`-equivalent moment, snapshot `session.recognizedBarcodes`).

## Customizing the control labels (optional)

The Next Group and Redo button labels are changed with **methods** on the view (they are setter methods,
not Kotlin properties):

```kotlin
barcodeCountView.setNextGroupButtonText("Next pallet")
barcodeCountView.setRedoButtonText("Clear group")
```

`setNextGroupButtonContentDescription(...)` / `setRedoButtonContentDescription(...)` set the
accessibility descriptions.

## After wiring up

Build the project. If a group-scanning API doesn't resolve, fetch the
[BarcodeCount API reference](https://docs.scandit.com/data-capture-sdk/android/barcode-capture/api.html) to
confirm the current signature before guessing. Always include the docs link in your answer.
