# MatrixScan Pick KMP — Highlight Configuration

MatrixScan Pick draws a **highlight** over every barcode it detects, and the look of that
highlight reflects the item's pick **state** (`BarcodePickState`: `TO_PICK`, `PICKED`, `IGNORE`,
`UNKNOWN`). This guide covers how to customize those highlights.

This assumes you already have a working MatrixScan Pick integration (`DataCaptureContext`,
`BarcodePick` mode, `BarcodePickView`, product provider, action listener). If not, start from
`integration.md` first — highlight configuration is a layer on top of that flow.

## Setting a highlight style

A style is any object implementing `BarcodePickViewHighlightStyle`. Assign it to
`BarcodePickViewSettings.highlightStyle` **before** constructing the `BarcodePickView`:

```kotlin
val viewSettings = BarcodePickViewSettings.barcodePickViewSettings()
viewSettings.highlightStyle = BarcodePickViewHighlightStyleRectangular()
// ... then BarcodePickView(context, barcodePick, viewSettings) / BarcodePickView(barcodePick, viewSettings)
```

The SDK ships five styles. Pick the simplest one that meets your needs.

## The five styles

### 1. `BarcodePickViewHighlightStyleDot`

A circular highlight. Configure a `Brush` (fill + stroke) per state, and optionally a separate
"selected" brush shown once the item is picked.

```kotlin
val style = BarcodePickViewHighlightStyleDot()
style.setBrushForState(Brush(fillColor = orange30, strokeColor = orangeColor, strokeWidth = 2f), BarcodePickState.TO_PICK)
style.setBrushForState(Brush(fillColor = green40, strokeColor = greenColor, strokeWidth = 2f), BarcodePickState.PICKED)
style.setSelectedBrushForState(Brush(fillColor = blue40, strokeColor = blueColor, strokeWidth = 2f), BarcodePickState.TO_PICK)
```

`Brush` (`com.kmp.datacapture.core.ui.style.Brush`) has a no-arg constructor and
`Brush(fillColor: Color, strokeColor: Color, strokeWidth: Float)`, all backed by
`com.kmp.datacapture.core.common.Color`. `Brush.transparent()` is a convenience for "draw
nothing". Use `brush.copy(fillColor, strokeColor, preserveAlpha)` to derive a variant.

### 2. `BarcodePickViewHighlightStyleRectangular`

A rectangle sized to the barcode. Same per-state brush API as the dot (`setBrushForState` /
`getBrushForState` / `setSelectedBrushForState` / `getSelectedBrushForState`), plus a minimum
size so small barcodes still get a tappable highlight:

```kotlin
val style = BarcodePickViewHighlightStyleRectangular()
style.minimumHighlightWidth = 40
style.minimumHighlightHeight = 40
style.setBrushForState(orangeBrush, BarcodePickState.TO_PICK)
style.setBrushForState(greenBrush, BarcodePickState.PICKED)
```

### 3. `BarcodePickViewHighlightStyleDotWithIcons`

A dot that can also show a `ScanditIcon` per state, plus an async style provider for per-barcode
styling (see "Async per-barcode styling" below).

```kotlin
val toPickIcon = ScanditIcon.builder()
    .withIcon(ScanditIconType.TO_PICK)
    .withIconColor(orangeColor)   // set an explicit color — the default can be hard to see
    .build()
val checkmarkIcon = ScanditIcon.builder().withIcon(ScanditIconType.CHECKMARK).withIconColor(greenColor).build()

val style = BarcodePickViewHighlightStyleDotWithIcons()
style.setBrushForState(orangeBrush, BarcodePickState.TO_PICK)
style.setIconForState(toPickIcon, BarcodePickState.TO_PICK)
style.setSelectedIconForState(checkmarkIcon, BarcodePickState.PICKED)
style.asyncStyleProvider = myProvider              // optional, see below
style.styleResponseCacheEnabled = true              // cache provider responses per item
```

`ScanditIcon` is built via `ScanditIcon.builder()` (`ScanditIconBuilder`), chaining `withIcon(ScanditIconType)`,
`withIconColor(Color?)`, `withBackgroundColor(Color?)`, `withBackgroundStrokeColor(Color?)`,
`withBackgroundStrokeWidth(Float)`, `withBackgroundShape(ScanditIconShape?)` (`CIRCLE`/`SQUARE`),
then `.build()`. `withBackgroundColor` only renders when paired with a `withBackgroundShape`.
`ScanditIconType` includes `TO_PICK`, `CHECKMARK`, `X_MARK`, `QUESTION_MARK`, `EXCLAMATION_MARK`,
`LOW_STOCK`, `WRONG_ITEM`, `EXPIRED_ITEM`, `INSPECT_ITEM`, `FRAGILE_ITEM`, and others.

### 4. `BarcodePickViewHighlightStyleRectangularWithIcons`

The rectangular equivalent of the dot-with-icons style: per-state brushes and icons, the async
style provider, plus `statusIconSettings` (a `BarcodePickStatusIconSettings`) to size the
status-icon badge (see "Status icons"), and a minimum highlight size.

```kotlin
val style = BarcodePickViewHighlightStyleRectangularWithIcons()
style.minimumHighlightWidth = 40
style.minimumHighlightHeight = 40
style.setIconForState(toPickIcon, BarcodePickState.TO_PICK)

val iconSettings = BarcodePickStatusIconSettings()
iconSettings.ratioToHighlightSize = 1.0f
iconSettings.minSize = 20
iconSettings.maxSize = 80
style.statusIconSettings = iconSettings
```

### 5. `BarcodePickViewHighlightStyleCustomView`

The most flexible style: supply your own platform-native view per barcode through a provider. Use
this when the built-in dot/rectangle plus icon isn't enough — e.g. a product card, a quantity
badge, a custom layout.

```kotlin
val style = BarcodePickViewHighlightStyleCustomView()
style.asyncCustomViewProvider = myCustomViewProvider
style.fitViewsToBarcode = true    // size your view to the barcode
style.minimumHighlightWidth = 40
style.minimumHighlightHeight = 40

val settings = BarcodePickStatusIconSettings()
style.statusIconSettings = settings
```

See "Custom views" below for the provider.

## Brushes and icons per state

The four non-custom styles share the same per-state API:

- `setBrushForState(brush, state)` / `getBrushForState(state)` — the brush (fill + stroke) for a state.
- `setSelectedBrushForState(brush, state)` / `getSelectedBrushForState(state)` — an optional brush
  shown once the item is picked/selected.

The two `*WithIcons` styles add:

- `setIconForState(icon, state)` / `setSelectedIconForState(icon, state)` — a `ScanditIcon`
  (`com.kmp.datacapture.core.ui.ScanditIcon`) for a state, and for the selected state.

Using the built-in icon set keeps highlights visually consistent with the rest of the SDK.

## Status icons

A **status icon** is a small badge drawn on the highlight (e.g. a quantity, a warning). It is
described by `BarcodePickStatusIconStyle`, built via one of its companion factories:

```kotlin
val lowStockIcon = ScanditIcon.builder().withIcon(ScanditIconType.LOW_STOCK).withIconColor(redColor).build()
BarcodePickStatusIconStyle.withIcon(icon = lowStockIcon, text = "Low")
BarcodePickStatusIconStyle.withColors(iconColor = redColor, iconBackgroundColor = whiteColor, text = "Pick 2")
```

> The status-icon badge renders on a light background — always set an explicit, non-white
> `withIconColor` on the `ScanditIcon` (or a non-white `iconColor` on `withColors`), or the glyph
> can be invisible.

Its size is controlled by `BarcodePickStatusIconSettings` (`ratioToHighlightSize`, `minSize`,
`maxSize`), set on the `*WithIcons` and custom-view styles via `statusIconSettings`. The status
icon itself is supplied through the async style provider (or the custom-view response) below.

## Async per-barcode styling

The `*WithIcons` styles can defer styling to a `BarcodePickViewHighlightStyleAsyncProvider` that
is asked, per barcode, what to show. `styleForRequest(request, callback)` receives a
`BarcodePickViewHighlightStyleRequest` (`itemData`, `productIdentifier`, `state`), so you can vary
the highlight by product. Invoke `callback` with a `BarcodePickViewHighlightStyleResponse`, or
`null` to fall back to the style's static configuration.

```kotlin
val provider = object : BarcodePickViewHighlightStyleAsyncProvider {
    override fun styleForRequest(
        request: BarcodePickViewHighlightStyleRequest,
        callback: (BarcodePickViewHighlightStyleResponse?) -> Unit,
    ) {
        val response = BarcodePickViewHighlightStyleResponse.withBrushAndIcon(
            brush = orangeBrush,
            icon = toPickIcon,
            statusIconStyle = BarcodePickStatusIconStyle.withColors(whiteColor, blueColor, request.productIdentifier ?: ""),
        )
        callback(response)
    }
}
style.asyncStyleProvider = provider
```

`BarcodePickViewHighlightStyleResponse` is built via one of its two companion factories:
`withBrushAndIcon(brush, icon, statusIconStyle)` (same brush/icon for all states) or
`withBrushAndSelectedIcon(brush, selectedBrush, icon, selectedIcon, statusIconStyle)` (a distinct
selected-state brush/icon). Both take `brush` and `statusIconStyle` as nullable — passing a
`null` `brush` makes the highlight shape transparent (nothing drawn for it) rather than falling
back to the style's per-state brush, so pass a real `Brush` whenever you want the highlight shape
to show. `icon` (and `selectedIcon` on the second factory) are the non-nullable-vs-nullable
`ScanditIcon` arguments — check the exact nullability in the API reference before assuming.

## Custom views

`BarcodePickViewHighlightStyleCustomView.asyncCustomViewProvider` is a
`BarcodePickViewHighlightStyleCustomViewProvider`. Implement `customViewForRequest(request, callback)`
— it receives the same `BarcodePickViewHighlightStyleRequest` and must invoke `callback` with a
`BarcodePickViewHighlightStyleCustomViewResponse(view, statusIconStyle)` wrapping your
platform-native view (`android.view.View` on Android, `UIView` on iOS — the shared type is
`NativeView`). `statusIconStyle` defaults to `null` if you don't want a badge. Return `null` from
the callback to draw nothing for a barcode.

```kotlin
val provider = object : BarcodePickViewHighlightStyleCustomViewProvider {
    override fun customViewForRequest(
        request: BarcodePickViewHighlightStyleRequest,
        callback: (BarcodePickViewHighlightStyleCustomViewResponse?) -> Unit,
    ) {
        val view = buildLabelView(request.productIdentifier ?: request.itemData) // platform-specific
        callback(BarcodePickViewHighlightStyleCustomViewResponse(view, statusIconStyle = null))
    }
}
style.asyncCustomViewProvider = provider
```

To add a status badge, pass a `BarcodePickStatusIconStyle` instead of `null` as `statusIconStyle`.

## After wiring up

If a symbol doesn't resolve, fetch the
[MatrixScan Pick Advanced guide](https://docs.scandit.com/sdks/kmp/matrixscan-pick/advanced/)
and confirm the exact signature before guessing. Always include the docs link in your answer.
