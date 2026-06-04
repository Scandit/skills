# ID Capture — iOS (Swift/UIKit) Integration Guide

ID Capture extracts data from identity documents — passports, driver's licenses, ID cards, residence permits, health-insurance cards, visas — by reading the MRZ (machine-readable zone), VIZ (visual inspection zone / printed text), and/or the PDF417 barcode on the back. You declare which documents you accept and which scanner to use, and the SDK returns a `CapturedId` with the holder's data.

Examples below use Swift and a `UIViewController`. Adapt ownership of `DataCaptureContext`, `Camera`, `IdCapture`, `DataCaptureView`, and the overlay to the project's existing structure.

## Prerequisites

- Scandit Data Capture SDK for iOS — add via Swift Package Manager:
  - URL: `https://github.com/Scandit/datacapture-spm`
  - Add `ScanditIdCapture` and `ScanditCaptureCore` package products to your target
- A valid Scandit license key:
  - Sign in at <https://ssl.scandit.com> to generate one.
  - No account yet? Sign up at <https://ssl.scandit.com/dashboard/sign-up?p=test>.
- `NSCameraUsageDescription` in `Info.plist`:
  ```xml
  <key>NSCameraUsageDescription</key>
  <string>Used to scan identity documents.</string>
  ```
  Without this key the app crashes on first camera access. iOS prompts the user for permission automatically the first time the camera opens — there is no separate runtime-permission code to write.

## Interactive Document Configuration

Before writing any code, walk the user through what they're scanning. Ask one question at a time.

**Question A — Which documents do you need to accept?** Present this list and ask which apply:
- `Passport` — passport booklets (MRZ)
- `DriverLicense` — driver's licenses (front VIZ + back PDF417 barcode)
- `IdCard` — national / regional ID cards
- `ResidencePermit` — residence permits
- `HealthInsuranceCard` — health-insurance cards
- `VisaIcao` — ICAO visas
- `RegionSpecific` — special document subtypes (e.g. a US Global Entry card) selected via `RegionSpecificSubtype`

Each takes an `IdCaptureRegion` (e.g. `.any`, `.us`, `.euAndSchengen`). Recommend the narrowest region the use case allows — it's faster and more accurate than `.any`.

**Question B — Which scanner?**
- **`FullDocumentScanner()`** — reads front and back automatically. The right default for most ID/DL use cases.
- **`SingleSideScanner(enablingBarcode:machineReadableZone:visualInspectionZone:)`** — reads a single side from only the zones you enable. Use when you only need, say, the back PDF417 barcode of a US license, or only the passport MRZ. (See `references/advanced.md`.)
- **`MobileDocumentScanner(enablingIso180135:ocr:)`** — mobile driver's licenses (mDL) displayed on a screen. (See `references/advanced.md`.)

**Question C — Which fields do you need to read?** (full name, date of birth, expiry, document number, nationality, …) This drives what you pull off `CapturedId` and informs whether anonymization is appropriate.

**Question D — Which `UIViewController` should the integration code go in?** Then write the code directly into that file.

## Step 1 — Initialize the SDK and create the DataCaptureContext

Initialize the SDK with your license key once (typically in `viewDidLoad` or a lazy property), then access the shared context.

```swift
import ScanditCaptureCore
import ScanditIdCapture

// In viewDidLoad or a lazy property:
DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
let context = DataCaptureContext.shared
```

The `DataCaptureContext` is the central hub. Construct it once and reuse it for the lifetime of the scanning surface.

## Step 2 — Build the settings (accepted documents + scanner)

`IdCaptureSettings` is configured by setting properties — there is no builder and no `supportedDocuments` bitmask. Set `acceptedDocuments` to the documents you accept and `scanner` to an `IdCaptureScanner` wrapping a physical and/or mobile scanner.

```swift
let settings = IdCaptureSettings()

settings.acceptedDocuments = [
    Passport(region: .any),
    DriverLicense(region: .any),
    IdCard(region: .any),
]

settings.scanner = IdCaptureScanner(physicalDocument: FullDocumentScanner())
```

**Notes:**
- `acceptedDocuments` takes an array of `IdCaptureDocument` values constructed with a region: `IdCard(region: .any)`, `DriverLicense(region: .us)`, etc.
- `scanner` always requires an `IdCaptureScanner` wrapper. For a typical document scan, use `IdCaptureScanner(physicalDocument: FullDocumentScanner())`.
- Do **not** write `settings.supportedDocuments` (v6 API) or `settings.scannerType = FullDocumentScanner()` (v7 API) — both are removed.
- Optional rejection rules, verification flags, and anonymization are set as properties here — see `references/advanced.md`.

## Step 3 — Create the IdCapture mode

```swift
let idCapture = IdCapture(context: context, settings: settings)
```

Key members:

| Member | Description |
|---|---|
| `IdCapture(context:settings:)` | Creates the mode and attaches it to the context. |
| `isEnabled` | `Bool` (get/set) — set `false` while a result is shown; re-enable to scan again. |
| `static recommendedCameraSettings` | Recommended camera settings for ID capture. |
| `applySettings(_:)` | Apply new settings at runtime. |
| `addListener(_:)` / `removeListener(_:)` | Register / remove an `IdCaptureListener`. |
| `feedback` | `IdCaptureFeedback` (get/set) — sound / vibration. |
| `reset()` | Reset capture state (e.g. before starting a new scan after showing results). |

## Step 4 — Set up the camera

Get the default camera, apply the recommended ID-capture settings to it, and attach it to the context.

```swift
let camera = Camera.default
context.setFrameSource(camera, completionHandler: nil)

let recommendedCameraSettings = IdCapture.recommendedCameraSettings
camera?.apply(recommendedCameraSettings)
```

The camera is off by default. Turn it on in `viewWillAppear` and off in `viewDidDisappear` (Step 7).

## Step 5 — Visualize with DataCaptureView + IdCaptureOverlay

```swift
let captureView = DataCaptureView(context: context, frame: view.bounds)
captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
view.addSubview(captureView)

let overlay = IdCaptureOverlay(idCapture: idCapture, view: captureView)
```

The `IdCaptureOverlay` draws the document viewfinder on top of the camera preview and is optional but strongly recommended. Key members:

| Member | Description |
|---|---|
| `IdCaptureOverlay(idCapture:view:)` | Creates and attaches the overlay to the view. |
| `idLayoutStyle` | `.rounded` (default) / `.square`. |
| `idLayoutLineStyle` | `.bold` / `.light`. |
| `showTextHints` / `textHintPosition` | Toggle/position on-screen hints. |
| `setFrontSideTextHint(_:)` / `setBackSideTextHint(_:)` | Customize hint text. |
| `capturedBrush` / `localizedBrush` / `rejectedBrush` | Brush appearance per scan state. |

## Step 6 — Implement IdCaptureListener

Conform to `IdCaptureListener`. **Both callbacks are called on a background thread** — dispatch UI work to the main thread, and disable the mode while a result is displayed so the same document isn't captured repeatedly.

```swift
extension IdCaptureViewController: IdCaptureListener {

    func idCapture(_ idCapture: IdCapture, didCapture capturedId: CapturedId) {
        // Stop capturing while we show the result.
        idCapture.isEnabled = false

        // Callback is on a background thread — dispatch to the main queue.
        DispatchQueue.main.async {
            let message = self.descriptionForCapturedId(capturedId)
            self.showAlert(title: "Recognized Document", message: message) {
                idCapture.isEnabled = true  // resume scanning
            }
        }
    }

    func idCapture(_ idCapture: IdCapture, didReject capturedId: CapturedId?, reason: RejectionReason) {
        idCapture.isEnabled = false

        let message: String
        switch reason {
        case .timeout:
            message = "Capture failed. Make sure the document is well lit and try again."
        default:
            message = "Document not supported. Try scanning another document."
        }

        DispatchQueue.main.async {
            self.showAlert(message: message) {
                idCapture.isEnabled = true
            }
        }
    }
}
```

Register the listener in `viewWillAppear` and remove it in `viewDidDisappear` (Step 7).

### Reading field values

`CapturedId` exposes the common holder fields at the top level, regardless of which zone they came from:

| Accessor | Type | Notes |
|---|---|---|
| `capturedId.fullName` / `firstName` / `lastName` | `String?` | |
| `capturedId.dateOfBirth` / `dateOfExpiry` / `dateOfIssue` | `DateResult?` | `.day` / `.month` / `.year` (`Int`) |
| `capturedId.documentNumber` / `documentAdditionalNumber` | `String?` | |
| `capturedId.nationality` / `nationalityISO` | `String?` | |
| `capturedId.sex` / `sexType` | `String?` / `Sex` enum | |
| `capturedId.age` | `Int?` | |
| `capturedId.isExpired` | `Bool` | |
| `capturedId.address` | `String?` | |
| `capturedId.document?.documentType` | `IdCaptureDocumentType` | which document was recognised |
| `capturedId.issuingCountry` | `IdCaptureRegion` | |

For the richer zone-specific results (`capturedId.mrzResult`, `capturedId.vizResult`, `capturedId.barcode`, `capturedId.mobileDocumentResult`), document images (`capturedId.images`), and the verification outcome (`capturedId.verificationResult`), see `references/advanced.md`.

Always guard for `nil` — a field that wasn't present on the scanned document is `nil`.

## Step 7 — Camera lifecycle

Toggle the camera and listener across the `UIViewController` lifecycle.

```swift
override func viewWillAppear(_ animated: Bool) {
    super.viewWillAppear(animated)
    idCapture.addListener(self)
    idCapture.isEnabled = true
    camera?.switch(toDesiredState: .on)
}

override func viewDidDisappear(_ animated: Bool) {
    super.viewDidDisappear(animated)
    idCapture.removeListener(self)
    idCapture.isEnabled = false
    camera?.switch(toDesiredState: .off)
}
```

> Use `viewDidDisappear` (not `viewWillDisappear`) to turn the camera off — it ensures the camera stays on during push transitions where the scanning screen is still visible.

## Setup checklist

1. Add `ScanditCaptureCore` and `ScanditIdCapture` to the project via SPM (`https://github.com/Scandit/datacapture-spm`).
2. Add `NSCameraUsageDescription` to `Info.plist`.
3. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from <https://ssl.scandit.com>.
4. Call `DataCaptureContext.initialize(licenseKey:)` before accessing `DataCaptureContext.shared`.
5. Apply `IdCapture.recommendedCameraSettings` to the camera.
6. Implement **both** `IdCaptureListener` callbacks and dispatch UI work to the main thread.
7. Set `idCapture.isEnabled = false` before showing results and re-enable when dismissed.

## Complete minimal example

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
    private var overlay: IdCaptureOverlay!

    override func viewDidLoad() {
        super.viewDidLoad()
        setupRecognition()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        idCapture.addListener(self)
        idCapture.isEnabled = true
        camera?.switch(toDesiredState: .on)
    }

    override func viewDidDisappear(_ animated: Bool) {
        super.viewDidDisappear(animated)
        idCapture.removeListener(self)
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
        settings.acceptedDocuments = [
            Passport(region: .any),
            DriverLicense(region: .any),
            IdCard(region: .any),
        ]
        settings.scanner = IdCaptureScanner(physicalDocument: FullDocumentScanner())

        idCapture = IdCapture(context: context, settings: settings)

        overlay = IdCaptureOverlay(idCapture: idCapture, view: captureView)
    }
}

extension IdCaptureViewController: IdCaptureListener {

    func idCapture(_ idCapture: IdCapture, didCapture capturedId: CapturedId) {
        idCapture.isEnabled = false
        let message = [
            capturedId.fullName.map { "Name: \($0)" },
            capturedId.dateOfBirth.map { "DOB: \($0.day)/\($0.month)/\($0.year)" },
            capturedId.documentNumber.map { "Doc #: \($0)" },
        ].compactMap { $0 }.joined(separator: "\n")

        DispatchQueue.main.async {
            let alert = UIAlertController(title: "Recognized", message: message, preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in
                idCapture.isEnabled = true
            })
            self.present(alert, animated: true)
        }
    }

    func idCapture(_ idCapture: IdCapture, didReject capturedId: CapturedId?, reason: RejectionReason) {
        idCapture.isEnabled = false
        let message = reason == .timeout
            ? "Capture timed out. Please try again."
            : "Document not supported."
        DispatchQueue.main.async {
            let alert = UIAlertController(title: "Not recognized", message: message, preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in
                idCapture.isEnabled = true
            })
            self.present(alert, animated: true)
        }
    }
}
```

## Key rules

1. **One context per scanning surface** — call `DataCaptureContext.initialize(licenseKey:)` once and use `DataCaptureContext.shared`.
2. **No settings builder, no bitmask** — `IdCaptureSettings()` then set `acceptedDocuments` and `scanner`.
3. **Documents take a region** — `DriverLicense(region: .us)`, `Passport(region: .any)`, etc.
4. **`scanner` takes an `IdCaptureScanner` wrapper** — `IdCaptureScanner(physicalDocument: FullDocumentScanner())`.
5. **`IdCapture(context:settings:)`** — initializer, not a factory or static `Create`.
6. **Apply `IdCapture.recommendedCameraSettings`** to the camera before starting.
7. **Handle both `didCapture` and `didReject`** — both run on a background thread; dispatch UI work to the main thread.
8. **Set `isEnabled = false` before showing results** and re-enable when the user dismisses.
9. **Camera lifecycle in `viewWillAppear` / `viewDidDisappear`** — turn the camera `.on` when appearing and `.off` when disappearing.
10. **`NSCameraUsageDescription` in `Info.plist`** — required; iOS prompts automatically, no runtime-permission code needed.
11. **`didCapture` fires once per complete document** (not per side or zone — that was the v6 behaviour).
12. **Never read `session.newlyCapturedId`** — `IdCaptureSession` was removed in v7; results are delivered directly via `didCapture(_:capturedId:)`.

## Where to go next

- `references/advanced.md` — scanner selection, rejection rules, verification, anonymization, rich results, overlay customization, BarcodeCapture co-existence.
- [Get Started (iOS)](https://docs.scandit.com/sdks/ios/id-capture/get-started/)
