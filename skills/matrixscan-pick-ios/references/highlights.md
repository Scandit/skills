# MatrixScan Pick iOS — Highlight Configuration

MatrixScan Pick draws a **highlight** over every barcode it detects, and the look of that highlight
reflects the item's pick **state**. This guide covers how to customize those highlights.

This assumes you already have a working MatrixScan Pick integration (`DataCaptureContext`,
`BarcodePick` mode, `BarcodePickView`, product provider, action listener). If not, start from
`integration.md` first — highlight configuration is a layer on top of that flow, not a replacement
for it.

## Pick states

Every highlight is rendered for one of four `BarcodePickState` values, and most customization is
keyed by state:

- `.toPick` — the item should be picked (it's in the list and not yet picked).
- `.picked` — the item has been picked.
- `.unknown` — the item has not been mapped to a product (i.e. not-in-list).
- `.ignore` — the item should be ignored in this session.

## Setting a highlight style

A style is any object conforming to `BarcodePickViewHighlightStyle`. Assign it to
`BarcodePickViewSettings.highlightStyle` **before** constructing the `BarcodePickView`:

```swift
let viewSettings = BarcodePickViewSettings()
viewSettings.highlightStyle = BarcodePickViewHighlightStyleRectangular()
// ... then BarcodePickView(frame:context:barcodePick:settings: viewSettings)
```

The SDK ships five styles. Pick the simplest one that meets your needs.

## The five styles

### 1. `BarcodePickViewHighlightStyleDot`

A circular highlight. Configure a `Brush` (fill + stroke) per state, and optionally a separate
"selected" brush shown once the item is picked.

```swift
let style = BarcodePickViewHighlightStyleDot()
style.setBrush(Brush(fill: UIColor.orange.withAlphaComponent(0.3), stroke: .orange, strokeWidth: 2), for: .toPick)
style.setBrush(Brush(fill: UIColor.green.withAlphaComponent(0.4), stroke: .green, strokeWidth: 2), for: .picked)
style.setSelectedBrush(Brush(fill: UIColor.blue.withAlphaComponent(0.4), stroke: .blue, strokeWidth: 2), for: .toPick)
```

### 2. `BarcodePickViewHighlightStyleRectangular`

A rectangle sized to the barcode. Same per-state brush API as the dot, plus a minimum size so small
barcodes still get a tappable highlight.

```swift
let style = BarcodePickViewHighlightStyleRectangular()
style.minimumHighlightHeight = 40
style.minimumHighlightWidth = 40
style.setBrush(Brush(fill: UIColor.orange.withAlphaComponent(0.3), stroke: .orange, strokeWidth: 2), for: .toPick)
style.setBrush(Brush(fill: UIColor.green.withAlphaComponent(0.4), stroke: .green, strokeWidth: 2), for: .picked)
```

### 3. `BarcodePickViewHighlightStyleDotWithIcons`

A dot that can also show an **icon** per state, and supports an async **delegate** for per-barcode
styling (see "Async per-barcode styling" below). Prefer a built-in `ScanditIcon` — it matches the
rest of the SDK's visual language and scales correctly; a `UIImage` is also accepted if you need a
custom asset.

Give the `ScanditIcon` a `withIconColor` — the default glyph color can be invisible (e.g. white on a
light highlight). Note its `withBackgroundColor` only renders if you also set a `withBackgroundShape`;
without a shape, only the glyph color matters, so pick one that contrasts with the highlight.

```swift
let style = BarcodePickViewHighlightStyleDotWithIcons()
style.setBrush(Brush(fill: UIColor.orange.withAlphaComponent(0.3), stroke: .orange, strokeWidth: 2), for: .toPick)
style.setScanditIcon(
    ScanditIconBuilder().withIcon(.toPick).withIconColor(.orange).build(),
    for: .toPick)
style.setSelectedScanditIcon(
    ScanditIconBuilder().withIcon(.checkmark).withIconColor(.systemGreen).build(),
    for: .picked)
style.delegate = self                  // optional, see "Async per-barcode styling"
style.styleResponseCacheEnabled = true // cache delegate responses per item
```

### 4. `BarcodePickViewHighlightStyleRectangularWithIcons`

The rectangular equivalent of the dot-with-icons style: per-state brushes and icons, the async
delegate, plus `statusIconSettings` to size the status-icon badge (see "Status icons") and a minimum
highlight size.

```swift
let style = BarcodePickViewHighlightStyleRectangularWithIcons()
style.minimumHighlightHeight = 40
style.minimumHighlightWidth = 40
style.setScanditIcon(
    ScanditIconBuilder().withIcon(.toPick).withIconColor(.orange).build(),
    for: .toPick)

let iconSettings = BarcodePickStatusIconSettings()
iconSettings.ratioToHighlightSize = 1.0
iconSettings.minSize = 20
iconSettings.maxSize = 80
style.statusIconSettings = iconSettings
```

### 5. `BarcodePickViewHighlightStyleCustomView`

The most flexible style: supply your own `UIView` per barcode through a delegate. Use this when the
built-in dot/rectangle plus icon isn't enough — e.g. a product card, a quantity badge, a custom
layout.

```swift
let style = BarcodePickViewHighlightStyleCustomView()
style.delegate = self
style.fitViewsToBarcode = true   // size your view to the barcode
style.minimumHighlightHeight = 40
style.minimumHighlightWidth = 40
```

See "Custom views" below for the delegate.

## Brushes and icons per state

The four non-custom styles share the same per-state API:

- `setBrush(_:for:)` / `brush(for:)` — the brush (fill + stroke) for a state.
- `setSelectedBrush(_:for:)` / `selectedBrush(for:)` — an optional brush shown once the item is
  picked / selected.

The two `*WithIcons` styles add:

- `setScanditIcon(_:for:)` / `setSelectedScanditIcon(_:for:)` — a built-in `ScanditIcon` for a state,
  and the icon once selected. **Prefer these.**
- `setIcon(_:for:)` / `setSelectedIcon(_:for:)` — the `UIImage` equivalents, if you need a custom asset.

A `Brush` is `Brush(fill:stroke:strokeWidth:)`. A `ScanditIcon` is built with `ScanditIconBuilder()`:

```swift
ScanditIconBuilder()
    .withIcon(.lowStock)            // .toPick, .checkmark, .xmark, .questionMark,
                                    // .exclamationMark, .wrongItem, .lowStock, and more
    .withIconColor(.systemRed)      // the glyph color — set this, the default can be invisible
    .build()
```

Using the built-in set keeps highlights visually consistent with the rest of the SDK. **Always set
`withIconColor` to something that contrasts with the highlight** — the default glyph color can render
invisibly (e.g. white on white). `withBackgroundColor` only takes effect when paired with a
`withBackgroundShape`; if you don't set a shape, the background color is ignored and only the glyph
color shows.

## Status icons

A **status icon** is a small badge drawn on the highlight (e.g. a quantity, a warning). It is
described by `BarcodePickStatusIconStyle`, constructed with one of:

```swift
BarcodePickStatusIconStyle(iconColor: .white, iconBackgroundColor: .systemBlue, text: "Pick 2")
BarcodePickStatusIconStyle(scanditIcon: ScanditIconBuilder().withIcon(.lowStock).withIconColor(.systemRed).build(), text: "Low")
BarcodePickStatusIconStyle(icon: someUIImage, text: "Check") // UIImage variant, if needed
```

Its size is controlled by `BarcodePickStatusIconSettings` (`ratioToHighlightSize`, `minSize`,
`maxSize`), set on the `*WithIcons` and custom-view styles via `statusIconSettings`. The status icon
itself is supplied through one of the async delegates below (or the custom-view response).

> **Don't use a white icon color for a status-icon `ScanditIcon`.** The status-icon badge is drawn on
> a white background, so a white glyph (the `ScanditIcon` default — always set `withIconColor`) is
> invisible. Use a dark or saturated color, e.g. `withIconColor(.systemRed)`. (For the
> `iconColor:iconBackgroundColor:text:` variant, set a colored `iconBackgroundColor` so a white
> `iconColor` still shows.)

## Async per-barcode styling

The `*WithIcons` styles can defer styling to a delegate that is asked, per barcode, what to show. The
request carries the item's `itemData`, `productIdentifier`, and `state`, so you can vary the highlight
by product (e.g. fetch a per-SKU color or a remaining-quantity badge). Return `nil` to fall back to
the style's static configuration.

```swift
extension ViewController: BarcodePickViewHighlightStyleDelegate {
    func style(for request: BarcodePickHighlightStyleRequest,
               completionHandler: @escaping (BarcodePickViewHighlightStyleResponse?) -> Void) {
        let response = BarcodePickViewHighlightStyleResponse(
            brush: Brush(fill: UIColor.orange.withAlphaComponent(0.3), stroke: .orange, strokeWidth: 2),
            scanditIcon: ScanditIconBuilder().withIcon(.toPick).withIconColor(.orange).build(),
            statusIconStyle: BarcodePickStatusIconStyle(iconColor: .white,
                                                        iconBackgroundColor: .systemBlue,
                                                        text: request.productIdentifier ?? "")
        )
        completionHandler(response)
    }
}
```

The callback is async (it hands you a `completionHandler`), so a backend lookup is fine. It is **not**
main-actor annotated — dispatch to the main queue before touching UIKit. `BarcodePickViewHighlightStyleResponse`
has initializers for `brush:scanditIcon:` and `brush:icon:`, plus their selected-state variants
(`brush:selectedBrush:scanditIcon:selectedScanditIcon:` and `brush:selectedBrush:icon:selectedIcon:`).
**Every one of these ends in a required `statusIconStyle:` argument — pass `nil` for no badge, but you
must pass it; it can't be omitted.**

> A `nil` `brush` makes the highlight shape **transparent** (nothing drawn for it); a `nil` icon just
> means no icon is shown (it does not affect the shape). So if you return a `nil` brush but supply a
> `statusIconStyle`, you'll see only the status badge floating over the barcode with no highlight
> behind it. Provide a visible brush if you want the highlight shape to show alongside the badge.

## Custom views

`BarcodePickViewHighlightStyleCustomView` asks its delegate for a `UIView` per barcode. The request
carries the same `itemData` / `productIdentifier` / `state`, and you return a
`BarcodePickHighlightCustomViewResponse` wrapping your view. Its initializer is
`init(view:statusIconStyle:)` — **`statusIconStyle:` is a required argument; pass `nil` if you don't
want a badge** (you can't omit it). Pass a `BarcodePickStatusIconStyle` to add one (sized by the
style's `statusIconSettings`). Return `nil` from the callback to draw nothing for a barcode.

```swift
extension ViewController: BarcodePickViewHighlightStyleCustomViewDelegate {
    func customView(for request: BarcodePickHighlightStyleRequest,
                    completionHandler: @escaping (BarcodePickHighlightCustomViewResponse?) -> Void) {
        let label = UILabel()
        label.text = request.productIdentifier ?? request.itemData
        label.sizeToFit()

        // No status badge — but statusIconStyle is still a required argument, so pass nil.
        completionHandler(BarcodePickHighlightCustomViewResponse(view: label, statusIconStyle: nil))
    }
}
```

To add a status badge, pass a `BarcodePickStatusIconStyle` instead of `nil`:

```swift
let statusIcon = BarcodePickStatusIconStyle(
    scanditIcon: ScanditIconBuilder().withIcon(.lowStock).withIconColor(.systemRed).build(),
    text: request.productIdentifier ?? "")
completionHandler(BarcodePickHighlightCustomViewResponse(view: label, statusIconStyle: statusIcon))
```

> **If the status icon looks cut off**, check whether your custom view clips its subviews. The status
> icon is positioned partially outside the view's bounds, so setting `layer.masksToBounds = true` (or
> `clipsToBounds = true`) on the view you return will clip the badge. Leave clipping off, or inset your
> content, if you need the full badge visible.

Same threading caveat — the callback is not main-actor annotated, so build your view and call the
completion handler on the main queue if it touches UIKit state beyond simple construction.

## After wiring up

Build the project. If a symbol doesn't resolve, fetch the
[MatrixScan Pick API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api.html)
and confirm the exact signature before guessing. Always include the docs link in your answer.
