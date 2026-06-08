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
            static let expired = "This ID has expired. Please use a valid document."
            static let forgedBarcode = "The barcode on this document appears to be forged."
            static let inconsistentData = "The data on this document is inconsistent."
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
        settings.acceptedDocuments = [DriverLicense(region: .us)]
        settings.scanner = IdCaptureScanner(physicalDocument: FullDocumentScanner())
        settings.rejectForgedAamvaBarcodes = true
        settings.rejectInconsistentData = true
        settings.rejectExpiredIds = true
        settings.setIncludeImage(true, for: .croppedDocument)

        idCapture = IdCapture(context: context, settings: settings)
        idCapture.addListener(self)

        overlay = IdCaptureOverlay(idCapture: idCapture, view: captureView)
    }
}

extension IdCaptureViewController: IdCaptureListener {

    func idCapture(_ idCapture: IdCapture, didCapture capturedId: CapturedId) {
        idCapture.isEnabled = false
        let reviewImage = capturedId.verificationResult.dataConsistency?.frontReviewImage
        let message = descriptionForCapturedId(result: capturedId)
        DispatchQueue.main.async {
            self.showResult(title: "Recognized Document", message: message, reviewImage: reviewImage) {
                idCapture.isEnabled = true
            }
        }
    }

    func idCapture(_ idCapture: IdCapture, didReject capturedId: CapturedId?, reason: RejectionReason) {
        idCapture.isEnabled = false
        switch reason {
        case .inconsistentData:
            let reviewImage = capturedId?.verificationResult.dataConsistency?.frontReviewImage
            DispatchQueue.main.async {
                self.showResult(title: "Verification Failed", message: Constants.Message.inconsistentData, reviewImage: reviewImage) {
                    idCapture.isEnabled = true
                }
            }
        case .forgedAamvaBarcode:
            showAlert(title: "Verification Failed", message: Constants.Message.forgedBarcode) {
                idCapture.isEnabled = true
            }
        case .documentExpired:
            showAlert(title: "Document Expired", message: Constants.Message.expired) {
                idCapture.isEnabled = true
            }
        case .timeout:
            showAlert(message: Constants.Message.timeout) {
                idCapture.isEnabled = true
            }
        default:
            showAlert(message: Constants.Message.rejected) {
                idCapture.isEnabled = true
            }
        }
    }

    // Shows an alert with an optional review image displayed above the message.
    private func showResult(title: String? = nil, message: String, reviewImage: UIImage?, completion: @escaping () -> Void) {
        if let image = reviewImage {
            let imageVC = ReviewImageAlertViewController(title: title, message: message, image: image, completion: completion)
            present(imageVC, animated: true)
        } else {
            showAlert(title: title, message: message, completion: completion)
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

// A minimal view controller that presents a review image above an alert-style message.
private final class ReviewImageAlertViewController: UIViewController {

    private let reviewImage: UIImage
    private let alertTitle: String?
    private let alertMessage: String
    private let completion: () -> Void

    init(title: String?, message: String, image: UIImage, completion: @escaping () -> Void) {
        self.alertTitle = title
        self.alertMessage = message
        self.reviewImage = image
        self.completion = completion
        super.init(nibName: nil, bundle: nil)
        modalPresentationStyle = .formSheet
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) not supported") }

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground

        let imageView = UIImageView(image: reviewImage)
        imageView.contentMode = .scaleAspectFit
        imageView.translatesAutoresizingMaskIntoConstraints = false

        let titleLabel = UILabel()
        titleLabel.text = alertTitle
        titleLabel.font = .boldSystemFont(ofSize: 17)
        titleLabel.textAlignment = .center
        titleLabel.numberOfLines = 0
        titleLabel.translatesAutoresizingMaskIntoConstraints = false

        let messageLabel = UILabel()
        messageLabel.text = alertMessage
        messageLabel.font = .systemFont(ofSize: 15)
        messageLabel.textAlignment = .center
        messageLabel.numberOfLines = 0
        messageLabel.translatesAutoresizingMaskIntoConstraints = false

        let okButton = UIButton(type: .system)
        okButton.setTitle("OK", for: .normal)
        okButton.titleLabel?.font = .boldSystemFont(ofSize: 17)
        okButton.translatesAutoresizingMaskIntoConstraints = false
        okButton.addTarget(self, action: #selector(didTapOK), for: .touchUpInside)

        let stack = UIStackView(arrangedSubviews: [imageView, titleLabel, messageLabel, okButton])
        stack.axis = .vertical
        stack.spacing = 16
        stack.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(stack)

        NSLayoutConstraint.activate([
            imageView.heightAnchor.constraint(equalToConstant: 200),
            stack.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 24),
            stack.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -24),
            stack.centerYAnchor.constraint(equalTo: view.centerYAnchor),
        ])
    }

    @objc private func didTapOK() {
        dismiss(animated: true) { self.completion() }
    }
}
