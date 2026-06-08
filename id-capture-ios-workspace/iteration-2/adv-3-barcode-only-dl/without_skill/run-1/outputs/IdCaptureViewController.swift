import UIKit
import ScanditIdCapture

class ViewController: UIViewController {

    private var context: DataCaptureContext!
    private var camera: Camera?
    private var idCapture: IdCapture!
    private var captureView: DataCaptureView!

    override func viewDidLoad() {
        super.viewDidLoad()
        setupScanning()
    }

    private func setupScanning() {
        // Create the data capture context with your license key
        context = DataCaptureContext(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

        // Set up the camera
        camera = Camera.default
        context.setFrameSource(camera, completionHandler: nil)

        // Configure the camera settings for ID capture
        let cameraSettings = IdCapture.recommendedCameraSettings
        camera?.apply(cameraSettings, completionHandler: nil)

        // Configure ID capture to only read the barcode (PDF417) from US driver's licenses
        let settings = IdCaptureSettings()
        settings.acceptedDocuments = [
            IdCapture.document(.driverLicenseOrId, .unitedStatesOfAmerica)
        ]
        settings.scannerType = SingleSideScanner(
            enablingBarcode: true,
            machineReadableZone: false,
            visualInspectionZone: false
        )

        // Create the ID capture instance
        idCapture = IdCapture(context: context, settings: settings)
        idCapture.addListener(self)

        // Set up the capture view
        captureView = DataCaptureView(context: context, frame: view.bounds)
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(captureView)

        // Add an ID capture overlay for visual feedback
        IdCaptureOverlay.overlay(with: idCapture, view: captureView)
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        idCapture.isEnabled = true
        camera?.switch(toDesiredState: .on, completionHandler: nil)
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        idCapture.isEnabled = false
        camera?.switch(toDesiredState: .off, completionHandler: nil)
    }
}

extension ViewController: IdCaptureListener {

    func idCapture(_ idCapture: IdCapture, didCaptureIn session: IdCaptureSession, frameData: FrameData) {
        guard let capturedId = session.newlyCapturedId else { return }

        // The barcode result is available on the captured ID
        let barcodeResult = capturedId.aamvaBarcodeResult

        DispatchQueue.main.async {
            idCapture.isEnabled = false
            self.showResult(for: capturedId, barcodeResult: barcodeResult)
        }
    }

    func idCapture(_ idCapture: IdCapture, didRejectIn session: IdCaptureSession, frameData: FrameData) {
        // Document was rejected — not a US driver's license barcode or not supported
        DispatchQueue.main.async {
            self.showRejectedAlert()
        }
    }

    private func showResult(for capturedId: CapturedId, barcodeResult: AamvaBarcodeResult?) {
        var message = "Name: \(capturedId.fullName ?? "N/A")\n"
        message += "Date of Birth: \(capturedId.dateOfBirth?.description ?? "N/A")\n"
        message += "Document Number: \(capturedId.documentNumber ?? "N/A")\n"

        if let barcode = barcodeResult {
            message += "AAMVA Version: \(barcode.aamvaVersion)\n"
            message += "Issuing Jurisdiction: \(barcode.issuingJurisdiction ?? "N/A")"
        }

        let alert = UIAlertController(title: "Scanned ID", message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "Scan Again", style: .default, handler: { _ in
            idCapture.isEnabled = true
        }))
        present(alert, animated: true)
    }

    private func showRejectedAlert() {
        let alert = UIAlertController(
            title: "Not Recognized",
            message: "Please scan the barcode on the back of a US driver's license.",
            preferredStyle: .alert
        )
        alert.addAction(UIAlertAction(title: "OK", style: .default, handler: { [weak self] _ in
            self?.idCapture.isEnabled = true
        }))
        present(alert, animated: true)
    }
}
