# MatrixScan AR Highlights — User Interaction

This file covers handling user interaction with MatrixScan AR highlights on iOS (most commonly: taps). It assumes MatrixScan AR is already integrated and highlights are already being produced by a `BarcodeArHighlightProvider` — if not, load `integration.md` first (or together, if the user's question spans both).

## The primary interaction hook: `BarcodeArViewUIDelegate`

Tap events on highlights are delivered through `BarcodeArViewUIDelegate`, assigned to `BarcodeArView.uiDelegate`. Do not rely on memorized method names or signatures — fetch the delegate's API page and use what it documents.

Pages to fetch when answering an interaction question:

| Topic | Page to fetch |
|---|---|
| `BarcodeArView.uiDelegate` and the `BarcodeArViewUIDelegate` protocol | https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api/ui/barcode-ar-view.html |
| `BarcodeArHighlight` (what the delegate hands back) | Follow the link from the `BarcodeArView` page |
| `BarcodeArRectangleHighlight` / `BarcodeArCircleHighlight` (concrete types) | https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api/ui/barcode-ar-highlight-rectangle.html · https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api/ui/barcode-ar-highlight-circle.html |

Include the link in your answer.

## Integration flow

1. Locate the existing `BarcodeArView` instance. Use the same search approach as in `integration.md` Step 1 (grep for `BarcodeArView`, then `BarcodeAr`, and search the whole project rather than just the file handed to you).
2. Make the owning type (usually a `UIViewController`) conform to `BarcodeArViewUIDelegate`.
3. Assign it: `barcodeArView.uiDelegate = self`.
4. Implement the tap callback using the signature documented on the fetched `BarcodeArView` page. Do not change or re-create the existing `BarcodeArHighlightProvider`, `DataCaptureContext`, `BarcodeAr`, or lifecycle calls.
5. If a `uiDelegate` is already assigned, ask the user whether to replace it or extend the existing conformance before overwriting.

Inside the tap callback, the delegate receives the tapped `Barcode` and the `UIView & BarcodeArHighlight` instance. From the `Barcode` you can read properties like `data` to branch on what was tapped.

## Per-highlight handling without the delegate

Highlights are plain `UIView`s. If the user needs different behavior per highlight (e.g. different actions for different product IDs) and finds the single `BarcodeArViewUIDelegate` callback too coarse, attaching a `UITapGestureRecognizer` directly to the highlight instance inside the `BarcodeArHighlightProvider` is a valid pattern — do this in addition to, not instead of, the standard delegate route if both are desired. Mention this only if the user's scenario actually calls for it; default to the `uiDelegate` approach.

## What does NOT belong here

- Tap handling on annotations (that's a different provider and a different tap surface) — out of scope for the highlights skill.
- Session-level callbacks (`BarcodeArListener.barcodeAr(_:didUpdate:frameData:)`) — this is about scan results arriving from the SDK, not user interaction with highlights. Out of scope for this skill.
- Camera/torch/zoom controls and their visibility toggles on `BarcodeArView` — these are view-configuration concerns, not highlight interaction.
