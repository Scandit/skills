# MatrixScan Count Android — Scanning Against a List

This guide covers scanning against a **known list of expected barcodes** (a manifest, a receiving
order, an inventory count, etc.). You declare which barcodes — and how many of each — are expected, and
MatrixScan Count tracks progress against that list and flags barcodes that aren't on it. It assumes the
basic integration is already in place (see `integration.md`); here we add the capture list on top.

When a capture list is set, the built-in UI automatically shows a **progress bar** (e.g. 7/10) and marks
scanned barcodes that are **not in the list** with a distinct (red) highlight.

## Build and set the expected list

Describe each expected barcode with a `TargetBarcode` (its data string and the quantity expected), wrap
them in a `BarcodeCountCaptureList` with a listener, and apply it to the mode with
`setBarcodeCountCaptureList(...)`:

```kotlin
val targetBarcodes = listOf(
    TargetBarcode.create("0123456789012", 2),
    TargetBarcode.create("9780201379624", 1)
)
val captureList = BarcodeCountCaptureList.create(this, targetBarcodes)  // 'this' = the listener below
barcodeCount.setBarcodeCountCaptureList(captureList)
```

- `TargetBarcode.create(data, quantity)` and `BarcodeCountCaptureList.create(listener, targets)` are
  **static factories** — not constructors.
- `targetBarcodes` is a **`List<TargetBarcode>`** (not a Set).
- The `listener` is a `BarcodeCountCaptureListListener` (below).
- Apply it on the `BarcodeCount` mode (e.g. at the end of your setup). There is no "clear" overload that
  takes `null`; build a fresh empty list if you need to reset.

## Observe progress (`BarcodeCountCaptureListListener`)

Implement `BarcodeCountCaptureListListener` to be notified as the list is filled:

```kotlin
class CountActivity : AppCompatActivity(), BarcodeCountCaptureListListener {

    override fun onCaptureListSessionUpdated(
        captureList: BarcodeCountCaptureList,
        session: BarcodeCountCaptureListSession
    ) {
        // Progress changed — read session.correctBarcodes / wrongBarcodes / missingBarcodes etc.
    }

    override fun onCaptureListCompleted(
        captureList: BarcodeCountCaptureList,
        session: BarcodeCountCaptureListSession
    ) {
        // Every expected barcode has been scanned.
    }
}
```

> `onObservationStarted(captureList)` / `onObservationStopped(captureList)` are also available
> (optional). These callbacks may arrive off the main thread — hop to the main thread before touching
> UI.

`BarcodeCountCaptureListSession` reports the breakdown:

- `correctBarcodes` (`List<TrackedBarcode>`) — scanned and in the list.
- `wrongBarcodes` (`List<TrackedBarcode>`) — scanned but not matching the list.
- `missingBarcodes` (`List<TargetBarcode>`) — in the list, not yet scanned.
- `acceptedBarcodes` / `rejectedBarcodes` (`List<TrackedBarcode>`) — from the not-in-list action (below).
- `additionalBarcodes` (`List<Barcode>`).

## Progress bar

The progress bar appears automatically once a capture list is set. Toggle it with
`barcodeCountView.shouldShowListProgressBar` (default `true`).

## Auto-finish when the list is complete

To disable the mode automatically once every expected barcode has been scanned, set this on
`BarcodeCountSettings` **before** creating the `BarcodeCount` mode:

```kotlin
settings.disableModeWhenCaptureListCompleted = true
```

## Not-in-list action (accept / reject)

When scanning against a list, a scanned barcode that isn't on the list is marked "not in list". You can
optionally let the user **accept or reject** each such barcode via a built-in popover. Enable it on the
view:

```kotlin
val notInListAction = BarcodeCountNotInListActionSettings()
notInListAction.enabled = true   // default is false
barcodeCountView.barcodeNotInListActionSettings = notInListAction
```

Accepted barcodes then appear in `session.acceptedBarcodes` and rejected ones in
`session.rejectedBarcodes`. The button/hint text is customizable on `BarcodeCountNotInListActionSettings`
(`acceptButtonText`, `rejectButtonText`, `cancelButtonText`, `barcodeAcceptedHint`,
`barcodeRejectedHint`).

The four barcode states map as follows:

| State | Meaning |
|-------|---------|
| **Recognized** | Scanned normally and was in the expected list. |
| **Not in list** | Scanned but not in the expected list. |
| **Accepted** | Was not in the list, but the user manually added it to the accepted list. |
| **Rejected** | Was not in the list, and the user marked it as a rejected barcode. |

## Highlight colors for the list states

The **not-in-list**, **accepted**, and **rejected** barcodes each have their own highlight appearance,
customized with a `Brush` exactly like the recognized state — via the view properties `notInListBrush` /
`acceptedBrush` / `rejectedBrush`, the listener callbacks `brushForRecognizedBarcodeNotInList` /
`brushForAcceptedBarcode` / `brushForRejectedBarcode`, or the per-barcode setters. The exact APIs are
covered in `highlights.md`.

## After wiring up

Build the project. If a capture-list API doesn't resolve or a listener method isn't called, fetch the
[Advanced Configurations](https://docs.scandit.com/sdks/android/matrixscan-count/advanced/) page and the
[BarcodeCount API reference](https://docs.scandit.com/data-capture-sdk/android/barcode-capture/api.html)
to confirm the current signatures before guessing. Always include the docs link in your answer.
