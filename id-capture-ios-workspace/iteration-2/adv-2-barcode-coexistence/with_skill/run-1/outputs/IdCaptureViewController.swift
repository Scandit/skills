import ScanditCaptureCore
import ScanditIdCapture
import UIKit

class IdCaptureViewController: UIViewController {

    // The DataCaptureContext is shared across the app — BarcodeCapture already
    // holds a reference to it. Access via DataCaptureContext.shared.
    private var context: DataCaptureContext { DataCaptureContext.shared }

    private var camera: Camera?
    private var idCapture: IdCapture!
    private var captureView: DataCaptureView!
    private var overlay: IdCaptureOverlay!

    override func viewDidLoad() {
        super.viewDidLoad()
        setupCapture()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        // Remove whatever mode BarcodeCapture has registered before adding IdCapture.
        // Without this, both modes would be active simultaneously and the SDK would
        // surface an incompatibility error on the DataCaptureView.
        context.removeCurrentMode()

        idCapture = IdCapture(context: context, settings: makeSettings())
        idCapture.addListener(self)
        overlay = IdCaptureOverlay(idCapture: idCapture, view: captureView)

        idCapture.isEnabled = true
        camera?.switch(toDesiredState: .on)
    }

    override func viewDidDisappear(_ animated: Bool) {
        super.viewDidDisappear(animated)
        // Disable and remove IdCapture so the previous screen can re-add BarcodeCapture
        // to the same context without conflicts.
        idCapture.isEnabled = false
        context.removeCurrentMode()
        camera?.switch(toDesiredState: .off)
    }

    // MARK: - Setup

    private func setupCapture() {
        camera = Camera.default
        context.setFrameSource(camera, completionHandler: nil)
        camera?.apply(IdCapture.recommendedCameraSettings)

        captureView = DataCaptureView(context: context, frame: view.bounds)
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(captureView)
    }

    private func makeSettings() -> IdCaptureSettings {
        let settings = IdCaptureSettings()
        settings.acceptedDocuments = [
            Passport(region: .any),
            DriverLicense(region: .any),
            IdCard(region: .any),
        ]
        settings.scanner = IdCaptureScanner(physicalDocument: FullDocumentScanner())
        return settings
    }
}

// MARK: - IdCaptureListener

extension IdCaptureViewController: IdCaptureListener {

    func idCapture(_ idCapture: IdCapture, didCapture capturedId: CapturedId) {
        // Disable the mode immediately so the same document isn't captured again
        // while the result is being displayed.
        idCapture.isEnabled = false

        let lines: [String] = [
            capturedId.fullName.map { "Name: \($0)" },
            capturedId.dateOfBirth.map { dob in "DOB: \(dob.day)/\(dob.month)/\(dob.year)" },
            capturedId.documentNumber.map { "Document #: \($0)" },
        ].compactMap { $0 }
        let message = lines.isEmpty ? "Document captured." : lines.joined(separator: "\n")

        // Callbacks arrive on a background thread — dispatch UI work to the main queue.
        DispatchQueue.main.async {
            let alert = UIAlertController(title: "Document Recognized", message: message, preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in
                idCapture.isEnabled = true
            })
            self.present(alert, animated: true)
        }
    }

    func idCapture(_ idCapture: IdCapture, didReject capturedId: CapturedId?, reason: RejectionReason) {
        idCapture.isEnabled = false

        let message: String
        switch reason {
        case .timeout:
            message = "Capture timed out. Make sure the document is well lit and try again."
        case .documentExpired:
            message = "This document has expired. Please use a valid document."
        default:
            message = "Document not supported. Please try a different document."
        }

        DispatchQueue.main.async {
            let alert = UIAlertController(title: "Not Recognized", message: message, preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in
                idCapture.isEnabled = true
            })
            self.present(alert, animated: true)
        }
    }
}
