import UIKit
import ScanditIdCapture
import ScanditCaptureCore

class ViewController: UIViewController {

    private var context: DataCaptureContext!
    private var idCapture: IdCapture!
    private var camera: Camera?
    private var captureView: DataCaptureView!

    override func viewDidLoad() {
        super.viewDidLoad()
        setupScanning()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        camera?.switch(toDesiredState: .on)
        idCapture.isEnabled = true
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        camera?.switch(toDesiredState: .off)
        idCapture.isEnabled = false
    }

    private func setupScanning() {
        // 1. Create the data capture context with your license key
        context = DataCaptureContext(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

        // 2. Configure the camera
        camera = Camera.default
        context.setFrameSource(camera, completionHandler: nil)

        let cameraSettings = IdCapture.recommendedCameraSettings
        camera?.apply(cameraSettings)

        // 3. Create and configure the capture view
        captureView = DataCaptureView(context: context, frame: view.bounds)
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(captureView)

        // 4. Configure ID Capture to recognize passports, driver's licenses, and ID cards
        let supportedDocuments: [IdDocumentType] = [
            .passport,
            .driverLicense,
            .idCard
        ]

        let supportedSides = SupportedSides.frontAndBack

        let settings = IdCaptureSettings()
        settings.supportedDocuments = supportedDocuments
        settings.supportedSides = supportedSides

        // 5. Create IdCapture and add the listener
        idCapture = IdCapture(context: context, settings: settings)
        idCapture.addListener(self)

        // 6. Add an IdCaptureOverlay for the default scanning UI
        let overlay = IdCaptureOverlay(idCapture: idCapture, view: captureView)
        _ = overlay
    }

    private func showResult(title: String, message: String) {
        DispatchQueue.main.async { [weak self] in
            guard let self else { return }
            // Pause scanning while the alert is shown
            self.idCapture.isEnabled = false

            let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: "OK", style: .default) { [weak self] _ in
                // Resume scanning after the user dismisses the alert
                self?.idCapture.isEnabled = true
            })
            self.present(alert, animated: true)
        }
    }
}

// MARK: - IdCaptureListener

extension ViewController: IdCaptureListener {

    func idCapture(_ idCapture: IdCapture, didCaptureIn session: IdCaptureSession, frameData: FrameData) {
        guard let capturedId = session.newlyCapturedId else { return }

        let fullName = capturedId.fullName ?? "Unknown"
        let dateOfBirth = capturedId.dateOfBirth.map { formatDate($0) } ?? "Unknown"
        let documentNumber = capturedId.documentNumber ?? "Unknown"

        let message = """
            Full Name: \(fullName)
            Date of Birth: \(dateOfBirth)
            Document Number: \(documentNumber)
            """

        showResult(title: "Document Scanned", message: message)
    }

    func idCapture(_ idCapture: IdCapture, didRejectIn session: IdCaptureSession, frameData: FrameData) {
        let reason: String
        if let rejectionReason = session.rejectionReason {
            switch rejectionReason {
            case .notAcceptedDocumentType:
                reason = "This document type is not supported."
            case .timeout:
                reason = "Scanning timed out. Please try again."
            case .singleImageNotRecognized:
                reason = "Document not recognized. Please try again."
            @unknown default:
                reason = "Document could not be scanned. Please try again."
            }
        } else {
            reason = "Document could not be scanned. Please try again."
        }

        showResult(title: "Document Rejected", message: reason)
    }

    // MARK: - Helpers

    private func formatDate(_ date: DateResult) -> String {
        let calendar = Calendar.current
        let year = date.year.map(String.init) ?? "????"
        let month = date.month.map { String(format: "%02d", $0) } ?? "??"
        let day = date.day.map { String(format: "%02d", $0) } ?? "??"
        _ = calendar
        return "\(year)-\(month)-\(day)"
    }
}
