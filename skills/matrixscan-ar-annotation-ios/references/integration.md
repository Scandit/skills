# MatrixScan AR Annotations iOS Integration Guide

MatrixScan AR annotations are augmented-reality overlays that display information *about* barcodes in the camera feed — in contrast to highlights, which are simple shapes drawn *on* them. This guide covers attaching annotations to an iOS app. For customization (anchors, triggers, content, colors), see `customization.md`. For user interaction with annotations, see `user-interaction.md`.

## Step 1: Confirm MatrixScan AR is already integrated

This skill assumes MatrixScan AR is already wired up in the project — it covers annotations only. Before writing anything, search the project for existing MatrixScan AR usage. Grep for, in order, and stop when you get a hit:

1. `BarcodeArView` — the view class; its presence is the strongest signal the integration exists.
2. `BarcodeAr` (without the open paren) — catches both `BarcodeAr(...)` construction calls and property declarations like `var scanner: BarcodeAr!` where the type appears but not the init.

Search the whole project, not just the file the user handed you — the `BarcodeArView` may be created in a helper, factory, or separate module.

- **If found** → MatrixScan AR is already set up. Proceed to **Attaching annotations to an existing `BarcodeArView`** below. Do not re-bootstrap the SDK, the license key, or symbologies.
- **If not found** → MatrixScan AR has not been integrated yet. Stop and tell the user that greenfield MatrixScan AR setup (SPM, license, `DataCaptureContext`, `BarcodeAr`, `BarcodeArView`, symbologies, lifecycle) is handled by the dedicated MatrixScan AR integration skill. Do not attempt to bootstrap it from this file.

If the situation is ambiguous (e.g. `BarcodeAr` is imported but no `BarcodeArView` is instantiated), ask the user before assuming.

## Annotation types

MatrixScan AR provides these concrete annotation types. All implement `BarcodeArAnnotation` and are returned from a `BarcodeArAnnotationProvider`. **Do not memorize their properties** — fetch the API page for the type you pick (see the table in `customization.md`).

| Type | When to use |
|---|---|
| `BarcodeArStatusIconAnnotation` | An icon (optionally with short text) that expands/collapses on tap. Good for compact status indicators. |
| `BarcodeArInfoAnnotation` | A structured info card with optional header, body components, and footer. Good for rich details. Has its own tap delegate. |
| `BarcodeArPopoverAnnotation` | A popover with one or more buttons. Good for actionable options tied to a barcode. Has its own tap delegate. |
| `BarcodeArResponsiveAnnotation` | A wrapper around close-up and far-away `BarcodeArInfoAnnotation` instances that switches based on how much of the screen the barcode occupies. Either side may be `nil` — pass only close-up (or only far-away) to show the annotation at one range and nothing at the other. Good for different detail levels at different distances. |

If the user hasn't specified a preference, ask what fits — the right choice is UX-driven, not technical.

## Attaching annotations to an existing `BarcodeArView`

Use this path when MatrixScan AR is already integrated in the project.

1. Locate the existing `BarcodeArView` instance (usually in a view controller or SwiftUI-wrapped view controller). Confirm with the user which file to edit if multiple matches exist.
2. Make that type conform to `BarcodeArAnnotationProvider` and assign it to `barcodeArView.annotationProvider`.
3. Do not touch the existing `DataCaptureContext`, `BarcodeAr`, `BarcodeArSettings`, symbology configuration, or lifecycle calls — those are out of scope for an annotations change. In particular, if the existing code uses `DataCaptureContext.initialize(licenseKey:)` + `DataCaptureContext.shared`, leave it alone — that is the recommended pattern, not a migration target.
4. Match the surrounding code's conventions (e.g. `import ScanditBarcodeCapture` umbrella only — no separate `import ScanditCaptureCore`; existing naming for the setup method like `setupRecognition()`).
5. If a highlight provider is already assigned (`barcodeArView.highlightProvider = ...`), leave it alone. Annotations and highlights are independent and can coexist on the same view.

Minimal addition (UIKit):

```swift
// In the view controller that already owns `barcodeArView`:
barcodeArView.annotationProvider = self
```

`BarcodeArAnnotationProvider` offers two equivalent variants — a completion-handler form and an `async` form. Implementing either one satisfies conformance; implement only the variant that matches the surrounding code. If the project already uses `async`/`await` (e.g. nearby methods are `async`, call sites use `Task { }`), use the async variant; otherwise use the completion handler.

Completion-handler variant:

```swift
extension ViewController: BarcodeArAnnotationProvider {
    func annotation(
        for barcode: Barcode,
        completionHandler: @escaping ((any UIView & BarcodeArAnnotation)?) -> Void
    ) {
        let annotation = BarcodeArStatusIconAnnotation(barcode: barcode)
        completionHandler(annotation)
    }
}
```

Async variant:

```swift
extension ViewController: BarcodeArAnnotationProvider {
    func annotation(for barcode: Barcode) async -> (any UIView & BarcodeArAnnotation)? {
        return BarcodeArStatusIconAnnotation(barcode: barcode)
    }
}
```

If the project already assigns an `annotationProvider`, ask the user whether they want to replace it or modify the existing one before overwriting.

## Choosing an annotation type in code

- **`BarcodeArStatusIconAnnotation(barcode:)`** — simplest, zero extra arguments.
- **`BarcodeArInfoAnnotation(barcode:)`** — simplest construction, but almost always customized immediately (header/footer/body). See `customization.md`.
- **`BarcodeArPopoverAnnotation(barcode:buttons:)`** — requires an array of `BarcodeArPopoverAnnotationButton`. Cannot be constructed with zero buttons meaningfully; ask the user which buttons are needed.
- **`BarcodeArResponsiveAnnotation(barcode:closeUp:farAway:)`** — wraps a close-up and a far-away `BarcodeArInfoAnnotation`. Either may be `nil` to suppress display at that range. Useful when the same barcode needs different detail at different distances, or when you want an annotation only when the user is close / only when they are far.

For any construction detail beyond what's shown here (exact property names, available anchors, trigger enum cases, sub-component types, colors), fetch the relevant API page rather than guessing — follow the pointers in `customization.md`.

## Custom annotations (beyond the four built-in types)

The four concrete types cover most needs, but the provider's return type is `(any UIView & BarcodeArAnnotation)?` — meaning **any `UIView` subclass can be an annotation** as long as it conforms to the `BarcodeArAnnotation` protocol. Reach for this when the user wants UI that the built-in types plus customization (`customization.md`) cannot express — for example: a bespoke layout mixing chart data with text, a branded visual that doesn't fit the info / popover / status-icon moulds, or a view driven by animations that aren't exposed as properties on the concrete types.

The `BarcodeArAnnotation` protocol has **two required members**:

```swift
func update(with location: Quadrilateral, highlight: (any UIView & BarcodeArHighlight)?)
var annotationTrigger: BarcodeArAnnotationTrigger { get set }
```

- `update(with:highlight:)` is called on every frame the barcode is tracked, on the main thread. It receives the barcode's `Quadrilateral` (four `CGPoint` corners — `topLeft`, `topRight`, `bottomLeft`, `bottomRight` — in the parent view's coordinate space) and the highlight view currently drawn over the barcode (or `nil` if no highlight provider is attached). Use it to position your annotation and, if needed, align relative to the highlight.
- `annotationTrigger` controls **when** the annotation appears. It is part of the protocol itself — not optional. See `customization.md` for the valid enum cases; typically you store a default in a stored property.

Unlike the built-in types, **the protocol has no `barcode` property**. If your annotation needs the barcode (for data lookup, analytics, tap routing), capture it at construction time and store it yourself.

Minimal custom annotation (UIKit) — a price badge positioned above the barcode:

```swift
import ScanditBarcodeCapture
import UIKit

class PriceBadgeAnnotation: UIView, BarcodeArAnnotation {
    var annotationTrigger: BarcodeArAnnotationTrigger = .highlightTapAndBarcodeScan

    private let barcode: Barcode
    private let label = UILabel()

    init(barcode: Barcode, price: String) {
        self.barcode = barcode
        super.init(frame: .zero)
        backgroundColor = UIColor.systemBlue
        layer.cornerRadius = 8
        label.text = price
        label.textColor = .white
        label.font = .boldSystemFont(ofSize: 14)
        label.textAlignment = .center
        label.translatesAutoresizingMaskIntoConstraints = false
        addSubview(label)
        NSLayoutConstraint.activate([
            label.leadingAnchor.constraint(equalTo: leadingAnchor, constant: 8),
            label.trailingAnchor.constraint(equalTo: trailingAnchor, constant: -8),
            label.topAnchor.constraint(equalTo: topAnchor, constant: 4),
            label.bottomAnchor.constraint(equalTo: bottomAnchor, constant: -4),
        ])
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

    func update(with location: Quadrilateral, highlight: (any UIView & BarcodeArHighlight)?) {
        // Position the badge centred horizontally above the barcode.
        let topMidX = (location.topLeft.x + location.topRight.x) / 2
        let topY = min(location.topLeft.y, location.topRight.y)
        let size = systemLayoutSizeFitting(UIView.layoutFittingCompressedSize)
        bounds = CGRect(origin: .zero, size: size)
        center = CGPoint(x: topMidX, y: topY - size.height / 2 - 8)
        // The `highlight` parameter is available if you want to anchor against the drawn highlight
        // rather than the raw barcode quad (e.g. to sit just above a circle highlight's top edge).
    }
}
```

Return an instance of the custom class from the provider exactly the same way you'd return a built-in annotation — the return type already accepts it:

```swift
extension ViewController: BarcodeArAnnotationProvider {
    func annotation(
        for barcode: Barcode,
        completionHandler: @escaping ((any UIView & BarcodeArAnnotation)?) -> Void
    ) {
        // Look up the price for this barcode in your data source, then construct the annotation.
        let price = priceLookup[barcode.data ?? ""] ?? "—"
        completionHandler(PriceBadgeAnnotation(barcode: barcode, price: price))
    }
}
```

A few practical notes:
- Do not call `update(with:highlight:)` yourself — the SDK drives it.
- The `Quadrilateral` coordinates are in the parent view's coordinate space, so they go directly into UIKit positioning APIs (`center`, `frame`). When drawing a shape inside the view's own `bounds`, translate corners by the view's origin.
- Set `annotationTrigger` as a stored property with the default that fits the use case (e.g. `.highlightTapAndBarcodeScan` for "show on scan, let the user dismiss via tap").
- For interaction (taps), custom annotations do **not** get the built-in `BarcodeArInfoAnnotationDelegate` / `BarcodeArPopoverAnnotationDelegate` callbacks. Use a `UITapGestureRecognizer` on the custom view if the user needs tap handling.
- If the user wants a simple barcode *outline* (coloured shape over the barcode, no text/UI), that is highlight territory (`matrixscan-ar-highlight-ios` skill) — annotations are for information *about* barcodes, highlights are for shapes *on* them.
