# MatrixScan Count iOS — Customizing Highlights (AR Overlays)

This guide covers customizing the look of the augmented-reality highlights `BarcodeCountView` draws
over each barcode. It assumes the basic integration is already in place (see `integration.md`) — here
we only change how the overlays *look*. Do not re-create the context, mode, view, camera, or lifecycle;
locate the existing `BarcodeCountView` and adjust only the highlight configuration.

> If anything is unclear, verify against the
> [BarcodeCountView API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api/ui/barcode-count-view.html)
> before writing code.

> **Keep the style the app already uses — don't switch styles just to change colors.** When the request
> is about *appearance* (colors, per-barcode looks), customize *within* the style the integration
> already has. The **Icon style is the default and is generally preferred** — it's the modern look and
> (in current SDKs) is fully customizable per barcode, including its **background color**. So:
> - App on the **Icon style** (the default) → recolor by customizing the **icon** (e.g. its background
>   color) via `iconForRecognizedBarcode`. This covers "make recognized barcodes green", "color each
>   barcode by its data", etc. **Do not switch to the Dot style just to change a color.**
> - Use a **`Brush`** only if the app is **already** on the Dot style, or the user **explicitly** asks
>   to switch to it. A brush set on an Icon-style view has **no effect** (it silently won't render).
>
> Older code/examples customized colors only with brushes (before per-barcode icon customization
> existed) — prefer the icon path on the default Icon style.

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

### Customizing the icon per barcode

Set the view's `delegate` (`BarcodeCountViewDelegate`) and return a `BarcodeCountIcon` from
`iconForRecognizedBarcode` for each barcode (return `nil` to keep the default). Unlike brushes, there is
**no per-state icon property** (no `recognizedIcon` analogous to `recognizedBrush`) — to use one icon
for *all* recognized barcodes, just return the same `BarcodeCountIcon` for every barcode from this
callback. A `BarcodeCountIcon` wraps a `ScanditIcon`, built with `ScanditIconBuilder`:

```swift
barcodeCountView.delegate = self

extension CountViewController: BarcodeCountViewDelegate {
    func barcodeCountView(_ view: BarcodeCountView,
                          iconForRecognizedBarcode trackedBarcode: TrackedBarcode) -> BarcodeCountIcon? {
        let icon = ScanditIconBuilder()
            .withIconColor(.white)
            .withBackgroundColor(.systemGreen)
            .withBackgroundShape(.circle)
            .build()
        return BarcodeCountIcon(defaultIcon: icon, accessibleIcon: nil)
    }
}
```

- `BarcodeCountIcon(defaultIcon:accessibleIcon:)` takes a default icon and an optional **accessible**
  variant; the SDK picks between them based on the user's accessibility settings (pass `nil` to reuse
  the default).
- `ScanditIconBuilder` chains `.withIcon(_:)` (a built-in `ScanditIconType`), `.withIconColor(_:)`,
  `.withBackgroundColor(_:)`, `.withBackgroundStrokeColor(_:)`, `.withBackgroundStrokeWidth(_:)`, and
  `.withBackgroundShape(_:)` (`.circle` / `.square`), then `.build()`. It is a fixed icon set, **not** a
  free-form image API. The `ScanditIconType` values (use these exact names — do not guess, e.g. it is
  `.checkmark`, not `.check`): `.checkmark`, `.xMark`, `.questionMark`, `.exclamationMark`, `.toPick`,
  `.wrongItem`, `.lowStock`, `.inspectItem`, `.expiredItem`, `.fragileItem`, `.starFilled`,
  `.starHalfFilled`, `.starOutlined`, `.arrowRight`, `.arrowLeft`, `.arrowUp`, `.arrowDown`,
  `.chevronRight`, `.chevronLeft`, `.chevronUp`, `.chevronDown`, `.delete`, `.print`, `.slash`, `.plus`,
  `.minus`. (Omit `.withIcon` to keep the default icon and just recolor the background.)
- The class properties `BarcodeCountView.defaultRecognizedIcon` (and `defaultNotInListIcon` /
  `defaultAcceptedIcon` / `defaultRejectedIcon`) return the SDK defaults, so you can override only some
  states.
- To override one specific tracked barcode imperatively: `barcodeCountView.setIcon(_:forRecognizedBarcode:)`.

The icon callbacks mirror the brush ones: `iconForRecognizedBarcode`, `iconForRecognizedBarcodeNotInList`,
`iconForAcceptedBarcode`, `iconForRejectedBarcode` — the not-in-list / accepted / rejected ones only
appear when scanning against a list (see `list-scanning.md`).

To recolor the highlight as a plain colored **dot** instead of an icon, use the Dot style below.

## Dot style

Set `style: .dot` in the initializer (above). Each recognized barcode is marked with a colored dot,
and you customize the color with a `Brush`. The brush APIs apply to the Dot style.

### One brush for all barcodes in the same state

Each state has its own view-level brush property (`recognizedBrush`, and the `notInListBrush` /
`acceptedBrush` / `rejectedBrush` covered below) — setting one applies that brush to every barcode in
that state. A `Brush` is constructed with a fill color, a stroke color, and a stroke width:

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

## Status mode (per-barcode status overlay)

Status mode is a different kind of overlay: instead of the normal recognized highlights, it shows a
**status indicator per barcode** (e.g. expired, low-stock, quality-check) so the user gets richer
handling information. You supply the status for each scanned barcode through a
`BarcodeCountStatusProvider`, which the view queries.

Wire it up in three parts: enable the overlay on the view, set the provider, and implement the provider
to return a status per barcode.

```swift
// On the BarcodeCountView, after the basic integration:
barcodeCountView.shouldShowStatusIconsOnScan = true   // load status icons right after scanning
barcodeCountView.setStatusProvider(self)
```

```swift
extension CountViewController: BarcodeCountStatusProvider {
    func statusRequested(for barcodes: [TrackedBarcode],
                         callback: BarcodeCountStatusProviderCallback) {
        // Build a BarcodeCountStatusItem per barcode (look up your own data here).
        let items: [BarcodeCountStatusItem] = barcodes.map { tracked in
            // BarcodeCountStatus cases: .none, .notAvailable, .expired, .fragile,
            // .qualityCheck, .lowStock, .wrong, .expiringSoon
            BarcodeCountStatusItem(barcode: tracked, status: .expired)
        }
        let result = BarcodeCountStatusSuccessResult(statusList: items,
                                                     statusModeEnabledMessage: "Status on.",
                                                     statusModeDisabledMessage: "Status off.")
        callback.onStatusReady(result)
    }
}
```

- `shouldShowStatusIconsOnScan = true` is the recommended approach (status icons load immediately after
  a scan). Alternatively, set `barcodeCountView.shouldShowStatusModeButton = true` to surface a button
  the user taps to toggle status mode on demand — but `shouldShowStatusIconsOnScan`, when enabled,
  takes precedence and the button is hidden.
- The provider protocol is `BarcodeCountStatusProvider`; its one method is
  `statusRequested(for:callback:)`. It is invoked on an internal thread, and you may answer
  asynchronously — call `callback.onStatusReady(_:)` once the statuses are ready (e.g. after a network
  fetch).
- Each `BarcodeCountStatusItem` is built with `BarcodeCountStatusItem(barcode:status:)` where `status`
  is a `BarcodeCountStatus` case. The success result is `BarcodeCountStatusSuccessResult(statusList:
  statusModeEnabledMessage:statusModeDisabledMessage:)` (the error / abort variants are
  `BarcodeCountStatusErrorResult` / `BarcodeCountStatusAbortResult`).
- `BarcodeCountStatus` has exactly these cases — use one of these and do **not** invent others:
  `.none`, `.notAvailable`, `.expired`, `.fragile`, `.qualityCheck`, `.lowStock`, `.wrong`,
  `.expiringSoon`. (For example, there is no `.recalled`, `.damaged`, or `.outOfStock` case.)

## After wiring up

Build the project. If a delegate method isn't being called or a name doesn't resolve, fetch the
[BarcodeCountView API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api/ui/barcode-count-view.html)
to confirm the exact current selector before guessing. Always include the docs link in your answer.
