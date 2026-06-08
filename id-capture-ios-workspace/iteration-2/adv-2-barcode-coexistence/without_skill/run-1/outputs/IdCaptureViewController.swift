import ScanditCaptureCore
import ScanditIdCapture
import UIKit

class IdCaptureViewController: UIViewController {

    private lazy var context = DataCaptureContext.shared
    private var camera: Camera?
    private var captureView: DataCaptureView!
    private var idCapture: IdCapture!
    private var overlay: IdCaptureOverlay!

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
        // Disable IdCapture and turn camera off when leaving this screen.
        // The BarcodeCapture screen will re-enable its own mode when it appears.
        idCapture.isEnabled = false
        camera?.switch(toDesiredState: .off)
    }

    private func setupRecognition() {
        // BarcodeCapture and IdCapture modes can co-exist with limitations placed on the
        // types of documents that can be scanned. We remove any pre-existing mode so that
        // IdCapture can operate with full functionality on this screen.
        context.removeCurrentMode()

        camera = Camera.default
        let cameraSettings = IdCapture.recommendedCameraSettings
        camera?.apply(cameraSettings)
        context.setFrameSource(camera, completionHandler: nil)

        captureView = DataCaptureView(context: context, frame: view.bounds)
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(captureView)

        let settings = IdCaptureSettings()
        settings.acceptedDocuments = [
            IdCard(region: .any),
            DriverLicense(region: .any),
            Passport(region: .any),
        ]
        settings.scanner = IdCaptureScanner(physicalDocument: FullDocumentScanner())

        idCapture = IdCapture(context: context, settings: settings)
        idCapture.addListener(self)

        overlay = IdCaptureOverlay(idCapture: idCapture, view: captureView)
    }
}

extension IdCaptureViewController: IdCaptureListener {

    func idCapture(_ idCapture: IdCapture, didCapture capturedId: CapturedId) {
        idCapture.isEnabled = false
        let message = buildResultMessage(for: capturedId)
        showAlert(title: "Captured ID", message: message) {
            idCapture.isEnabled = true
        }
    }

    func idCapture(_ idCapture: IdCapture, didReject capturedId: CapturedId?, reason: RejectionReason) {
        idCapture.isEnabled = false
        let message: String
        switch reason {
        case .timeout:
            message = "Document capture timed out. Ensure the document is well lit and free of glare."
        default:
            message = "Document not supported. Try scanning another document."
        }
        showAlert(message: message) {
            idCapture.isEnabled = true
        }
    }

    private func showAlert(title: String? = nil, message: String, completion: @escaping () -> Void) {
        DispatchQueue.main.async {
            let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in completion() })
            self.present(alert, animated: true)
        }
    }

    private func buildResultMessage(for capturedId: CapturedId) -> String {
        var parts: [String] = []
        if let fullName = capturedId.fullName {
            parts.append("Name: \(fullName)")
        }
        if let dateOfBirth = capturedId.dateOfBirth {
            parts.append("Date of Birth: \(dateOfBirth)")
        }
        if let dateOfExpiry = capturedId.dateOfExpiry {
            parts.append("Expiry: \(dateOfExpiry)")
        }
        if let documentNumber = capturedId.documentNumber {
            parts.append("Document Number: \(documentNumber)")
        }
        return parts.joined(separator: "\n")
    }
}
