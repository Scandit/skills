---
name: barcode-capture-ios
description: Fixture skill for the accuracy-review call tests.
---

# Barcode Capture (iOS)

Add the overlay to the capture view:

```swift
let overlay = BarcodeCaptureOverlay(barcodeCapture: barcodeCapture, view: captureView, style: .legacy)
```

Then enable the mode.
