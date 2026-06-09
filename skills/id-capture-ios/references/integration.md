# ID Capture — iOS (Swift/UIKit) Integration Guide

ID Capture reads identity documents — passports, driver's licenses, ID cards, residence permits, health-insurance cards, visas — via MRZ, VIZ, and/or PDF417 barcode. You declare which documents to accept and which scanner to use; the SDK returns a `CapturedId`.

## Prerequisites

- SPM: `https://github.com/Scandit/datacapture-spm` — add `ScanditIdCapture` and `ScanditCaptureCore`
- A valid Scandit license key from <https://ssl.scandit.com>
- `NSCameraUsageDescription` in `Info.plist` — iOS prompts automatically, no runtime-permission code needed

## Before writing code — ask the user

1. **Which documents?** `Passport`, `DriverLicense`, `IdCard`, `ResidencePermit`, `HealthInsuranceCard`, `VisaIcao`, `RegionSpecific`. Each takes an `IdCaptureRegion` (`.any`, `.us`, `.euAndSchengen`, …). Use the narrowest region that fits.
2. **Which scanner?** — see Step 2 below.
3. **Any documents to explicitly exclude?** — use `rejectedDocuments`.
4. **Which fields to read?** Top-level (`fullName`, `dateOfBirth`, `documentNumber`, …) or zone-specific (`mrzResult`, `vizResult`, `barcode`)?
5. **Document images needed?** Face photo, cropped document, or raw frame?
6. **Which `UIViewController` to integrate into?** Write code directly into that file.

## Step 1 — Initialize and create context

```swift
import ScanditCaptureCore
import ScanditIdCapture

DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
let context = DataCaptureContext.shared
```

## Step 2 — Configure settings

### Accepted and rejected documents

```swift
let settings = IdCaptureSettings()

settings.acceptedDocuments = [
    Passport(region: .any),
    DriverLicense(region: .any),
    IdCard(region: .any),
]

// Optional: explicitly reject a subset of accepted documents.
// "Rejected always wins" — a match in rejectedDocuments overrides acceptedDocuments.
settings.rejectedDocuments = [IdCard(region: .france)]
```

Document constructors: `IdCard(region:)`, `DriverLicense(region:)`, `Passport(region:)`, `VisaIcao(region:)`, `ResidencePermit(region:)`, `HealthInsuranceCard(region:)`, `RegionSpecific(subtype:)`.

> **US Visa foil number:** `VisaIcao(region: .us)` with MRZ enabled also captures the foil number; returned in `capturedId.vizResult`.

### Scanner

Choose based on what data you need:

**`FullDocumentScanner`** — reads both sides, all zones. Use when you need complete data from front and back.

```swift
settings.scanner = IdCaptureScanner(physicalDocument: FullDocumentScanner())
```

**`SingleSideScanner`** — one side, only the zones you enable. Use when you need a specific zone only.

```swift
// Back barcode only (US DL):
settings.scanner = IdCaptureScanner(physicalDocument: SingleSideScanner(
    enablingBarcode: true, machineReadableZone: false, visualInspectionZone: false))

// MRZ only (passport):
settings.scanner = IdCaptureScanner(physicalDocument: SingleSideScanner(
    enablingBarcode: false, machineReadableZone: true, visualInspectionZone: false))
```

> When `SingleSideScanner` has both `machineReadableZone` and `visualInspectionZone` enabled and `acceptedDocuments` includes `Passport`, the SDK captures VIZ + MRZ together in a single pass. This is passport-specific — other MRZ documents are not affected.

**`MobileDocumentScanner`** — for IDs presented on another device's screen. Not for physical documents.

- `enablingIso180135: true` — ISO 18013-5 QR + Bluetooth handover
- `ocr: true` — OCR of a digital document displayed on screen

```swift
settings.scanner = IdCaptureScanner(
    physicalDocument: FullDocumentScanner(),
    mobileDocument: MobileDocumentScanner(enablingIso180135: true, ocr: false))
```

### Rejection rules

Set flags before creating `IdCapture`. The SDK calls `didReject` with the matching `RejectionReason` when a rule trips.

| Setting | Rejection reason |
|---|---|
| `rejectExpiredIds = true` | `.documentExpired` |
| `rejectIdsExpiringIn = Duration(days:months:years:)` | `.documentExpiresSoon` |
| `rejectVoidedIds = true` | `.documentVoided` |
| `rejectHolderBelowAge = 21` | `.holderUnderage` |
| `rejectNotRealIdCompliant = true` | `.notRealIdCompliant` |
| `rejectForgedAamvaBarcodes = true` | `.forgedAamvaBarcode` |
| `rejectInconsistentData = true` | `.inconsistentData` |

Verification is settings-driven — there is no verifier class.

### Image capture

Opt in before creating `IdCapture`. Images increase processing time — only request what you need.

```swift
settings.setIncludeImage(true, for: .face)            // holder portrait
settings.setIncludeImage(true, for: .croppedDocument) // cropped document image (required for frontReviewImage)
settings.setIncludeImage(true, for: .frame)            // full camera frame
```

## Step 3 — Create IdCapture

```swift
let idCapture = IdCapture(context: context, settings: settings)
idCapture.addListener(self)  // register once at setup, not in viewWillAppear
```

## Step 4 — Camera

```swift
let camera = Camera.default
context.setFrameSource(camera, completionHandler: nil)
camera?.apply(IdCapture.recommendedCameraSettings)
```

## Step 5 — DataCaptureView + overlay

```swift
let captureView = DataCaptureView(context: context, frame: view.bounds)
captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
view.addSubview(captureView)

let overlay = IdCaptureOverlay(idCapture: idCapture, view: captureView)
```

## Step 6 — Implement IdCaptureListener

Both callbacks run on a **background thread** — dispatch UI work to the main thread. Disable the mode before showing results to prevent re-capture.

```swift
extension IdCaptureViewController: IdCaptureListener {

    func idCapture(_ idCapture: IdCapture, didCapture capturedId: CapturedId) {
        idCapture.isEnabled = false
        DispatchQueue.main.async {
            // Read results — see "Reading results" below
            self.showAlert(title: "Recognized", message: ...) {
                idCapture.isEnabled = true
            }
        }
    }

    func idCapture(_ idCapture: IdCapture, didReject capturedId: CapturedId?, reason: RejectionReason) {
        idCapture.isEnabled = false
        DispatchQueue.main.async {
            let message: String
            switch reason {
            case .documentExpired: message = "This ID has expired."
            case .holderUnderage:  message = "Age requirement not met."
            case .timeout:         message = "Capture timed out. Try again."
            default:               message = "Document not supported."
            }
            self.showAlert(message: message) { idCapture.isEnabled = true }
        }
    }
}
```

Always handle every `RejectionReason` you enable with a distinct user-facing message.

### Reading results

**Top-level fields** (aggregated from all zones):

```swift
capturedId.fullName          // String?
capturedId.dateOfBirth       // DateResult? (.day, .month, .year)
capturedId.dateOfExpiry      // DateResult?
capturedId.documentNumber    // String?
capturedId.nationality       // String?
capturedId.issuingCountry    // IdCaptureRegion
capturedId.document?.documentType  // IdCaptureDocumentType
```

**Zone-specific results** (available when that zone was scanned):

```swift
capturedId.mrzResult         // MrzResult? — MRZ string, check digits
capturedId.vizResult         // VizResult? — VIZ data, capturedSides
capturedId.barcode           // BarcodeResult? — AAMVA data for US/Canadian DLs
capturedId.mobileDocumentResult  // MobileDocumentResult? — ISO 18013-5 mDL data
```

Driving license details (vehicle class, restrictions, endorsements) are nested under `capturedId.barcode` for AAMVA documents.

**Images** (only populated if opted in via `setIncludeImage`):

```swift
capturedId.images.face                         // UIImage?
capturedId.images.croppedDocument(side: .front) // UIImage?
capturedId.images.frame                        // UIImage?
```

## Step 7 — Camera lifecycle

```swift
override func viewWillAppear(_ animated: Bool) {
    super.viewWillAppear(animated)
    idCapture.isEnabled = true
    camera?.switch(toDesiredState: .on)
}

override func viewDidDisappear(_ animated: Bool) {
    super.viewDidDisappear(animated)
    idCapture.isEnabled = false
    camera?.switch(toDesiredState: .off)
}
```

Use `viewDidDisappear` (not `viewWillDisappear`) so the camera stays on during push transitions.

## Complete example

```swift
import ScanditCaptureCore
import ScanditIdCapture
import UIKit

class IdCaptureViewController: UIViewController {

    private lazy var context: DataCaptureContext = {
        DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
        return DataCaptureContext.shared
    }()

    private var camera: Camera?
    private var idCapture: IdCapture!
    private var captureView: DataCaptureView!

    override func viewDidLoad() {
        super.viewDidLoad()
        setupRecognition()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        idCapture.isEnabled = true
        camera?.switch(toDesiredState: .on)
    }

    override func viewDidDisappear(_ animated: Bool) {
        super.viewDidDisappear(animated)
        idCapture.isEnabled = false
        camera?.switch(toDesiredState: .off)
    }

    private func setupRecognition() {
        camera = Camera.default
        context.setFrameSource(camera, completionHandler: nil)
        camera?.apply(IdCapture.recommendedCameraSettings)

        captureView = DataCaptureView(context: context, frame: view.bounds)
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(captureView)

        let settings = IdCaptureSettings()
        settings.acceptedDocuments = [Passport(region: .any), DriverLicense(region: .any), IdCard(region: .any)]
        settings.scanner = IdCaptureScanner(physicalDocument: FullDocumentScanner())

        idCapture = IdCapture(context: context, settings: settings)
        idCapture.addListener(self)
        IdCaptureOverlay(idCapture: idCapture, view: captureView)
    }
}

extension IdCaptureViewController: IdCaptureListener {

    func idCapture(_ idCapture: IdCapture, didCapture capturedId: CapturedId) {
        idCapture.isEnabled = false
        let message = [capturedId.fullName, capturedId.documentNumber]
            .compactMap { $0 }.joined(separator: "\n")
        DispatchQueue.main.async {
            let alert = UIAlertController(title: "Recognized", message: message, preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in idCapture.isEnabled = true })
            self.present(alert, animated: true)
        }
    }

    func idCapture(_ idCapture: IdCapture, didReject capturedId: CapturedId?, reason: RejectionReason) {
        idCapture.isEnabled = false
        let message = reason == .timeout ? "Capture timed out." : "Document not supported."
        DispatchQueue.main.async {
            let alert = UIAlertController(title: "Rejected", message: message, preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in idCapture.isEnabled = true })
            self.present(alert, animated: true)
        }
    }
}
```

## Key rules

1. `DataCaptureContext.initialize(licenseKey:)` once — then `DataCaptureContext.shared`.
2. `settings.scanner` always takes an `IdCaptureScanner` wrapper — not `scannerType` (v7) or `supportedDocuments` (v6).
3. `IdCapture(context:settings:)` — not a factory or static `Create`.
4. `addListener` once after creating the mode, not in `viewWillAppear`.
5. Both callbacks run on a background thread — always `DispatchQueue.main.async` for UI.
6. `isEnabled = false` before showing results; `true` when dismissed.
7. `didCapture` fires once per complete document — not per side or zone (that was v6 behaviour).

## Where to go next

- `references/advanced.md` — USDL verification, anonymization, BarcodeCapture co-existence, overlay/feedback customization.
- [Get Started (iOS)](https://docs.scandit.com/sdks/ios/id-capture/get-started/)
