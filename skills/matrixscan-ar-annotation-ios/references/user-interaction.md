# MatrixScan AR Annotations — User Interaction

This file covers handling user interaction with MatrixScan AR annotations on iOS (most commonly: taps). It assumes MatrixScan AR is already integrated and annotations are already being produced by a `BarcodeArAnnotationProvider` — if not, load `integration.md` first (or together, if the user's question spans both).

## Annotations do NOT use `BarcodeArViewUIDelegate`

`BarcodeArViewUIDelegate` is the tap hook for **highlights only**. Annotation interaction is handled on a **per-annotation-type** basis:

| Annotation type | Interaction model |
|---|---|
| `BarcodeArStatusIconAnnotation` | Self-handled: taps toggle between collapsed (icon only) and expanded (icon + text) states. No delegate. |
| `BarcodeArInfoAnnotation` | `BarcodeArInfoAnnotationDelegate` assigned to the annotation's `delegate` property. Callbacks for tapping header, footer, body component icons, and the whole annotation. |
| `BarcodeArPopoverAnnotation` | `BarcodeArPopoverAnnotationDelegate` assigned to the annotation's `delegate` property. Callbacks for individual-button taps and for whole-popover taps. |
| `BarcodeArResponsiveAnnotation` | Interaction goes through the underlying `BarcodeArInfoAnnotation` (close-up or far-away) — assign the `delegate` on the inner info annotation(s), not on the wrapper. |

If the user says "handle a tap on an annotation" without specifying the type, ask which annotation type they are using — the answer differs.

### Per-element vs. whole-annotation taps (info and popover)

Both `BarcodeArInfoAnnotation` and `BarcodeArPopoverAnnotation` have a boolean that routes taps differently:

- `BarcodeArInfoAnnotation.isEntireAnnotationTappable` — when `false` (default per API), individual elements (header, footer, body-component icons) report taps; when `true`, only the whole-annotation callback fires.
- `BarcodeArPopoverAnnotation.isEntirePopoverTappable` — when `false` (default per API), each button reports its own tap; when `true`, only the whole-popover callback fires.

**This flag decides which delegate callbacks are reachable.** If the user wants to react to a specific button tap, `isEntirePopoverTappable` must be `false`. If they want granular taps on an info annotation's header or footer, `isEntireAnnotationTappable` must be `false`. Confirm exact property defaults and callback names on the fetched per-type page.

## Do not mirror — fetch

Do not rely on memorized delegate method names or signatures. Fetch the relevant delegate page and implement what's documented there.

## Pages to fetch

| Topic | Page to fetch |
|---|---|
| `BarcodeArInfoAnnotation.delegate` and the `BarcodeArInfoAnnotationDelegate` protocol | https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api/ui/barcode-ar-info-annotation.html |
| `BarcodeArPopoverAnnotation.delegate` and the `BarcodeArPopoverAnnotationDelegate` protocol | https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api/ui/barcode-ar-popover-annotation.html |
| `BarcodeArAnnotationTrigger` (interaction affects when annotations appear — see `customization.md` for the trigger concept) | https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api/ui/barcode-ar-annotation.html |

Always include the link in your answer.

## Integration flow

1. Locate the existing `BarcodeArView` and the `BarcodeArAnnotationProvider` implementation. Use the same search approach as in `integration.md` Step 1 (grep for `BarcodeArView`, then `BarcodeAr`, and search the whole project rather than just the file handed to you).
2. Inside the provider, after constructing the annotation, assign its `delegate` property to the object that will receive tap callbacks (typically `self`).
3. Make that object conform to the appropriate delegate protocol (`BarcodeArInfoAnnotationDelegate` or `BarcodeArPopoverAnnotationDelegate`) and implement the callbacks documented on the fetched page.
4. Do not change or re-create the existing `DataCaptureContext`, `BarcodeAr`, lifecycle calls, or any other annotation provider setup beyond what's needed to attach the delegate.
5. If a `delegate` is already assigned on an annotation instance, ask the user whether to replace it or extend the existing conformance before overwriting.

## Interaction via the `annotationTrigger`

Not every "interaction" question is about taps-on-annotations. Some are about **when an annotation appears**:
- "Only show the annotation when the user taps the highlight" → `annotationTrigger` change (see `customization.md`). No delegate needed.
- "Show the annotation immediately on scan, but let the user dismiss it by tapping" → also `annotationTrigger` — the case that toggles on tap.
- "Do something when the user taps a button *inside* the annotation" → that's a delegate callback.

If the request is ambiguous, ask whether the user wants to change *when the annotation appears* (trigger) or *react to a tap inside the annotation* (delegate).

## What does NOT belong here

- Tap handling on highlights (`BarcodeArViewUIDelegate.didTapHighlightFor`) — out of scope for this skill.
- Session-level callbacks (`BarcodeArListener.barcodeAr(_:didUpdate:frameData:)`) — this is about scan results arriving from the SDK, not user interaction with annotations. Out of scope for this skill.
- Camera/torch/zoom controls and their visibility toggles on `BarcodeArView` — these are view-configuration concerns, not annotation interaction.
