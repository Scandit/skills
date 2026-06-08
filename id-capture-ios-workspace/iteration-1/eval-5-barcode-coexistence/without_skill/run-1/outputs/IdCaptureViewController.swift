import UIKit
import ScanditIdCapture

class IdCaptureViewController: UIViewController {

    private var context: DataCaptureContext!
    private var camera: Camera?
    private var idCapture: IdCapture!
    private var captureView: DataCaptureView!

    override func viewDidLoad() {
        super.viewDidLoad()
        setupDataCaptureContext()
        setupCamera()
        setupIdCapture()
        setupCaptureView()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        // Enable IdCapture and start the camera when this screen becomes visible.
        idCapture.isEnabled = true
        camera?.switch(toDesiredState: .on)
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        // Disable IdCapture and stop the camera when leaving this screen.
        // This ensures IdCapture does not process frames while inactive and
        // releases the camera so BarcodeCapture can resume on the other screen.
        idCapture.isEnabled = false
        camera?.switch(toDesiredState: .off)
    }

    // MARK: - Setup

    private func setupDataCaptureContext() {
        // Re-use the shared context that the rest of the app (including
        // BarcodeCapture) was created with.  Using a single context is the
        // correct way to achieve mode co-existence: each screen owns its own
        // mode object but they all share the same context and camera.
        context = DataCaptureContext.licensed
    }

    private func setupCamera() {
        // Use the same default camera position used elsewhere in the app.
        let cameraSettings = IdCapture.recommendedCameraSettings
        camera = Camera.default
        camera?.apply(cameraSettings)
        context.setFrameSource(camera, completionHandler: nil)
    }

    private func setupIdCapture() {
        // Build the list of documents this screen should accept.
        let settings = IdCaptureSettings()
        settings.acceptedDocuments = [
            IdCard(supportedSides: .frontAndBack),
            Passport(supportedSides: .singleSide),
            DriverLicense(supportedSides: .frontAndBack)
        ]

        idCapture = IdCapture(context: context, settings: settings)
        idCapture.addListener(self)
        // Keep disabled until viewWillAppear so that frames are not processed
        // while the view is off-screen (important for co-existence).
        idCapture.isEnabled = false
    }

    private func setupCaptureView() {
        captureView = DataCaptureView(context: context, frame: view.bounds)
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(captureView)

        // Add an IdCaptureOverlay so the viewfinder and feedback are shown.
        let overlay = IdCaptureOverlay(idCapture: idCapture, view: captureView)
        _ = overlay // retained by captureView
    }
}

// MARK: - IdCaptureListener

extension IdCaptureViewController: IdCaptureListener {

    func idCapture(_ idCapture: IdCapture, didCaptureIn session: IdCaptureSession, frameData: FrameData) {
        guard let capturedId = session.newlyCapturedId else { return }

        // Disable IdCapture immediately to avoid processing further frames
        // while we handle the result.
        idCapture.isEnabled = false

        DispatchQueue.main.async {
            self.handleCapturedId(capturedId)
        }
    }

    func idCapture(_ idCapture: IdCapture, didRejectIn session: IdCaptureSession, frameData: FrameData) {
        // A document was detected but rejected (e.g. wrong document type or
        // barcode could not be parsed).  Give feedback and let the user try again.
        DispatchQueue.main.async {
            self.showAlert(title: "Document Rejected",
                           message: "The scanned document could not be processed. Please try again.")
        }
    }

    // MARK: - Result handling

    private func handleCapturedId(_ capturedId: CapturedId) {
        let fullName = capturedId.fullName ?? "Unknown"
        let dateOfBirth = capturedId.dateOfBirth?.description ?? "N/A"
        let documentNumber = capturedId.documentNumber ?? "N/A"
        let expiryDate = capturedId.dateOfExpiry?.description ?? "N/A"

        let message = """
        Name: \(fullName)
        Date of Birth: \(dateOfBirth)
        Document Number: \(documentNumber)
        Expiry Date: \(expiryDate)
        """

        showAlert(title: "ID Captured", message: message) {
            // Re-enable scanning after the user dismisses the result.
            self.idCapture.isEnabled = true
        }
    }

    private func showAlert(title: String, message: String, completion: (() -> Void)? = nil) {
        let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in
            completion?()
        })
        present(alert, animated: true)
    }
}
