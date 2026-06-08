import ScanditCaptureCore
import ScanditIdCapture
import UIKit

class ViewController: UIViewController {

    private var context: DataCaptureContext!
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
        // Enter your Scandit License key here.
        DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
        context = DataCaptureContext.shared

        camera = Camera.default
        context.setFrameSource(camera, completionHandler: nil)

        let recommendedCameraSettings = IdCapture.recommendedCameraSettings
        camera?.apply(recommendedCameraSettings)

        captureView = DataCaptureView(context: context, frame: view.bounds)
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(captureView)

        let settings = IdCaptureSettings()

        // Accept ID cards and driver's licenses from the US only.
        settings.acceptedDocuments = [
            IdCard(region: .us),
            DriverLicense(region: .us),
        ]

        // Explicitly reject passports.
        settings.rejectedDocuments = [
            Passport(region: .any),
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
        showAlert(title: "Captured", message: capturedId.fullName ?? "Unknown") {
            idCapture.isEnabled = true
        }
    }

    func idCapture(_ idCapture: IdCapture, didReject capturedId: CapturedId?, reason: RejectionReason) {
        idCapture.isEnabled = false
        showAlert(title: "Rejected", message: "Document not supported.") {
            idCapture.isEnabled = true
        }
    }

    private func showAlert(title: String, message: String, completion: @escaping () -> Void) {
        DispatchQueue.main.async {
            let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in completion() })
            self.present(alert, animated: true)
        }
    }
}
