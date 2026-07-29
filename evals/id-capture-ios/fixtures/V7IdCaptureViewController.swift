import ScanditIdCapture
import UIKit

class IdCaptureViewController: UIViewController {

    private lazy var context = DataCaptureContext.shared
    private lazy var camera = Camera.default
    private lazy var captureView = DataCaptureView(context: context, frame: view.bounds)

    private lazy var idCaptureSettings: IdCaptureSettings = {
        let settings = IdCaptureSettings()

        settings.acceptedDocuments = [
            IdCard(region: .any),
            DriverLicense(region: .any),
            Passport(region: .any),
        ]

        settings.scannerType = FullDocumentScanner()

        return settings
    }()

    private lazy var idCapture: IdCapture = {
        let idCapture = IdCapture(context: context, settings: idCaptureSettings)
        idCapture.addListener(self)
        return idCapture
    }()

    private lazy var overlay = IdCaptureOverlay(idCapture: idCapture, view: captureView)

    override func viewDidLoad() {
        super.viewDidLoad()
        context.setFrameSource(camera, completionHandler: nil)
        camera?.apply(IdCapture.recommendedCameraSettings)
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(captureView)
        _ = overlay
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
}

extension IdCaptureViewController: IdCaptureListener {

    func idCapture(_ idCapture: IdCapture, didCapture capturedId: CapturedId) {
        idCapture.isEnabled = false
        DispatchQueue.main.async {
            let alert = UIAlertController(title: "Recognized", message: capturedId.fullName, preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in idCapture.isEnabled = true })
            self.present(alert, animated: true)
        }
    }

    func idCapture(_ idCapture: IdCapture, didReject capturedId: CapturedId?, reason: RejectionReason) {
        idCapture.isEnabled = false
        DispatchQueue.main.async {
            let alert = UIAlertController(title: "Rejected", message: "Document not supported", preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in idCapture.isEnabled = true })
            self.present(alert, animated: true)
        }
    }
}
