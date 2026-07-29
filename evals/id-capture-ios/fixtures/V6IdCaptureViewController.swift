import UIKit
import ScanditCaptureCore
import ScanditIdCapture

class IdCaptureViewController: UIViewController {

    private lazy var idCaptureSettings = IdCaptureSettings()

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

    func setupRecognition() {
        context = DataCaptureContext.licensed

        camera = Camera.default
        context.setFrameSource(camera, completionHandler: nil)

        let recommendedCameraSettings = IdCapture.recommendedCameraSettings
        camera?.apply(recommendedCameraSettings)

        captureView = DataCaptureView(context: context, frame: view.bounds)
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(captureView)

        idCaptureSettings.supportedDocuments = [
            .idCardVIZ,
            .dlVIZ,
            .passportMRZ
        ]

        idCapture = IdCapture(context: context, settings: idCaptureSettings)
        idCapture.addListener(self)

        overlay = IdCaptureOverlay(idCapture: idCapture, view: captureView)
    }
}

extension IdCaptureViewController: IdCaptureListener {

    func idCapture(_ idCapture: IdCapture, didCaptureIn session: IdCaptureSession, frameData: FrameData) {
        guard let capturedId = session.newlyCapturedId else { return }
        idCapture.isEnabled = false
        showAlert(title: "Recognized", message: descriptionForCapturedId(result: capturedId)) {
            idCapture.isEnabled = true
        }
    }

    func idCapture(_ idCapture: IdCapture, didRejectIn session: IdCaptureSession, frameData: FrameData) {
        idCapture.isEnabled = false
        showAlert(message: "Document not supported") {
            idCapture.isEnabled = true
        }
    }

    func showAlert(title: String? = nil, message: String? = nil, completion: @escaping () -> Void) {
        DispatchQueue.main.async {
            let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in completion() })
            self.present(alert, animated: true)
        }
    }

    func descriptionForCapturedId(result: CapturedId) -> String {
        var results = [String]()
        if !result.fullName.isEmpty { results.append("Full Name: \(result.fullName)") }
        if let dob = result.dateOfBirth { results.append("Date of Birth: \(dob)") }
        if let docNumber = result.documentNumber { results.append("Document Number: \(docNumber)") }
        return results.joined(separator: "\n")
    }
}
