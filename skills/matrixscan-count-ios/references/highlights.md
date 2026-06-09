# MatrixScan Count iOS — Customizing Highlights (AR Overlays)

This guide covers customizing the look of the augmented-reality highlights `BarcodeCountView` draws
over each barcode. It assumes the basic integration is already in place (see `integration.md`) — here
we only change how the overlays *look*. Do not re-create the context, mode, view, camera, or lifecycle;
locate the existing `BarcodeCountView` and adjust only the highlight configuration.

> If anything is unclear, verify against the
> [BarcodeCountView API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api/ui/barcode-count-view.html)
> before writing code.

`BarcodeCountView` has two highlight styles, chosen via the `style:` initializer argument
(`BarcodeCountViewStyle.icon` — the default — or `.dot`). `style` is read-only after construction, so
pick it when creating the view:

```swift
let barcodeCountView = BarcodeCountView(frame: view.bounds,
                                        context: context,
                                        barcodeCount: barcodeCount,
                                        style: .dot)
```

## Icon style (default)

The default style. Each recognized barcode is marked with a dot carrying an icon (e.g. a check mark),
using Scandit's built-in icons. This is what you get from the basic integration when no `style:` is
passed.

Per-barcode customization of the icon appearance is **not available in the current released SDK**. If
you need to customize the highlight color/appearance today, use the **Dot style** below.

## Dot style

Set `style: .dot` in the initializer (above). Each recognized barcode is marked with a colored dot,
and you customize the color with a `Brush`. The brush APIs apply to the Dot style.

### One brush for all recognized barcodes

Set the brush on the view. A `Brush` is constructed with a fill color, a stroke color, and a stroke
width:

```swift
barcodeCountView.recognizedBrush = Brush(fill: UIColor.systemGreen.withAlphaComponent(0.3),
                                         stroke: .systemGreen,
                                         strokeWidth: 2)
```

> **Swift naming:** the initializer is `Brush(fill:stroke:strokeWidth:)` — note `fill:` / `stroke:`,
> **not** `fillColor:` / `strokeColor:` (the ObjC `initWithFillColor:strokeColor:strokeWidth:` is
> renamed for Swift). Its read-only properties are `fillColor` / `strokeColor` / `strokeWidth`.

To start from the SDK's recommended brush, read the class property
`BarcodeCountView.defaultRecognizedBrush`.

### A brush per individual barcode (delegate)

To decide the brush per barcode (e.g. color by payload), set the view's `delegate`
(`BarcodeCountViewDelegate`) and implement `barcodeCountView(_:brushForRecognizedBarcode:)`. It is
called for each recognized barcode and returns the brush to draw (return `nil` to use the default):

```swift
barcodeCountView.delegate = self

extension CountViewController: BarcodeCountViewDelegate {
    func barcodeCountView(_ view: BarcodeCountView,
                          brushForRecognizedBarcode trackedBarcode: TrackedBarcode) -> Brush? {
        if trackedBarcode.barcode.data == "1234567890" {
            return Brush(fill: UIColor.systemOrange.withAlphaComponent(0.3),
                         stroke: .systemOrange, strokeWidth: 2)
        }
        return BarcodeCountView.defaultRecognizedBrush
    }
}
```

`TrackedBarcode` (from the batch module) exposes `.barcode`, `.identifier`, and `.location`. Note that
`barcode.data` is **optional** (`String?`) — unwrap it before using it (e.g.
`guard let data = trackedBarcode.barcode.data else { return nil }`), especially before parsing it
(`Int(data)`).

> `BarcodeCountViewDelegate` is main-actor (`NS_SWIFT_UI_ACTOR`) — its callbacks arrive on the main
> queue and can touch UIKit directly.

### Overriding the brush for one specific tracked barcode

When you already hold a `TrackedBarcode` and want to override its brush imperatively, use the
per-barcode setter on the view (pass `nil` to clear the override):

```swift
barcodeCountView.setBrush(myBrush, forRecognizedBarcode: trackedBarcode)
```

### Other highlight states

`recognizedBrush` / `brushForRecognizedBarcode` cover the basic counting flow. The other states are
customized the **same way** — static view properties `notInListBrush`, `acceptedBrush`, `rejectedBrush`,
or the delegate callbacks `brushForRecognizedBarcodeNotInList`, `brushForAcceptedBarcode`,
`brushForRejectedBarcode`. These states only become *visible* when scanning against a list, so their
behavior (when each one shows) is covered in the list-scanning guide (`list-scanning.md`); the brushes
themselves are set exactly like `recognizedBrush` above.

## After wiring up

Build the project. If a delegate method isn't being called or a name doesn't resolve, fetch the
[BarcodeCountView API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api/ui/barcode-count-view.html)
to confirm the exact current selector before guessing. Always include the docs link in your answer.
