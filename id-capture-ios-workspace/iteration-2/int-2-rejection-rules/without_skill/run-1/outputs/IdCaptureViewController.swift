import ScanditCaptureCore
import ScanditIdCapture
import UIKit

class IdCaptureViewController: UIViewController {

    private enum Constants {
        enum Message {
            static let expired = "Document is expired. Please provide a valid, non-expired document."
            static let underage = "You must be 21 or older to proceed."
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
            IdCard(region: .any),
            DriverLicense(region: .any),
            Passport(region: .any),
        ]
        settings.scanner = IdCaptureScanner(physicalDocument: FullDocumentScanner())

        idCapture = IdCapture(context: context, settings: settings)
        idCapture.addListener(self)

        overlay = IdCaptureOverlay(idCapture: idCapture, view: captureView)
    }

    // Returns true if the document has expired relative to today.
    private func isExpired(_ capturedId: CapturedId) -> Bool {
        guard let expiry = capturedId.dateOfExpiry else { return false }
        let today = Calendar.current.dateComponents([.year, .month, .day], from: Date())
        guard let todayYear = today.year, let todayMonth = today.month, let todayDay = today.day else {
            return false
        }
        if expiry.year < todayYear { return true }
        if expiry.year == todayYear && expiry.month < todayMonth { return true }
        if expiry.year == todayYear && expiry.month == todayMonth && expiry.day < todayDay { return true }
        return false
    }

    // Returns true if the holder is under 21 years old.
    private func isUnderage(_ capturedId: CapturedId) -> Bool {
        guard let dob = capturedId.dateOfBirth else { return false }
        var dobComponents = DateComponents()
        dobComponents.year = dob.year
        dobComponents.month = dob.month
        dobComponents.day = dob.day
        guard let birthDate = Calendar.current.date(from: dobComponents) else { return false }
        let age = Calendar.current.dateComponents([.year], from: birthDate, to: Date())
        return (age.year ?? 0) < 21
    }
}

extension IdCaptureViewController: IdCaptureListener {

    func idCapture(_ idCapture: IdCapture, didCapture capturedId: CapturedId) {
        idCapture.isEnabled = false

        if isExpired(capturedId) {
            showAlert(message: Constants.Message.expired) {
                idCapture.isEnabled = true
            }
            return
        }

        if isUnderage(capturedId) {
            showAlert(message: Constants.Message.underage) {
                idCapture.isEnabled = true
            }
            return
        }

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
