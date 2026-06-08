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
            static let expired = "Document is expired. Please use a valid document."
            static let inconsistentData = "Document data is inconsistent. Please try again."
            static let forgedBarcode = "Barcode appears to be forged. Document rejected."
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
        settings.rejectedDocuments = [
            DriverLicense(region: .any),
            IdCard(region: .any),
            Passport(region: .any),
        ]
        settings.scanner = IdCaptureScanner(physicalDocument: FullDocumentScanner())

        let verificationSettings = AamvaVizBarcodeComparisonVerifier()
        settings.usdlVerification = USDLVerificationSettings(
            verifiers: [
                AamvaBarcodeVerifier(),
                verificationSettings,
            ]
        )
        settings.rejectExpiredIds = true

        idCapture = IdCapture(context: context, settings: settings)
        idCapture.addListener(self)

        overlay = IdCaptureOverlay(idCapture: idCapture, view: captureView)
    }

    private func displayReviewImage(_ image: UIImage, title: String, completion: @escaping () -> Void) {
        DispatchQueue.main.async {
            let imageViewController = UIViewController()
            imageViewController.view.backgroundColor = .black

            let imageView = UIImageView(image: image)
            imageView.contentMode = .scaleAspectFit
            imageView.translatesAutoresizingMaskIntoConstraints = false
            imageViewController.view.addSubview(imageView)

            NSLayoutConstraint.activate([
                imageView.topAnchor.constraint(equalTo: imageViewController.view.safeAreaLayoutGuide.topAnchor),
                imageView.leadingAnchor.constraint(equalTo: imageViewController.view.leadingAnchor),
                imageView.trailingAnchor.constraint(equalTo: imageViewController.view.trailingAnchor),
                imageView.bottomAnchor.constraint(equalTo: imageViewController.view.safeAreaLayoutGuide.bottomAnchor, constant: -60),
            ])

            let titleLabel = UILabel()
            titleLabel.text = title
            titleLabel.textColor = .white
            titleLabel.textAlignment = .center
            titleLabel.translatesAutoresizingMaskIntoConstraints = false
            imageViewController.view.addSubview(titleLabel)

            NSLayoutConstraint.activate([
                titleLabel.topAnchor.constraint(equalTo: imageViewController.view.safeAreaLayoutGuide.topAnchor, constant: 8),
                titleLabel.leadingAnchor.constraint(equalTo: imageViewController.view.leadingAnchor),
                titleLabel.trailingAnchor.constraint(equalTo: imageViewController.view.trailingAnchor),
            ])

            let dismissButton = UIButton(type: .system)
            dismissButton.setTitle("OK", for: .normal)
            dismissButton.translatesAutoresizingMaskIntoConstraints = false
            imageViewController.view.addSubview(dismissButton)

            NSLayoutConstraint.activate([
                dismissButton.bottomAnchor.constraint(equalTo: imageViewController.view.safeAreaLayoutGuide.bottomAnchor, constant: -8),
                dismissButton.centerXAnchor.constraint(equalTo: imageViewController.view.centerXAnchor),
            ])

            dismissButton.addAction(UIAction { [weak imageViewController] _ in
                imageViewController?.dismiss(animated: true, completion: completion)
            }, for: .touchUpInside)

            imageViewController.modalPresentationStyle = .fullScreen
            self.present(imageViewController, animated: true)
        }
    }
}

extension IdCaptureViewController: IdCaptureListener {

    func idCapture(_ idCapture: IdCapture, didCapture capturedId: CapturedId) {
        idCapture.isEnabled = false

        // Check for expiry
        if let expiry = capturedId.dateOfExpiry {
            let calendar = Calendar.current
            let expiryDate = calendar.date(from: DateComponents(
                year: expiry.year,
                month: expiry.month,
                day: expiry.day
            ))
            if let expiryDate = expiryDate, expiryDate < Date() {
                showAlert(title: "Expired Document", message: Constants.Message.expired) {
                    idCapture.isEnabled = true
                }
                return
            }
        }

        // Check USDL verification result
        if let verificationResult = capturedId.usdlVerificationResult {
            if !verificationResult.allChecksPassed {
                let message = descriptionForCapturedId(result: capturedId)
                let frontReviewImage = verificationResult.frontReviewImage

                if let reviewImage = frontReviewImage {
                    displayReviewImage(reviewImage, title: "Verification Issues - Front Image") {
                        idCapture.isEnabled = true
                    }
                } else {
                    showAlert(
                        title: "Verification Failed",
                        message: message
                    ) {
                        idCapture.isEnabled = true
                    }
                }
                return
            }
        }

        // Successful scan
        let message = descriptionForCapturedId(result: capturedId)

        if let verificationResult = capturedId.usdlVerificationResult,
           let reviewImage = verificationResult.frontReviewImage {
            displayReviewImage(reviewImage, title: "Recognized Document - Review Image") {
                idCapture.isEnabled = true
            }
        } else {
            showAlert(
                title: "Recognized Document",
                message: message
            ) {
                idCapture.isEnabled = true
            }
        }
    }

    func idCapture(_ idCapture: IdCapture, didReject capturedId: CapturedId?, reason: RejectionReason) {
        idCapture.isEnabled = false

        switch reason {
        case .timeout:
            showAlert(message: Constants.Message.timeout) {
                idCapture.isEnabled = true
            }
        case .notAcceptedDocumentType:
            showAlert(message: Constants.Message.rejected) {
                idCapture.isEnabled = true
            }
        case .expired:
            showAlert(title: "Expired Document", message: Constants.Message.expired) {
                idCapture.isEnabled = true
            }
        case .inconsistentData:
            if let capturedId = capturedId,
               let verificationResult = capturedId.usdlVerificationResult,
               let reviewImage = verificationResult.frontReviewImage {
                displayReviewImage(reviewImage, title: "Inconsistent Data - Front Review Image") {
                    idCapture.isEnabled = true
                }
            } else {
                showAlert(title: "Inconsistent Data", message: Constants.Message.inconsistentData) {
                    idCapture.isEnabled = true
                }
            }
        case .holdingWrongSide:
            showAlert(message: "Please flip the document to the other side.") {
                idCapture.isEnabled = true
            }
        default:
            showAlert(message: Constants.Message.rejected) {
                idCapture.isEnabled = true
            }
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
