import ScanditCaptureCore
import ScanditIdCapture
import UIKit

class IdCaptureViewController: UIViewController {

    private enum Constants {
        enum Message {
            static let timeout =
                "Document capture failed. Make sure the document is well lit and free of glare. "
                + "Alternatively, try scanning another document"
            static let expired = "This ID has expired. Please use a valid document."
            static let forgedBarcode = "This document's barcode appears to be forged."
            static let inconsistentData = "The data on this document is inconsistent."
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
        settings.acceptedDocuments = [DriverLicense(region: .us)]
        settings.scanner = IdCaptureScanner(physicalDocument: FullDocumentScanner())

        // Required for frontReviewImage to be populated in DataConsistencyResult
        settings.setIncludeImage(true, for: .croppedDocument)

        settings.rejectForgedAamvaBarcodes = true
        settings.rejectInconsistentData = true
        settings.rejectExpiredIds = true

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
            self.presentResult(title: "Recognized Document", message: message, reviewImage: reviewImage) {
                idCapture.isEnabled = true
            }
        }
    }

    func idCapture(_ idCapture: IdCapture, didReject capturedId: CapturedId?, reason: RejectionReason) {
        idCapture.isEnabled = false

        let message: String
        let reviewImage: UIImage?

        switch reason {
        case .inconsistentData:
            message = Constants.Message.inconsistentData
            reviewImage = capturedId?.verificationResult.dataConsistency?.frontReviewImage
        case .forgedAamvaBarcode:
            message = Constants.Message.forgedBarcode
            reviewImage = nil
        case .documentExpired:
            message = Constants.Message.expired
            reviewImage = nil
        case .timeout:
            message = Constants.Message.timeout
            reviewImage = nil
        default:
            message = Constants.Message.rejected
            reviewImage = nil
        }

        DispatchQueue.main.async {
            self.presentResult(title: "Scan Rejected", message: message, reviewImage: reviewImage) {
                idCapture.isEnabled = true
            }
        }
    }

    // MARK: - Private helpers

    private func presentResult(
        title: String?,
        message: String?,
        reviewImage: UIImage?,
        completion: @escaping () -> Void
    ) {
        if let image = reviewImage {
            showReviewImageAlert(title: title, message: message, image: image, completion: completion)
        } else {
            showAlert(title: title, message: message, completion: completion)
        }
    }

    private func showAlert(title: String? = nil, message: String? = nil, completion: @escaping () -> Void) {
        let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in completion() })
        present(alert, animated: true)
    }

    private func showReviewImageAlert(
        title: String?,
        message: String?,
        image: UIImage,
        completion: @escaping () -> Void
    ) {
        let imageViewController = UIViewController()
        imageViewController.view.backgroundColor = .systemBackground

        let imageView = UIImageView(image: image)
        imageView.contentMode = .scaleAspectFit
        imageView.translatesAutoresizingMaskIntoConstraints = false
        imageViewController.view.addSubview(imageView)

        let label = UILabel()
        label.text = message
        label.numberOfLines = 0
        label.textAlignment = .center
        label.translatesAutoresizingMaskIntoConstraints = false
        imageViewController.view.addSubview(label)

        let button = UIButton(type: .system)
        button.setTitle("OK", for: .normal)
        button.translatesAutoresizingMaskIntoConstraints = false
        button.addAction(UIAction { [weak imageViewController] _ in
            imageViewController?.dismiss(animated: true, completion: completion)
        }, for: .touchUpInside)
        imageViewController.view.addSubview(button)

        NSLayoutConstraint.activate([
            label.topAnchor.constraint(equalTo: imageViewController.view.safeAreaLayoutGuide.topAnchor, constant: 20),
            label.leadingAnchor.constraint(equalTo: imageViewController.view.leadingAnchor, constant: 16),
            label.trailingAnchor.constraint(equalTo: imageViewController.view.trailingAnchor, constant: -16),

            imageView.topAnchor.constraint(equalTo: label.bottomAnchor, constant: 16),
            imageView.leadingAnchor.constraint(equalTo: imageViewController.view.leadingAnchor, constant: 16),
            imageView.trailingAnchor.constraint(equalTo: imageViewController.view.trailingAnchor, constant: -16),

            button.topAnchor.constraint(equalTo: imageView.bottomAnchor, constant: 16),
            button.centerXAnchor.constraint(equalTo: imageViewController.view.centerXAnchor),
            button.bottomAnchor.constraint(equalTo: imageViewController.view.safeAreaLayoutGuide.bottomAnchor, constant: -20),
        ])

        imageViewController.modalPresentationStyle = .formSheet
        if let sheetController = imageViewController.sheetPresentationController {
            sheetController.detents = [.medium(), .large()]
        }
        imageViewController.title = title

        present(imageViewController, animated: true)
    }

    private func descriptionForCapturedId(result: CapturedId) -> String {
        var parts: [String] = []
        if let fullName = result.fullName { parts.append("Name: \(fullName)") }
        if let dob = result.dateOfBirth { parts.append("DOB: \(dob.day)/\(dob.month)/\(dob.year)") }
        if let expiry = result.dateOfExpiry { parts.append("Expiry: \(expiry.day)/\(expiry.month)/\(expiry.year)") }
        if let docNumber = result.documentNumber { parts.append("Doc #: \(docNumber)") }
        return parts.joined(separator: "\n")
    }
}
