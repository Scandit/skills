# MatrixScan Count iOS — Scanning Against a List

This guide covers scanning against a **known list of expected barcodes** (a manifest, a receiving
order, an inventory count, etc.). You declare which barcodes — and how many of each — are expected, and
MatrixScan Count tracks progress against that list and flags barcodes that aren't on it. It assumes the
basic integration is already in place (see `integration.md`); here we add the capture list on top.

When a capture list is set, the built-in UI automatically shows a **progress bar** (e.g. 7/10) and marks
scanned barcodes that are **not in the list** with a distinct (red) highlight.

## Build and set the expected list

Describe each expected barcode with a `TargetBarcode` (its data string and the quantity expected), wrap
them in a `BarcodeCountCaptureList` with a listener, and apply it to the mode with `setCaptureList(_:)`:

```swift
let targetBarcodes: Set<TargetBarcode> = [
    TargetBarcode(data: "0123456789012", quantity: 2),
    TargetBarcode(data: "9780201379624", quantity: 1),
]
let captureList = BarcodeCountCaptureList(listener: self, targetBarcodes: targetBarcodes)
barcodeCount.setCaptureList(captureList)
```

- `targetBarcodes` is a **`Set<TargetBarcode>`**.
- The `listener` is a `BarcodeCountCaptureListListener` (below).
- Apply it on the `BarcodeCount` mode (e.g. at the end of your `setupRecognition()`). Call
  `barcodeCount.setCaptureList(nil)` to clear it.

## Observe progress (`BarcodeCountCaptureListListener`)

Conform to `BarcodeCountCaptureListListener` to be notified as the list is filled:

```swift
extension CountViewController: BarcodeCountCaptureListListener {
    func captureList(_ captureList: BarcodeCountCaptureList,
                     didUpdate session: BarcodeCountCaptureListSession) {
        // Progress changed — read session.correctBarcodes / wrongBarcodes / missingBarcodes etc.
    }

    func captureList(_ captureList: BarcodeCountCaptureList,
                     didCompleteWith session: BarcodeCountCaptureListSession) {
        // Every expected barcode has been scanned.
    }
}
```

> **Swift naming:** the methods are `captureList(_:didUpdate:)` and `captureList(_:didCompleteWith:)` —
> the ObjC `captureList:didUpdateSession:` / `captureList:didCompleteWithSession:` are renamed for
> Swift. `didStartObservingCaptureList(_:)` / `didStopObservingCaptureList(_:)` are also available
> (optional). Update UI on the main thread.

`BarcodeCountCaptureListSession` reports the breakdown:

- `correctBarcodes` (`[TrackedBarcode]`) — scanned and in the list.
- `wrongBarcodes` (`[TrackedBarcode]`) — scanned but not matching the list.
- `missingBarcodes` (`[TargetBarcode]`) — in the list, not yet scanned.
- `acceptedBarcodes` / `rejectedBarcodes` (`[TrackedBarcode]`) — from the not-in-list action (below).
- `additionalBarcodes` (`[Barcode]`).

## Progress bar

The progress bar appears automatically once a capture list is set. Toggle it with
`barcodeCountView.shouldShowListProgressBar` (default `true`).

## Auto-finish when the list is complete

To disable the mode automatically once every expected barcode has been scanned, set this on
`BarcodeCountSettings` **before** creating the `BarcodeCount` mode:

```swift
settings.disableModeWhenCaptureListCompleted = true
```

## Not-in-list action (accept / reject)

When scanning against a list, a scanned barcode that isn't on the list is marked "not in list". You can
optionally let the user **accept or reject** each such barcode via a built-in popover. Enable it on the
view:

```swift
let notInListAction = BarcodeCountNotInListActionSettings()
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
customizable the same way as the recognized state.

> **Keep the style the app already uses — don't switch styles just to change colors.** The **Icon
> style is the default and is generally preferred**. So:
> - App on the **Icon style** (the default) → recolor each state by customizing its **icon** (e.g. its
>   background color) via the `iconForRecognizedBarcodeNotInList` / `iconForAcceptedBarcode` /
>   `iconForRejectedBarcode` delegate callbacks (returning a `BarcodeCountIcon`). **Do not switch to the
>   Dot style just to change a color.**
> - Use the **brush** properties (`notInListBrush` / `acceptedBrush` / `rejectedBrush`, or the
>   `brushForRecognizedBarcodeNotInList` / `brushForAcceptedBarcode` / `brushForRejectedBarcode`
>   callbacks) only if the app is **already** on the Dot style, or the user **explicitly** asks to
>   switch to it. A brush set on an Icon-style view has **no effect** (it silently won't render).

Both paths (icons and brushes) and the exact APIs are covered in `highlights.md`.

## After wiring up

Build the project. If a capture-list API doesn't resolve or a delegate method isn't called, fetch the
[Advanced Configurations](https://docs.scandit.com/sdks/ios/matrixscan-count/advanced/) page and the
[BarcodeCount API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api.html)
to confirm the current signatures before guessing. Always include the docs link in your answer.
