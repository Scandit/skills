import ScanditCaptureCore
import ScanditIdCapture
import UIKit

class IdCaptureViewController: UIViewController {

    private enum Constants {
        enum Message {
            static let timeout =
                "Document capture failed. Make sure the document is well lit and free of glare. "
                + "Alternatively, try scanning another document"
            static let rejected = "Document not supported. Try scanning another document"
        }
    }

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
            IdCard(region: .any),
            DriverLicense(region: .any),
            Passport(region: .any),
        ]
        settings.scanner = IdCaptureScanner(physicalDocument: FullDocumentScanner())

        idCapture = IdCapture(context: context, settings: settings)

        overlay = IdCaptureOverlay(idCapture: idCapture, view: captureView)
    }
}

extension IdCaptureViewController: IdCaptureListener {

    func idCapture(_ idCapture: IdCapture, didCapture capturedId: CapturedId) {
        idCapture.isEnabled = false
        showAlert(
            title: "Recognized Document",
            message: descriptionForCapturedId(result: capturedId)
        ) {
            idCapture.isEnabled = true
        }
    }

    func idCapture(_ idCapture: IdCapture, didReject capturedId: CapturedId?, reason: RejectionReason) {
        idCapture.isEnabled = false
        let message = reason == .timeout ? Constants.Message.timeout : Constants.Message.rejected
        showAlert(message: message) {
            idCapture.isEnabled = true
        }
    }

    private func showAlert(title: String? = nil, message: String? = nil, completion: @escaping () -> Void) {
        DispatchQueue.main.async {
            let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in completion() })
            self.present(alert, animated: true)
        }
    }

    private func descriptionForCapturedId(result: CapturedId) -> String {
        var parts: [String] = []
        if let fullName = result.fullName { parts.append("Name: \(fullName)") }
        if let dob = result.dateOfBirth { parts.append("DOB: \(dob.day)/\(dob.month)/\(dob.year)") }
        if let expiry = result.dateOfExpiry { parts.append("Expiry: \(expiry.day)/\(expiry.month)/\(expiry.year)") }
        if let docNumber = result.documentNumber { parts.append("Doc #: \(docNumber)") }
        if let nationality = result.nationality { parts.append("Nationality: \(nationality)") }
        if let docType = result.document?.documentType { parts.append("Type: \(docType)") }
        return parts.joined(separator: "\n")
    }
}
