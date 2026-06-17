# MatrixScan Count Android — Customizing Highlights (AR Overlays)

This guide covers customizing the look of the augmented-reality highlights `BarcodeCountView` draws
over each barcode. It assumes the basic integration is already in place (see `integration.md`) — here
we only change how the overlays *look*. Do not re-create the context, mode, view, camera, or lifecycle;
locate the existing `BarcodeCountView` and adjust only the highlight configuration.

> If anything is unclear, verify against the
> [BarcodeCountView API reference](https://docs.scandit.com/data-capture-sdk/android/barcode-capture/api/ui/barcode-count-view.html)
> before writing code.

> **Keep the style the app already uses — don't switch styles just to change colors.** When the request
> is about *appearance*, customize *within* the style the integration already has. The **Icon style is
> the default and is generally preferred** (the modern look, fully customizable including the background
> color). So:
> - App on the **Icon style** (the default) → recolor by customizing the **icon** (e.g. its background
>   color) via `iconForRecognizedBarcode`. This covers "make recognized barcodes green", "color each
>   barcode by its data", etc. **Do not switch to the Dot style just to change a color.**
> - Use a **`Brush`** only if the app is **already** on the Dot style, or the user **explicitly** asks
>   to switch to it. A brush set on an Icon-style view has no effect.

`BarcodeCountView` has two highlight styles, chosen via the `newInstance` overload that takes a
`BarcodeCountViewStyle` (`ICON` — the default — or `DOT`). `style` is read-only after construction, so
pick it when creating the view:

```kotlin
val barcodeCountView = BarcodeCountView.newInstance(
    this, dataCaptureContext, barcodeCount, BarcodeCountViewStyle.DOT
)
```

## Icon style (default)

Each recognized barcode is marked with a dot carrying an icon (e.g. a check mark). Customize it by
setting the view's `listener` (`BarcodeCountViewListener`) and returning a `BarcodeCountIcon` from
`iconForRecognizedBarcode` for each barcode. A `BarcodeCountIcon` wraps a `ScanditIcon` built with
`ScanditIconBuilder`:

```kotlin
import android.graphics.Color
import com.scandit.datacapture.barcode.count.ui.icon.BarcodeCountIcon
import com.scandit.datacapture.core.ui.icon.ScanditIcon
import com.scandit.datacapture.core.ui.icon.ScanditIconBuilder
import com.scandit.datacapture.core.ui.icon.ScanditIconShape
import com.scandit.datacapture.core.ui.icon.ScanditIconType

barcodeCountView.listener = object : BarcodeCountViewListener {
    override fun iconForRecognizedBarcode(
        view: BarcodeCountView,
        trackedBarcode: TrackedBarcode
    ): BarcodeCountIcon {
        val icon: ScanditIcon = ScanditIconBuilder()
            .withIcon(ScanditIconType.CHECKMARK)
            .withIconColor(Color.WHITE)
            .withBackgroundColor(Color.GREEN)
            .withBackgroundShape(ScanditIconShape.CIRCLE)   // a background color only shows with a shape set
            .build()
        return BarcodeCountIcon(icon, icon)   // BarcodeCountIcon(defaultIcon, accessibleIcon)
    }
}
```

- The callback returns a **non-null** `BarcodeCountIcon`. To keep the SDK default for a barcode, return
  `BarcodeCountView.defaultRecognizedIcon()` (and `defaultNotInListIcon()` / `defaultAcceptedIcon()` /
  `defaultRejectedIcon()` for the other states).
- `BarcodeCountIcon(defaultIcon, accessibleIcon)` takes a default `ScanditIcon` and an **accessible**
  variant; the SDK picks between them based on the user's accessibility settings (pass the same icon for
  both if you don't need a distinct accessible version).
- `ScanditIconBuilder` chains `.withIcon(ScanditIconType)`, `.withIconColor(Int?)`,
  `.withBackgroundColor(Int?)`, `.withBackgroundStrokeColor(Int?)`, `.withBackgroundStrokeWidth(Float)`,
  and `.withBackgroundShape(ScanditIconShape)` (`CIRCLE` / `SQUARE`), then `.build()`. Colors are
  **Android color ints**. `ScanditIconType` values are uppercase: `CHECKMARK`, `X_MARK`, `QUESTION_MARK`,
  `EXCLAMATION_MARK`, `TO_PICK`, `WRONG_ITEM`, `LOW_STOCK`, `INSPECT_ITEM`, `EXPIRED_ITEM`,
  `FRAGILE_ITEM`, `STAR_FILLED`, `STAR_HALF_FILLED`, `STAR_OUTLINED`, `ARROW_*`, `CHEVRON_*`, `PRINT`,
  `PLUS`, `MINUS`, `DELETE`, `SLASH`. (Omit `.withIcon(...)` to keep the default glyph and only recolor.)
- **A background color only renders if you also set a background shape** — pair `.withBackgroundColor(...)`
  with `.withBackgroundShape(ScanditIconShape.CIRCLE)` (or `SQUARE`).
- To override one specific tracked barcode imperatively:
  `barcodeCountView.setIconForRecognizedBarcode(trackedBarcode, barcodeCountIcon)`.

The icon callbacks mirror the brush ones: `iconForRecognizedBarcode`, `iconForRecognizedBarcodeNotInList`,
`iconForAcceptedBarcode`, `iconForRejectedBarcode` — the not-in-list / accepted / rejected ones only
appear when scanning against a list (see `list-scanning.md`).

## Dot style

Set `BarcodeCountViewStyle.DOT` in `newInstance` (above). Each recognized barcode is marked with a
colored dot, customized with a `Brush`. A `Brush` is constructed with a fill color, a stroke color, and
a stroke width — the colors are **Android color ints** and the width is a `Float`:

```kotlin
import android.graphics.Color
import com.scandit.datacapture.core.ui.style.Brush

barcodeCountView.recognizedBrush = Brush(Color.argb(76, 0, 200, 0), Color.GREEN, 2f)  // Brush(fillColor, strokeColor, strokeWidth)
```

To start from the SDK's recommended brush, read the static factory
`BarcodeCountView.defaultRecognizedBrush()`.

### A brush per individual barcode (listener)

To decide the brush per barcode (e.g. color by payload), set the view's `listener`
(`BarcodeCountViewListener`) and implement `brushForRecognizedBarcode`:

```kotlin
barcodeCountView.listener = object : BarcodeCountViewListener {
    override fun brushForRecognizedBarcode(
        view: BarcodeCountView,
        trackedBarcode: TrackedBarcode
    ): Brush {
        return if (trackedBarcode.barcode.data == "1234567890") {
            Brush(Color.argb(76, 255, 165, 0), Color.rgb(255, 165, 0), 2f)
        } else {
            BarcodeCountView.defaultRecognizedBrush()
        }
    }
}
```

`TrackedBarcode` (imported from `com.scandit.datacapture.barcode.batch.data` — see the Package paths
table in `integration.md`) exposes `.barcode`, `.identifier`, and `.location`; read its payload via
`trackedBarcode.barcode.data`. These listener callbacks arrive on the main thread, so they can touch UI
directly. The same `listener` also delivers the barcode-tap callbacks (`onRecognizedBarcodeTapped`, etc.
— see `integration.md`).

To override one specific tracked barcode imperatively:
`barcodeCountView.setBrushForRecognizedBarcode(trackedBarcode, myBrush)`.

## Other highlight states

`recognizedBrush` / `iconForRecognizedBarcode` cover the basic counting flow. The other states are
customized the **same way** — view properties `notInListBrush` / `acceptedBrush` / `rejectedBrush`, the
listener callbacks `brushForRecognizedBarcodeNotInList` / `brushForAcceptedBarcode` /
`brushForRejectedBarcode` (Dot style) or `iconForRecognizedBarcodeNotInList` / `iconForAcceptedBarcode` /
`iconForRejectedBarcode` (Icon style), or the per-barcode setters. These states only become *visible*
when scanning against a list, so their behavior is covered in `list-scanning.md`; the brushes/icons
themselves are set exactly like the recognized state above.

## After wiring up

Build the project. If a listener method isn't being called or a name doesn't resolve, fetch the
[BarcodeCountView API reference](https://docs.scandit.com/data-capture-sdk/android/barcode-capture/api/ui/barcode-count-view.html)
to confirm the exact current signature before guessing. Always include the docs link in your answer.
