import ScanditCaptureCore
import ScanditIdCapture
import UIKit

class IdCaptureViewController: UIViewController {

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
        settings.acceptedDocuments = [Passport(region: .any)]
        settings.scanner = IdCaptureScanner(
            physicalDocument: SingleSideScanner(
                enablingBarcode: false,
                machineReadableZone: true,
                visualInspectionZone: false
            )
        )

        idCapture = IdCapture(context: context, settings: settings)
        idCapture.addListener(self)

        overlay = IdCaptureOverlay(idCapture: idCapture, view: captureView)
    }
}

extension IdCaptureViewController: IdCaptureListener {

    func idCapture(_ idCapture: IdCapture, didCapture capturedId: CapturedId) {
        idCapture.isEnabled = false

        let mrz = capturedId.mrzResult
        let message = [
            capturedId.fullName.map { "Name: \($0)" },
            capturedId.dateOfBirth.map { "DOB: \($0.day)/\($0.month)/\($0.year)" },
            capturedId.dateOfExpiry.map { "Expiry: \($0.day)/\($0.month)/\($0.year)" },
            capturedId.documentNumber.map { "Document #: \($0)" },
            capturedId.nationality.map { "Nationality: \($0)" },
            mrz.map { _ in "MRZ: present" },
        ].compactMap { $0 }.joined(separator: "\n")

        DispatchQueue.main.async {
            let alert = UIAlertController(title: "Passport Scanned", message: message, preferredStyle: .alert)
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
            message = "Capture timed out. Make sure the passport MRZ is visible and well lit, then try again."
        case .notAcceptedDocumentType:
            message = "Document not supported. Only passports are accepted."
        default:
            message = "Could not scan the passport. Please try again."
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
