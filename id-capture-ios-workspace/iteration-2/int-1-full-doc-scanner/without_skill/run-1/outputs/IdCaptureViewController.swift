import UIKit
import ScanditIdCapture
import ScanditCaptureCore

class ViewController: UIViewController {

    private var context: DataCaptureContext!
    private var camera: Camera?
    private var idCapture: IdCapture!
    private var captureView: DataCaptureView!

    override func viewDidLoad() {
        super.viewDidLoad()
        setupScanning()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        idCapture.isEnabled = true
        camera?.switch(toDesiredState: .on)
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        idCapture.isEnabled = false
        camera?.switch(toDesiredState: .off)
    }

    private func setupScanning() {
        // Create data capture context with your license key
        context = DataCaptureContext(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

        // Set up the camera
        camera = Camera.default
        context.setFrameSource(camera, completionHandler: nil)

        // Build the capture view and add it to the hierarchy
        captureView = DataCaptureView(context: context, frame: view.bounds)
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(captureView)
        view.sendSubviewToBack(captureView)

        // Configure ID capture to scan passports, driver's licenses, and ID cards from any region
        let supportedDocuments: [IdDocumentType] = [
            .idCardVIZ,
            .dlVIZ,
            .passportMRZ,
            .idCardMRZ,
            .visaMRZ,
            .passportVIZ
        ]

        let settings = IdCaptureSettings()
        settings.supportedDocuments = supportedDocuments

        // Enable both sides so we capture data from front and back
        settings.scannerType = SingleSideScanner(enabled: false) // use full document scanner
        // For both-sides scanning use FullDocumentScanner
        let fullDocumentSettings = IdCaptureSettings()
        fullDocumentSettings.supportedDocuments = supportedDocuments
        fullDocumentSettings.scannerType = FullDocumentScanner()

        idCapture = IdCapture(context: context, settings: fullDocumentSettings)
        idCapture.addListener(self)

        // Add the ID capture overlay to the capture view
        let overlay = IdCaptureOverlay(idCapture: idCapture, view: captureView)
        _ = overlay
    }

    private func showResult(title: String, message: String) {
        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }
            self.idCapture.isEnabled = false

            let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: "OK", style: .default) { [weak self] _ in
                guard let self = self else { return }
                // Reset ID capture and re-enable scanning for the next document
                self.idCapture.reset()
                self.idCapture.isEnabled = true
            })
            self.present(alert, animated: true)
        }
    }
}

// MARK: - IdCaptureListener

extension ViewController: IdCaptureListener {

    func idCapture(_ idCapture: IdCapture, didCaptureIn session: IdCaptureSession, frameData: FrameData) {
        guard let capturedId = session.newlyCapturedId else { return }

        // Build a message with the available fields
        var lines: [String] = []

        if let fullName = capturedId.fullName {
            lines.append("Name: \(fullName)")
        } else {
            // Fallback: compose from first/last name
            var nameParts: [String] = []
            if let first = capturedId.firstName { nameParts.append(first) }
            if let last = capturedId.lastName { nameParts.append(last) }
            if !nameParts.isEmpty {
                lines.append("Name: \(nameParts.joined(separator: " "))")
            }
        }

        if let dob = capturedId.dateOfBirth {
            let dobString = String(format: "%04d-%02d-%02d", dob.year, dob.month, dob.day)
            lines.append("Date of Birth: \(dobString)")
        }

        if let docNumber = capturedId.documentNumber {
            lines.append("Document Number: \(docNumber)")
        }

        let message = lines.isEmpty ? "Document captured." : lines.joined(separator: "\n")
        showResult(title: "Document Captured", message: message)
    }

    func idCapture(_ idCapture: IdCapture, didRejectIn session: IdCaptureSession, frameData: FrameData) {
        showResult(title: "Document Rejected", message: "The document could not be recognized. Please ensure it is well-lit and fully visible, then try again.")
    }
}
