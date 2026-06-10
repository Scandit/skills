# MatrixScan Count iOS — Tote Mapping (MS Map)

Tote mapping lets you map scanned barcodes to physical **totes** (containers), and even **sub-totes**
(smaller totes inside a larger one) — useful for in-store order-fulfillment, where each scanned item is
assigned to a tote. It is built on top of the basic MatrixScan Count integration (see `integration.md`);
this guide adds the mapping/editor layer on top.

> **Beta API.** The Barcode Count mapping API is still in beta and may change in future SDK versions.
> Verify the current signatures against the
> [BarcodeCount API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api.html)
> before writing code, and always include the docs link in your answer.

The feature involves three pieces:

1. **Enable mapping** on `BarcodeCountSettings` so the mode builds a spatial map of the scanned
   barcodes.
2. **Obtain the spatial grid** (`BarcodeSpatialGrid`) of the scanned barcodes from the session.
3. **Present the editor** (`BarcodeSpatialGridEditorView`) so the user can review / correct the
   tote layout, and read back the finished grid from its delegate.

## 1 — Enable mapping

Set `mappingEnabled` on the `BarcodeCountSettings` **before** constructing the `BarcodeCount` mode:

```swift
let settings = BarcodeCountSettings()
settings.set(symbology: .ean13UPCA, enabled: true)
settings.mappingEnabled = true

let barcodeCount = BarcodeCount(context: context, settings: settings)
```

## 2 — Obtain the spatial grid from the session

The arrangement of the scanned barcodes is exposed as a `BarcodeSpatialGrid`, read from the
`BarcodeCountSession` via `spatialMap()` (or the hinted overload that takes an expected row/column
count). The session is only valid inside the listener callback:

```swift
extension CountViewController: BarcodeCountListener {
    func barcodeCount(_ barcodeCount: BarcodeCount,
                      didScanIn session: BarcodeCountSession,
                      frameData: FrameData) {
        guard let grid = session.spatialMap() else { return }
        // grid.rows / grid.columns; grid.element(atRow:column:) -> BarcodeSpatialGridElement?
        DispatchQueue.main.async {
            self.presentToteEditor(with: grid)
        }
    }
}
```

- `spatialMap()` returns a `BarcodeSpatialGrid?`. There is also
  `spatialMap(withExpectedNumberOfRows:expectedNumberOfColumns:)` when you know the expected layout.
- A `BarcodeSpatialGrid` exposes `rows`, `columns`, `element(atRow:column:)`, and `row(at:)`. Each
  `BarcodeSpatialGridElement` has a `mainBarcode` and an optional `subBarcode` (the sub-tote barcode).

## 3 — Present the spatial-grid editor

`BarcodeSpatialGridEditorView` is a `UIView` that lets the user review and correct the tote layout.
Construct it with the grid and a `BarcodeSpatialGridEditorViewSettings`, set its `delegate`, and add it
to your hierarchy:

```swift
func presentToteEditor(with grid: BarcodeSpatialGrid) {
    let editorSettings = BarcodeSpatialGridEditorViewSettings()
    let editorView = try? BarcodeSpatialGridEditorView(frame: view.bounds,
                                                       grid: grid,
                                                       settings: editorSettings)
    editorView?.delegate = self
    if let editorView { view.addSubview(editorView) }
}

extension CountViewController: BarcodeSpatialGridEditorViewDelegate {
    func barcodeSpatialGridEditorView(_ view: BarcodeSpatialGridEditorView,
                                      didFinishEditingWith spatialGrid: BarcodeSpatialGrid) {
        // The user finished — read the corrected tote layout from spatialGrid.
    }

    func didCancelEditing(in view: BarcodeSpatialGridEditorView) {
        // The user cancelled.
    }
}
```

- The editor initializer is **throwing** — `BarcodeSpatialGridEditorView(frame:grid:settings:)`.
- `BarcodeSpatialGridEditorViewSettings` customizes the editor's text (`reorderHintText`,
  `toteTextFormat`, `finishMappingButtonText`, …).
- The delegate is `BarcodeSpatialGridEditorViewDelegate`:
  `barcodeSpatialGridEditorView(_:didFinishEditingWith:)` delivers the finished grid;
  `didCancelEditing(in:)` reports a cancel.

## After wiring up

Build the project. Because this is a beta API, if a class or selector doesn't resolve, fetch the
[BarcodeCount API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api.html)
to confirm the current shape before guessing. Always include the docs link in your answer.
