# MatrixScan Count iOS — Customizing Highlights (AR Overlays)

This guide covers customizing the augmented-reality highlights `BarcodeCountView` draws over each
barcode. It assumes the basic integration is already in place (see `integration.md`) — here we only
change how the overlays *look* and react to taps. Do not re-create the context, mode, view, camera, or
lifecycle; locate the existing `BarcodeCountView` and adjust only the highlight configuration.

> Verify every API below against the [BarcodeCountView API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api/ui/barcode-count-view.html)
> before writing code if anything is unclear — the delegate method names in particular have changed
> across SDK versions (older docs show `brushForUnrecognizedBarcode:` / `didTapUnrecognizedBarcode:`,
> which no longer exist; the current names are below).

## Style decides brushes vs. icons

`BarcodeCountView` has two styles, chosen via the `style:` initializer argument
(`BarcodeCountViewStyle.icon` — the default — or `.dot`). The style determines *which* customization
applies:

- **`.icon`** (default) — each barcode is highlighted with an **icon** (e.g. a check mark). Customize
  via the **icon** APIs (`iconForRecognizedBarcode`, `BarcodeCountView.defaultRecognizedIcon`).
- **`.dot`** — each barcode is highlighted with a **dot/shape drawn with a brush**. Customize via the
  **brush** APIs. The `brushFor…` delegate callbacks are relevant in this style.

```swift
let barcodeCountView = BarcodeCountView(frame: view.bounds,
                                        context: context,
                                        barcodeCount: barcodeCount,
                                        style: .dot)
```

`style` is read-only after construction — pick it via the initializer.

## Scope of the highlight states

`BarcodeCountView` exposes four per-state highlight slots: **recognized**, **not-in-list**,
**accepted**, and **rejected**. Only **recognized** is in play for the basic counting flow. The
**not-in-list / accepted / rejected** states only appear when you scan against an expected list — see
the receiving guide (`receiving.md`) for those. **Cluster** and **filtered** highlights belong to the
clustering and filtering features respectively and are out of scope here. This guide focuses on the
**recognized** highlight; the same patterns apply verbatim to the other states by swapping the
method/property name.

## Static per-state brush (simplest)

Set a single brush for all recognized barcodes via the view property. A `Brush` is constructed with a
fill color, a stroke color, and a stroke width:

```swift
barcodeCountView.recognizedBrush = Brush(fill: UIColor.systemGreen.withAlphaComponent(0.3),
                                         stroke: .systemGreen,
                                         strokeWidth: 2)
```

> **Swift naming:** the `Brush` initializer is `Brush(fill:stroke:strokeWidth:)` — note `fill:` /
> `stroke:`, **not** `fillColor:` / `strokeColor:` (the ObjC `initWithFillColor:strokeColor:strokeWidth:`
> is renamed for Swift). Its read-only properties are `fillColor` / `strokeColor` / `strokeWidth`.

- The companion properties are `notInListBrush`, `acceptedBrush`, `rejectedBrush` (see `receiving.md`).
- To start from the SDK defaults, the class properties `BarcodeCountView.defaultRecognizedBrush`
  (and `defaultNotInListBrush` / `defaultAcceptedBrush` / `defaultRejectedBrush`) return the
  recommended brushes.
- `Brush.transparentBrush` draws nothing — use it to make a highlight invisible.

## Dynamic per-barcode brush (delegate)

To decide the brush per individual barcode (e.g. color by payload), set the view's `delegate`
(`BarcodeCountViewDelegate`) and implement `barcodeCountView(_:brushForRecognizedBarcode:)`. It is
called for each recognized barcode and returns the brush to draw (return `nil` to use the default).
These `brushFor…` callbacks apply to the **Dot** style.

```swift
barcodeCountView.delegate = self

extension CountViewController: BarcodeCountViewDelegate {
    func barcodeCountView(_ view: BarcodeCountView,
                          brushForRecognizedBarcode trackedBarcode: TrackedBarcode) -> Brush? {
        // e.g. highlight a specific SKU differently
        if trackedBarcode.barcode.data == "1234567890" {
            return Brush(fill: UIColor.systemOrange.withAlphaComponent(0.3),
                         stroke: .systemOrange, strokeWidth: 2)
        }
        return BarcodeCountView.defaultRecognizedBrush
    }
}
```

The full set of `BarcodeCountViewDelegate` brush callbacks is
`brushForRecognizedBarcode`, `brushForRecognizedBarcodeNotInList`, `brushForAcceptedBarcode`,
`brushForRejectedBarcode` (and `brushForCluster:`). `TrackedBarcode` (from the batch module) exposes
`.barcode`, `.identifier`, and `.location`.

> `BarcodeCountViewDelegate` is main-actor (`NS_SWIFT_UI_ACTOR`) — its callbacks arrive on the main
> queue and can touch UIKit directly.

## Icons (Icon style)

In the `.icon` style, the highlight is a `BarcodeCountIcon`. Set a single icon for all recognized
barcodes by returning one from the delegate's `iconForRecognizedBarcode`, or read the SDK defaults via
the class properties `BarcodeCountView.defaultRecognizedIcon` (+ `defaultNotInListIcon` /
`defaultAcceptedIcon` / `defaultRejectedIcon`).

A `BarcodeCountIcon` wraps a `ScanditIcon`, which is built with `ScanditIconBuilder`:

```swift
let scanditIcon = ScanditIconBuilder()
    .withIconColor(.white)
    .withBackgroundColor(.systemGreen)
    .withBackgroundShape(.circle)
    .build()
// accessibleIcon is an optional larger / high-contrast variant — pass nil to reuse the default.
let icon = BarcodeCountIcon(defaultIcon: scanditIcon, accessibleIcon: nil)

extension CountViewController: BarcodeCountViewDelegate {
    func barcodeCountView(_ view: BarcodeCountView,
                          iconForRecognizedBarcode trackedBarcode: TrackedBarcode) -> BarcodeCountIcon? {
        return icon
    }
}
```

`ScanditIconBuilder` also offers `.withIcon(_:)` (a `ScanditIconType` — consult the
[ScanditIcon API reference](https://docs.scandit.com/data-capture-sdk/ios/core/api.html) for the
available icon types rather than guessing), `.withBackgroundStrokeColor(_:)`,
`.withBackgroundStrokeWidth(_:)`, and `.withBackgroundShape(_:)`. `BarcodeCountIcon(defaultIcon:)` can
also take an `accessibleIcon` variant for larger/high-contrast rendering.

The icon callbacks mirror the brush ones: `iconForRecognizedBarcode`,
`iconForRecognizedBarcodeNotInList`, `iconForAcceptedBarcode`, `iconForRejectedBarcode`.

## Setting a brush/icon for one specific tracked barcode

When you already hold a `TrackedBarcode` (e.g. inside a delegate callback) and want to override its
highlight imperatively, use the per-barcode setters on the view:

```swift
barcodeCountView.setBrush(myBrush, forRecognizedBarcode: trackedBarcode)
barcodeCountView.setIcon(myIcon, forRecognizedBarcode: trackedBarcode)
```

The `forRecognizedBarcodeNotInList:` / `forAcceptedBarcode:` / `forRejectedBarcode:` variants exist too.
Passing `nil` clears the override.

## Reacting to taps

Reacting to taps on a highlight uses the same `BarcodeCountViewDelegate` — the `didTap…` callbacks
(`didTapRecognizedBarcode`, `didTapRecognizedBarcodeNotInList`, `didTapAcceptedBarcode`,
`didTapRejectedBarcode`, `didTapFilteredBarcode`, `didTapCluster`). Tap handling is covered in the base
integration guide (`integration.md`, "Reacting to barcode taps"); the brush/icon callbacks above and
those tap callbacks live on the same `delegate`.

> **Common mistake — do NOT use `brushForUnrecognizedBarcode:` / `didTapUnrecognizedBarcode:`.** Those
> appear in older documentation but are not part of the current `BarcodeCountViewDelegate`. The
> "not recognized as part of the list" state is **`…RecognizedBarcodeNotInList`**, and there are
> distinct `…AcceptedBarcode` / `…RejectedBarcode` / `…FilteredBarcode` / `…Cluster` callbacks.

## Clear-screen button

To let the user clear all AR overlays while keeping the scanned list, enable the built-in button:

```swift
barcodeCountView.shouldShowClearHighlightsButton = true
```

(To clear highlights programmatically, call `barcodeCountView.clearHighlights()`.)

## After wiring up

Build the project. If a delegate method isn't being called or a name doesn't resolve, fetch the
[BarcodeCountView API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api/ui/barcode-count-view.html)
to confirm the exact current selector before guessing. Always include the docs link in your answer.
