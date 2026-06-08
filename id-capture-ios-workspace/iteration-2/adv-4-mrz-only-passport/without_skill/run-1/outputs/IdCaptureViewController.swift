import UIKit
import ScanditIdCapture

class IdCaptureViewController: UIViewController {

    private var context: DataCaptureContext!
    private var camera: Camera?
    private var idCapture: IdCapture!
    private var captureView: DataCaptureView!

    override func viewDidLoad() {
        super.viewDidLoad()
        setupScanning()
    }

    private func setupScanning() {
        // Create the data capture context
        context = DataCaptureContext(licenseKey: "-- ENTER YOUR LICENSE KEY --")

        // Set up the camera
        camera = Camera.default
        context.setFrameSource(camera, completionHandler: nil)

        // Configure IdCapture to read only MRZ from passports
        let settings = IdCaptureSettings()
        settings.supportedDocuments = [.visaIcao, .passportMrz]
        settings.supportedSides = .frontOnly

        // Create IdCapture with the settings
        idCapture = IdCapture(context: context, settings: settings)
        idCapture.addListener(self)

        // Set up the capture view
        captureView = DataCaptureView(context: context, frame: view.bounds)
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(captureView)
        view.sendSubviewToBack(captureView)
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

extension IdCaptureViewController: IdCaptureListener {

    func idCapture(_ idCapture: IdCapture, didCapture capturedId: CapturedId) {
        idCapture.isEnabled = false

        guard let mrzResult = capturedId.mrzResult else { return }

        let firstName = capturedId.firstName ?? ""
        let lastName = capturedId.lastName ?? ""
        let documentNumber = mrzResult.documentNumber
        let dateOfBirth = capturedId.dateOfBirth?.utcIso8601Date ?? ""
        let dateOfExpiry = capturedId.dateOfExpiry?.utcIso8601Date ?? ""
        let nationality = mrzResult.nationality

        let message = """
            Name: \(firstName) \(lastName)
            Document Number: \(documentNumber)
            Date of Birth: \(dateOfBirth)
            Date of Expiry: \(dateOfExpiry)
            Nationality: \(nationality)
            """

        DispatchQueue.main.async {
            let alert = UIAlertController(title: "Passport Scanned", message: message, preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: "OK", style: .default) { [weak self] _ in
                self?.idCapture.isEnabled = true
            })
            self.present(alert, animated: true)
        }
    }

    func idCapture(_ idCapture: IdCapture, didReject capturedId: CapturedId?, reason: RejectionReason) {
        // Handle rejection if needed
    }
}
