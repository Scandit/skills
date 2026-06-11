# MatrixScan Count iOS — Status Mode

Status mode lets you annotate each counted barcode with a **status** — a per-barcode status icon. The
statuses are shown automatically as barcodes are scanned (the recommended setup), or optionally only when
the user taps the status-mode button. You decide each barcode's status by implementing a **status
provider**, which the SDK calls with the current barcodes and which hands back a status (and icon) for
each. This guide assumes the basic integration is already in place (see `integration.md`); here we only
add status mode.

> Verify any status-mode symbol against the
> [BarcodeCount API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api.html)
> before guessing.

## Register a status provider

Conform to `BarcodeCountStatusProvider` and register it on the view. The recommended setup is to show the
statuses automatically as barcodes are scanned with `shouldShowStatusIconsOnScan = true`:

```swift
barcodeCountView.setStatusProvider(self)
barcodeCountView.shouldShowStatusIconsOnScan = true   // statuses appear automatically on scan (recommended)
```

See **Showing the statuses** below for the button-only alternative.

## Provide a status per barcode

The SDK calls your provider whenever it needs statuses, handing you the current barcodes and a callback.
Build one `BarcodeCountStatusItem` per barcode, wrap them in a result, and deliver it via the callback.
The work can be **asynchronous** — e.g. look the statuses up in a backend and call `onStatusReady` when
the response arrives:

```swift
extension CountViewController: BarcodeCountStatusProvider {
    func statusRequested(for barcodes: [TrackedBarcode],
                         callback: BarcodeCountStatusProviderCallback) {
        // Build a status item per barcode. The modern initializer takes a ScanditIcon you build
        // yourself (see highlights.md for ScanditIconBuilder); pass nil if the barcode has no status.
        let statusItems = barcodes.map { barcode -> BarcodeCountStatusItem in
            let icon = ScanditIconBuilder()
                .withIcon(.exclamationMark)
                .withIconColor(.white)
                .withBackgroundColor(.systemRed)
                .withBackgroundShape(.circle)   // a background color only shows with a shape set
                .build()
            return BarcodeCountStatusItem(barcode: barcode, icon: icon)
        }

        let result = BarcodeCountStatusSuccessResult(statusList: statusItems,
                                                     statusModeEnabledMessage: "Reviewing items",
                                                     statusModeDisabledMessage: "Status mode off")
        callback.onStatusReady(result)
    }
}
```

- `statusRequested(for:callback:)` is the one required method. Deliver your result **exactly once** per
  call via `callback.onStatusReady(_:)` — synchronously or after async work.
- **Return an item for every barcode you want to control.** To display **nothing** for a barcode, include
  it in the status list with a **`nil` icon** — it's then treated as having no status and no indicator is
  shown. A barcode you **leave out** of the list entirely is instead marked as *missing its status* and
  gets the SDK's fallback indicator — so omitting is not the same as a `nil` icon.
- `BarcodeCountStatusItem(barcode:icon:)` is the current initializer: it takes the `TrackedBarcode` and a
  `ScanditIcon?` (build it with `ScanditIconBuilder` — see `highlights.md`; pass `nil` to show nothing for
  that barcode).
  The older `BarcodeCountStatusItem(barcode:status:)` initializer (which takes a fixed `BarcodeCountStatus`
  enum value — `.expired`, `.fragile`, `.lowStock`, `.qualityCheck`, `.expiringSoon`, `.notAvailable`,
  `.wrong`, `.none`) is **deprecated** in favor of the customizable icon initializer; prefer the icon form.

## Result types

Resolving statuses is meant to be **asynchronous** — you typically fetch them from a backend or some other
slow source. Whatever the outcome of that lookup, you tell Barcode Count about it by delivering one of
three result types to `callback.onStatusReady(_:)`:

- `BarcodeCountStatusSuccessResult(statusList:statusModeEnabledMessage:statusModeDisabledMessage:)` —
  everything went fine; you resolved statuses for the barcodes. The two messages are shown when status
  mode is toggled on / off (pass `nil` to omit).
- `BarcodeCountStatusErrorResult(statusList:errorMessage:statusModeDisabledMessage:)` — something went
  wrong, but you still got **at least some** statuses; show those and surface the error message.
- `BarcodeCountStatusAbortResult(errorMessage:)` — abort: you couldn't get any statuses (the lookup
  failed entirely), or you don't want to display any for some other reason.

## Showing the statuses

There are two ways to present the statuses; pick one.

**Recommended — show them automatically on scan.** Each barcode's status icon appears as soon as it's
counted, with no extra tap:

```swift
barcodeCountView.shouldShowStatusIconsOnScan = true
```

**Alternative — show them only when the user taps the status-mode button.** A button in the UI toggles
status mode, where the normal highlights are replaced by the status icons:

```swift
barcodeCountView.shouldShowStatusModeButton = true   // show the button
// Just don't enable shouldShowStatusIconsOnScan — it defaults to false, which is what the button needs.
```

The two are mutually exclusive: if `shouldShowStatusIconsOnScan` is `true`, the status-mode button is
hidden regardless of `shouldShowStatusModeButton`. Since it's `false` by default, you usually only set
`shouldShowStatusModeButton`.

## Status icons with clustering

If clustering (see `clustering.md`) is enabled together with status icons, the statuses are organized on
the **cluster** highlight rather than per individual barcode:

- A cluster shows the status icons of its members arranged in a **grid** inside the cluster highlight.
- **Duplicate** statuses within a cluster are shown only once.
- The default no-status marker that individual barcodes get is **not** shown on a cluster.
- While barcodes are clustered, the SDK can't indicate which status icon belongs to which individual
  barcode — the user has to **uncluster** them to tell the statuses apart. In dedicated status mode
  (button), manual cluster gestures are disabled.

## After wiring up

Build the project. If a status-mode API doesn't resolve or the provider isn't called, fetch the
[Advanced Configurations](https://docs.scandit.com/sdks/ios/matrixscan-count/advanced/) page and the
[BarcodeCount API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api.html)
to confirm the current signatures before guessing. Always include the docs link in your answer.
