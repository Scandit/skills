import ScanditCaptureCore
import ScanditIdCapture
import UIKit

/// ID scanning screen that co-exists correctly with BarcodeCapture.
///
/// This view controller assumes `DataCaptureContext` is shared across the app
/// (i.e. `DataCaptureContext.initialize(licenseKey:)` was already called before
/// this screen is presented, typically in the app delegate or the BarcodeCapture
/// view controller).
///
/// Mode co-existence strategy:
/// - On `viewWillAppear`: call `context.removeCurrentMode()` to tear down
///   whichever mode (e.g. BarcodeCapture) is currently attached, then create
///   and attach `IdCapture`. This prevents the SDK from detecting incompatible
///   concurrent modes and displaying an error on the `DataCaptureView`.
/// - On `viewDidDisappear`: remove `IdCapture` so that when the caller's
///   BarcodeCapture screen becomes active again it can re-attach its own mode
///   cleanly.
class IdCaptureViewController: UIViewController {

    // MARK: - Properties

    private var context: DataCaptureContext { DataCaptureContext.shared }
    private var camera: Camera?
    private var idCapture: IdCapture!
    private var captureView: DataCaptureView!
    private var overlay: IdCaptureOverlay!

    // MARK: - Lifecycle

    override func viewDidLoad() {
        super.viewDidLoad()
        setupCaptureView()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)

        // Remove whatever mode the caller had active (e.g. BarcodeCapture)
        // before attaching IdCapture. This is the required co-existence pattern.
        context.removeCurrentMode()
        setupIdCapture()

        idCapture.isEnabled = true
        camera?.switch(toDesiredState: .on)
    }

    override func viewDidDisappear(_ animated: Bool) {
        super.viewDidDisappear(animated)

        idCapture.isEnabled = false
        camera?.switch(toDesiredState: .off)

        // Remove IdCapture so the caller's mode (e.g. BarcodeCapture) can
        // re-attach to the context without interference.
        context.removeCurrentMode()

        // Clean up the listener reference.
        idCapture.removeListener(self)
    }

    // MARK: - Setup

    /// Creates the `DataCaptureView` once and pins it behind all other subviews.
    /// The view is reused across appearances; only the mode changes.
    private func setupCaptureView() {
        captureView = DataCaptureView(context: context, frame: view.bounds)
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.insertSubview(captureView, at: 0)

        // Camera setup — apply recommended settings for ID capture.
        camera = Camera.default
        context.setFrameSource(camera, completionHandler: nil)
        camera?.apply(IdCapture.recommendedCameraSettings)
    }

    /// Creates `IdCapture` with settings and wires the overlay and listener.
    /// Called on every `viewWillAppear` after removing the previous mode so
    /// that the mode is always freshly attached to the context.
    private func setupIdCapture() {
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

// MARK: - IdCaptureListener

extension IdCaptureViewController: IdCaptureListener {

    func idCapture(_ idCapture: IdCapture, didCapture capturedId: CapturedId) {
        // Disable scanning while the result is displayed.
        idCapture.isEnabled = false

        let message = [
            capturedId.fullName.map { "Name: \($0)" },
            capturedId.dateOfBirth.map { "DOB: \($0.day)/\($0.month)/\($0.year)" },
            capturedId.documentNumber.map { "Doc #: \($0)" },
        ].compactMap { $0 }.joined(separator: "\n")

        DispatchQueue.main.async {
            let alert = UIAlertController(
                title: "Document Recognized",
                message: message.isEmpty ? "No readable fields." : message,
                preferredStyle: .alert
            )
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
        case .documentExpired:
            message = "This document has expired. Please use a valid document."
        case .notAcceptedDocumentType:
            message = "Document type not supported. Try a passport, driver's license, or ID card."
        default:
            message = "Document could not be scanned. Please try again."
        }

        DispatchQueue.main.async {
            let alert = UIAlertController(
                title: "Not Recognized",
                message: message,
                preferredStyle: .alert
            )
            alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in
                idCapture.isEnabled = true
            })
            self.present(alert, animated: true)
        }
    }
}
