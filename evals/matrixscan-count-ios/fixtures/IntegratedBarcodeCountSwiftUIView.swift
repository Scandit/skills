import SwiftUI
import ScanditBarcodeCapture

// MARK: - SwiftUI layer
//
// MatrixScan Count has no native SwiftUI view (`BarcodeCountView` is a UIView), so we bridge the
// UIKit `CountViewController` into SwiftUI via `UIViewControllerRepresentable`. All `BarcodeCount*`
// API calls live inside the UIKit layer; this SwiftUI struct contains no Scandit code.

struct ScanView: View {
    var body: some View {
        CountViewControllerRepresentable()
            .ignoresSafeArea()
    }
}

struct CountViewControllerRepresentable: UIViewControllerRepresentable {
    func makeUIViewController(context: Context) -> CountViewController {
        CountViewController()
    }

    func updateUIViewController(_ uiViewController: CountViewController, context: Context) {}
}

// MARK: - UIKit layer (MatrixScan Count integration)

class CountViewController: UIViewController {

    // Step 1: the Data Capture Context, created with your license key.
    private lazy var context: DataCaptureContext = {
        DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
        return DataCaptureContext.shared
    }()

    private var camera: Camera?
    private var barcodeCount: BarcodeCount!
    private var barcodeCountView: BarcodeCountView!

    // The app's own running tally. The BarcodeCountSession is only valid inside the listener
    // callback, so we copy the recognized barcodes out into this list (step 7).
    private var allRecognizedBarcodes: [Barcode] = []

    override func viewDidLoad() {
        super.viewDidLoad()
        setupRecognition()
    }

    // Step 6: the camera is NOT turned on automatically. Re-arm the view and switch the camera
    // on when it appears; switch off when it disappears, and tear the view down on the way out.
    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        barcodeCountView.prepareScanning(with: context)
        camera?.switch(toDesiredState: .on)
    }

    override func viewDidDisappear(_ animated: Bool) {
        super.viewDidDisappear(animated)
        camera?.switch(toDesiredState: .off)
        if isMovingFromParent {
            barcodeCountView.stopScanning()
        }
    }

    private func setupRecognition() {
        // Step 3: obtain the camera, apply the recommended settings, and set it as the
        //         context's frame source. Always start from BarcodeCount.recommendedCameraSettings.
        let cameraSettings = BarcodeCount.recommendedCameraSettings
        camera = Camera.default
        camera?.apply(cameraSettings)
        context.setFrameSource(camera)

        // Step 2: configure the Barcode Count mode. Settings start with all symbologies disabled —
        //         enable only the ones the app needs. (Adjust this list to your use case; fewer
        //         enabled symbologies improves scanning performance and accuracy.)
        let settings = BarcodeCountSettings()
        settings.set(symbology: .ean13UPCA, enabled: true)
        settings.set(symbology: .ean8, enabled: true)
        settings.set(symbology: .upce, enabled: true)
        settings.set(symbology: .code128, enabled: true)
        settings.set(symbology: .code39, enabled: true)

        barcodeCount = BarcodeCount(context: context, settings: settings)

        // Step 4: register a listener for completed scan phases.
        barcodeCount.addListener(self)

        // Step 5: add the BarcodeCountView (the built-in AR counting UI). It is designed to be
        //         displayed full screen and does NOT add itself to the hierarchy.
        barcodeCountView = BarcodeCountView(frame: view.bounds,
                                            context: context,
                                            barcodeCount: barcodeCount)
        barcodeCountView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(barcodeCountView)

        // Step 8: handle the List / Exit buttons.
        barcodeCountView.uiDelegate = self
    }
}

// Step 7: collect recognized barcodes when a scan phase completes.
extension CountViewController: BarcodeCountListener {
    func barcodeCount(_ barcodeCount: BarcodeCount,
                      didScanIn session: BarcodeCountSession,
                      frameData: FrameData) {
        // The session is only valid inside this callback — copy out what you need now.
        let recognizedBarcodes = session.recognizedBarcodes
        // This is invoked on an internal recognition thread; hop to main before touching app state.
        DispatchQueue.main.async {
            self.allRecognizedBarcodes = recognizedBarcodes
        }
    }
}

// Step 8: the List / Exit button callbacks. "List" = show progress so far; "Exit" = counting finished.
// The sessionSnapshot gives you the recognized barcodes at tap time (on the main thread).
extension CountViewController: BarcodeCountViewUIDelegate {
    func listButtonTapped(for view: BarcodeCountView,
                          sessionSnapshot: BarcodeCountSessionSnapshot) {
        // Present a list, e.g. from sessionSnapshot.recognizedBarcodes (counting still in progress).
    }

    func exitButtonTapped(for view: BarcodeCountView,
                          sessionSnapshot: BarcodeCountSessionSnapshot) {
        // The user finished — present a summary / complete the scanning.
    }
}
