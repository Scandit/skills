import ScanditCaptureCore
import ScanditIdCapture
import UIKit

class ViewController: UIViewController {

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
            Passport(region: .any),
            DriverLicense(region: .any),
            IdCard(region: .any),
        ]
        settings.scanner = IdCaptureScanner(physicalDocument: FullDocumentScanner())

        idCapture = IdCapture(context: context, settings: settings)
        idCapture.addListener(self)

        overlay = IdCaptureOverlay(idCapture: idCapture, view: captureView)
    }
}

extension ViewController: IdCaptureListener {

    func idCapture(_ idCapture: IdCapture, didCapture capturedId: CapturedId) {
        idCapture.isEnabled = false

        var lines: [String] = []
        if let name = capturedId.fullName {
            lines.append("Name: \(name)")
        }
        if let dob = capturedId.dateOfBirth {
            lines.append("Date of Birth: \(dob.day)/\(dob.month)/\(dob.year)")
        }
        if let docNumber = capturedId.documentNumber {
            lines.append("Document Number: \(docNumber)")
        }
        let message = lines.isEmpty ? "Document recognized." : lines.joined(separator: "\n")

        DispatchQueue.main.async {
            let alert = UIAlertController(title: "Recognized Document", message: message, preferredStyle: .alert)
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
        case .notAcceptedDocumentType:
            message = "This document type is not supported. Please use a passport, driver's license, or ID card."
        case .documentExpired:
            message = "The document appears to be expired."
        case .documentVoided:
            message = "The document appears to be voided."
        default:
            message = "Document could not be recognized. Please try again."
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
