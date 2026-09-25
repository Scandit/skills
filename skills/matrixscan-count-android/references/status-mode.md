# MatrixScan Count Android — Status Mode

Status mode lets you annotate each counted barcode with a **status** — a per-barcode status icon. The
statuses are shown automatically as barcodes are scanned (the recommended setup), or optionally only when
the user taps the status-mode button. You decide each barcode's status by implementing a **status
provider**, which the SDK calls with the current barcodes and which hands back a status for each. This
guide assumes the basic integration is already in place (see `integration.md`); here we only add status
mode.

> Verify any status-mode symbol against the
> [BarcodeCount API reference](https://docs.scandit.com/data-capture-sdk/android/barcode-capture/api.html)
> before guessing.

## Register a status provider

Implement `BarcodeCountStatusProvider` and register it on the view. The recommended setup is to show the
statuses automatically as barcodes are scanned with `shouldShowStatusIconsOnScan = true`:

```kotlin
barcodeCountView.setStatusProvider(statusProvider)
barcodeCountView.shouldShowStatusIconsOnScan = true   // statuses appear automatically on scan (recommended)
```

See **Showing the statuses** below for the button-only alternative.

## Provide a status per barcode

The SDK calls your provider whenever it needs statuses, handing you the current barcodes and a callback.
Build one `BarcodeCountStatusItem` per barcode, wrap them in a result, and deliver it via the callback.
The work can be **asynchronous** — e.g. look the statuses up in a backend and call `onStatusReady` when
the response arrives:

```kotlin
val statusProvider = object : BarcodeCountStatusProvider {
    override fun onStatusRequested(
        barcodes: List<TrackedBarcode>,
        callback: BarcodeCountStatusProviderCallback
    ) {
        // Build a status item per barcode. On Android the status is one of the built-in
        // BarcodeCountStatus enum values (NONE, NOT_AVAILABLE, EXPIRED, FRAGILE, QUALITY_CHECK,
        // LOW_STOCK, WRONG, EXPIRING_SOON).
        val statusItems = barcodes.map { trackedBarcode ->
            // `trackedBarcode` is a TrackedBarcode; read its payload via trackedBarcode.barcode.data.
            BarcodeCountStatusItem.create(trackedBarcode, BarcodeCountStatus.EXPIRED)
        }

        val result = BarcodeCountStatusResultSuccess.create(
            statusItems,
            "Reviewing items",   // shown when status mode is enabled (nullable)
            "Status mode off"    // shown when status mode is disabled (nullable)
        )
        callback.onStatusReady(result)
    }
}
```

- `onStatusRequested(barcodes, callback)` is the one method to implement. Deliver your result **exactly
  once** per call via `callback.onStatusReady(...)` — synchronously or after async work.
- `BarcodeCountStatusItem.create(trackedBarcode, status)` takes the `TrackedBarcode` and a
  `BarcodeCountStatus`. Use `BarcodeCountStatus.NONE` to show no status for a barcode.
- The `BarcodeCountStatus` values are a fixed set: `NONE`, `NOT_AVAILABLE`, `EXPIRED`, `FRAGILE`,
  `QUALITY_CHECK`, `LOW_STOCK`, `WRONG`, `EXPIRING_SOON`.

## Result types

Resolving statuses is meant to be **asynchronous** — you typically fetch them from a backend or some other
slow source. Whatever the outcome of that lookup, deliver one of three result types to
`callback.onStatusReady(...)`, each created via its static `create(...)` factory:

- `BarcodeCountStatusResultSuccess.create(statusList, statusModeEnabledMessage, statusModeDisabledMessage)`
  — everything went fine; you resolved statuses for the barcodes. The two messages are shown when status
  mode is toggled on / off (pass `null` to omit).
- `BarcodeCountStatusResultError.create(statusList, errorMessage, statusModeDisabledMessage)` — something
  went wrong, but you still got **at least some** statuses; show those and surface the error message.
- `BarcodeCountStatusResultAbort.create(errorMessage)` — abort: you couldn't get any statuses (the lookup
  failed entirely), or you don't want to display any for some other reason.

All three `create(...)` calls return a `BarcodeCountStatusResult`, which is what `onStatusReady` expects.

## Showing the statuses

There are two ways to present the statuses; pick one.

**Recommended — show them automatically on scan.** Each barcode's status icon appears as soon as it's
counted, with no extra tap:

```kotlin
barcodeCountView.shouldShowStatusIconsOnScan = true
```

**Alternative — show them only when the user taps the status-mode button.** A button in the UI toggles
status mode, where the normal highlights are replaced by the status icons:

```kotlin
barcodeCountView.shouldShowStatusModeButton = true   // show the button
// Leave shouldShowStatusIconsOnScan = false (its default), which is what the button flow needs.
```

If `shouldShowStatusIconsOnScan` is `true`, the status-mode button is effectively redundant. Since it's
`false` by default, you usually only set `shouldShowStatusModeButton` for the button flow.

## After wiring up

Build the project. If a status-mode API doesn't resolve or the provider isn't called, fetch the
[Advanced Configurations](https://docs.scandit.com/sdks/android/matrixscan-count/advanced/) page and the
[BarcodeCount API reference](https://docs.scandit.com/data-capture-sdk/android/barcode-capture/api.html)
to confirm the current signatures before guessing. Always include the docs link in your answer.
