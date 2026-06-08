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
        settings.acceptedDocuments = [
            DriverLicense(region: .us),
        ]
        settings.scanner = IdCaptureScanner(physicalDocument: FullDocumentScanner())
        settings.rejectExpiredDocuments = true

        let verificationSettings = AamvaVizBarcodeComparisonVerifier()
        settings.verifier = verificationSettings

        idCapture = IdCapture(context: context, settings: settings)
        idCapture.addListener(self)

        overlay = IdCaptureOverlay(idCapture: idCapture, view: captureView)
    }
}

extension IdCaptureViewController: IdCaptureListener {

    func idCapture(_ idCapture: IdCapture, didCapture capturedId: CapturedId) {
        idCapture.isEnabled = false

        var reviewImage: UIImage? = nil
        if let aamvaResult = capturedId.aamvaVizBarcodeComparisonResult {
            reviewImage = aamvaResult.frontReviewImage
        }

        if let image = reviewImage {
            showAlertWithImage(
                title: "Recognized Document",
                message: descriptionForCapturedId(result: capturedId),
                image: image
            ) {
                idCapture.isEnabled = true
            }
        } else {
            showAlert(
                title: "Recognized Document",
                message: descriptionForCapturedId(result: capturedId)
            ) {
                idCapture.isEnabled = true
            }
        }
    }

    func idCapture(_ idCapture: IdCapture, didReject capturedId: CapturedId?, reason: RejectionReason) {
        idCapture.isEnabled = false

        if reason == .documentDataNotConsistent,
           let capturedId = capturedId,
           let aamvaResult = capturedId.aamvaVizBarcodeComparisonResult,
           let frontImage = aamvaResult.frontReviewImage {
            showAlertWithImage(
                title: "Inconsistent Data Detected",
                message: "The data on the front and back of the document are inconsistent.",
                image: frontImage
            ) {
                idCapture.isEnabled = true
            }
            return
        }

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

    private func showAlertWithImage(title: String? = nil, message: String? = nil, image: UIImage, completion: @escaping () -> Void) {
        DispatchQueue.main.async {
            let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
            let imageView = UIImageView(image: image)
            imageView.contentMode = .scaleAspectFit
            imageView.translatesAutoresizingMaskIntoConstraints = false
            alert.view.addSubview(imageView)
            NSLayoutConstraint.activate([
                imageView.topAnchor.constraint(equalTo: alert.view.topAnchor, constant: 80),
                imageView.centerXAnchor.constraint(equalTo: alert.view.centerXAnchor),
                imageView.widthAnchor.constraint(equalToConstant: 200),
                imageView.heightAnchor.constraint(equalToConstant: 120),
            ])
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
