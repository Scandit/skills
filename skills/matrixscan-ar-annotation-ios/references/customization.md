# MatrixScan AR Annotations — Customization

This file covers customizing annotation **content, appearance, position, and visibility** on iOS. It assumes an annotation is already being returned from a `BarcodeArAnnotationProvider` — if the provider is not yet set up, load `integration.md` first (or together).

Annotations are far more configurable than highlights: content composition (sub-components), position (anchor), when they appear (trigger), sizing presets, colors, and — for responsive — close-up / far-away switching.

## Do not mirror — fetch

The customization surface is wide, spans multiple types and sub-component classes, and grows across SDK versions (e.g. `BarcodeArResponsiveAnnotation` was added mid-v8). **Do not rely on memorized property names, defaults, or enum cases.** For any customization request, fetch the API page for the annotation type the user is working with and apply the properties documented there.

## Pages to fetch

| Topic | Page to fetch |
|---|---|
| `BarcodeArStatusIconAnnotation` properties (icon, text, colors, anchor) | https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api/ui/barcode-ar-status-icon-annotation.html |
| `BarcodeArInfoAnnotation` properties (header/footer/body, width preset, colors, anchor, tappability) | https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api/ui/barcode-ar-info-annotation.html |
| `BarcodeArInfoAnnotationHeader` (header sub-component) | https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api/ui/barcode-ar-info-annotation-header.html |
| `BarcodeArInfoAnnotationBodyComponent` (body sub-component — used in an array) | https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api/ui/barcode-ar-info-annotation-body-component.html |
| `BarcodeArInfoAnnotationFooter` (footer sub-component) | https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api/ui/barcode-ar-info-annotation-footer.html |
| `BarcodeArPopoverAnnotation` properties (buttons, anchor, tappability) | https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api/ui/barcode-ar-popover-annotation.html |
| `BarcodeArPopoverAnnotationButton` (button sub-component used in the popover's buttons array) | Follow the link from the popover-annotation page |
| `BarcodeArResponsiveAnnotation` (close-up / far-away wrapper + threshold class var) | https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api/ui/barcode-ar-responsive-annotation.html |
| `BarcodeArAnnotation` base protocol (including the `annotationTrigger` property shared across all types) | https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api/ui/barcode-ar-annotation.html |
| `ScanditIcon` / `ScanditIconBuilder` (used by status-icon annotations and some info-annotation sub-components) | https://docs.scandit.com/data-capture-sdk/ios/core/api/ui/scandit-icon.html |

Always include the link in your answer.

## Concepts shared across annotation types

Three concepts recur — understand them first, then apply per-type customization from the fetched page.

### Annotation trigger (`annotationTrigger`)

All four concrete annotation types expose `annotationTrigger: BarcodeArAnnotationTrigger`. This controls **when** the annotation becomes visible. Exact cases come from the fetched page; mention them by name once you have it. Defaults vary per type, so read the per-type page before assuming.

If the user asks "make the annotation only appear when tapped" or "always show the annotation", that's an `annotationTrigger` change, not a provider change.

### Anchor (`anchor`)

All concrete annotation types expose an `anchor` property with a per-type enum (e.g. `BarcodeArInfoAnnotationAnchor`, `BarcodeArStatusIconAnnotationAnchor`, `BarcodeArPopoverAnnotationAnchor`). Cases typically include `.top`, `.bottom`, `.left`, `.right`. Confirm exact cases from the fetched page — do not assume all types have the same cases.

### Composition (`BarcodeArInfoAnnotation` + `BarcodeArResponsiveAnnotation`)

- `BarcodeArInfoAnnotation` content is built from optional `header` / `footer` and an array of `body` components. Each sub-component has its own API page and its own set of properties (text, icon, colors, tappability). Fetch the sub-component page — don't guess field names.
- `BarcodeArResponsiveAnnotation` wraps a close-up and a far-away `BarcodeArInfoAnnotation`. Either may be `nil` — pass only one side to show an annotation at that range and nothing at the other. If the user wants "different detail at different distances," supply both; if they want "only show a detailed annotation when the user is close," supply close-up only (far-away `nil`). The distance switch is a threshold (class-level, percentage of screen area).

## Applying a customization

1. Configure the annotation *inside* the provider's `annotation(for:…)` method, before returning / calling the completion handler — same pattern as highlights.
2. When the customization involves a sub-component (e.g. setting the info annotation's header), construct the sub-component first, set its properties, then assign it to the parent annotation's property.
3. For `BarcodeArResponsiveAnnotation`, build both the close-up and far-away `BarcodeArInfoAnnotation` instances fully *before* wrapping, not after — the wrapper takes them in its initializer.

## What does NOT belong here

- The *which-type-to-use* decision — see `integration.md`'s annotation-types table.
- Attaching a tap delegate / reacting to taps — see `user-interaction.md`.
- Highlight customization (`Brush`, highlight-specific properties) — that's the highlights skill.
- View-level settings on `BarcodeArView` (camera switch, torch, zoom) — these are view-configuration concerns, not annotation customization.
