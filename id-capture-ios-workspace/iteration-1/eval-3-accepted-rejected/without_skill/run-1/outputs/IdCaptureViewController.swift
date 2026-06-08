import UIKit
import ScanditIdCapture

class IdCaptureViewController: UIViewController {

    private var context: DataCaptureContext!
    private var camera: Camera?
    private var idCapture: IdCapture!
    private var captureView: DataCaptureView!

    override func viewDidLoad() {
        super.viewDidLoad()
        setupIdCapture()
    }

    private func setupIdCapture() {
        // Create the data capture context with your license key
        context = DataCaptureContext(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

        // Set up the camera
        camera = Camera.default
        context.setFrameSource(camera, completionHandler: nil)

        let cameraSettings = IdCapture.recommendedCameraSettings
        camera?.apply(cameraSettings)

        // Configure accepted documents: US ID cards and US driver's licenses
        let acceptedDocuments: [IdCaptureDocument] = [
            IdCard(region: .usUnspecified),
            DriverLicense(region: .usUnspecified)
        ]

        // Configure rejected documents: passports (regardless of region)
        let rejectedDocuments: [IdCaptureDocument] = [
            Passport(region: .any)
        ]

        // Build the ID capture settings
        let settings = IdCaptureSettings()
        settings.acceptedDocuments = acceptedDocuments
        settings.rejectedDocuments = rejectedDocuments

        // Create the ID capture instance
        idCapture = IdCapture(context: context, settings: settings)
        idCapture.addListener(self)

        // Set up the capture view
        captureView = DataCaptureView(context: context, frame: view.bounds)
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(captureView)
        view.sendSubviewToBack(captureView)

        // Add an ID capture overlay for the viewfinder UI
        IdCaptureOverlay.overlay(with: idCapture, view: captureView)
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        idCapture.isEnabled = true
        camera?.switch(toDesiredState: .on)
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        idCapture.isEnabled = false
        camera?.switch(toDesiredState: .off)
    }
}

// MARK: - IdCaptureListener

extension IdCaptureViewController: IdCaptureListener {

    func idCapture(_ idCapture: IdCapture, didCaptureIn session: IdCaptureSession, frameData: FrameData) {
        guard let capturedId = session.newlyCapturedId else { return }

        idCapture.isEnabled = false

        DispatchQueue.main.async {
            self.handleCapturedId(capturedId)
        }
    }

    func idCapture(_ idCapture: IdCapture, didRejectIn session: IdCaptureSession, frameData: FrameData) {
        guard let rejectedId = session.newlyRejectedId else { return }

        DispatchQueue.main.async {
            self.handleRejectedId(rejectedId)
        }
    }

    private func handleCapturedId(_ capturedId: CapturedId) {
        let message: String
        if let firstName = capturedId.firstName, let lastName = capturedId.lastName {
            message = "Captured: \(firstName) \(lastName)"
        } else {
            message = "Document captured successfully."
        }

        let alert = UIAlertController(title: "Document Accepted", message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .default) { [weak self] _ in
            self?.idCapture.isEnabled = true
        })
        present(alert, animated: true)
    }

    private func handleRejectedId(_ rejectedId: RejectedId) {
        let alert = UIAlertController(
            title: "Document Rejected",
            message: "This document type is not accepted. Please present a US ID card or driver's license.",
            preferredStyle: .alert
        )
        alert.addAction(UIAlertAction(title: "OK", style: .default) { [weak self] _ in
            self?.idCapture.isEnabled = true
        })
        present(alert, animated: true)
    }
}
