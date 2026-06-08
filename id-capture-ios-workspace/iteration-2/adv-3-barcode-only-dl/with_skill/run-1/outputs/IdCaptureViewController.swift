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
        settings.acceptedDocuments = [DriverLicense(region: .us)]
        // Read only the PDF417 barcode on the back — skip VIZ and MRZ entirely.
        settings.scanner = IdCaptureScanner(
            physicalDocument: SingleSideScanner(
                enablingBarcode: true,
                machineReadableZone: false,
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

        // Pull data from the barcode result — VIZ and MRZ are not scanned.
        let barcode = capturedId.barcode
        let message = [
            capturedId.fullName.map { "Name: \($0)" },
            capturedId.dateOfBirth.map { "DOB: \($0.day)/\($0.month)/\($0.year)" },
            capturedId.documentNumber.map { "Doc #: \($0)" },
            barcode.map { _ in "Barcode data captured" },
        ].compactMap { $0 }.joined(separator: "\n")

        DispatchQueue.main.async {
            let alert = UIAlertController(title: "Barcode Scanned", message: message, preferredStyle: .alert)
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
            message = "Capture timed out. Make sure the back of the license is well lit and try again."
        case .notAcceptedDocumentType:
            message = "Document not supported. Please scan a US driver's license."
        default:
            message = "Document could not be scanned. Please try again."
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
