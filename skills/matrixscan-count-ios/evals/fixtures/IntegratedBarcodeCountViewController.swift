import UIKit
import ScanditBarcodeCapture

class ScanViewController: UIViewController {

    // Step 1: the Data Capture Context, created with your license key.
    private lazy var context: DataCaptureContext = {
        DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
        return DataCaptureContext.shared
    }()

    private var camera: Camera?
    private var barcodeCount: BarcodeCount!
    private var barcodeCountView: BarcodeCountView!

    // The app's own running tally. The BarcodeCountSession is only valid inside the
    // listener callback, so we copy the recognized barcodes out into this list (step 7).
    private var allRecognizedBarcodes: [Barcode] = []

    override func viewDidLoad() {
        super.viewDidLoad()
        setupRecognition()
    }

    // Step 6: the camera is NOT turned on automatically — switch it on when the view
    // appears and off when it disappears.
    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        camera?.switch(toDesiredState: .on)
    }

    override func viewDidDisappear(_ animated: Bool) {
        super.viewDidDisappear(animated)
        camera?.switch(toDesiredState: .off)
    }

    private func setupRecognition() {
        // Step 3: obtain the camera, apply the recommended settings, and set it as the
        //         context's frame source. Always start from BarcodeCount.recommendedCameraSettings.
        let cameraSettings = BarcodeCount.recommendedCameraSettings
        camera = Camera.default
        camera?.apply(cameraSettings)
        context.setFrameSource(camera)

        // Step 2: configure the Barcode Count mode. Settings start with all symbologies
        //         disabled — enable only the ones the app needs. This is a reasonable
        //         default set of common retail / 1D symbologies.
        let settings = BarcodeCountSettings()
        settings.set(symbology: .ean13UPCA, enabled: true)
        settings.set(symbology: .ean8, enabled: true)
        settings.set(symbology: .upce, enabled: true)
        settings.set(symbology: .code128, enabled: true)
        settings.set(symbology: .code39, enabled: true)

        barcodeCount = BarcodeCount(context: context, settings: settings)

        // Step 4: register a listener for completed scan phases.
        barcodeCount.addListener(self)

        // Step 5: add the BarcodeCountView (the built-in AR counting UI). It is designed
        //         to be displayed full screen and does NOT add itself to the hierarchy.
        barcodeCountView = BarcodeCountView(frame: view.bounds,
                                            context: context,
                                            barcodeCount: barcodeCount)
        barcodeCountView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(barcodeCountView)

        // Step 9: handle the List / Exit buttons.
        barcodeCountView.uiDelegate = self
    }
}

// Step 7: collect recognized barcodes when a scan phase completes.
extension ScanViewController: BarcodeCountListener {
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

// Step 9: the List / Exit button callbacks. "List" = show progress so far;
// "Exit" = counting finished. The sessionSnapshot gives you the recognized barcodes
// at tap time (on the main thread).
extension ScanViewController: BarcodeCountViewUIDelegate {
    func listButtonTapped(for view: BarcodeCountView,
                          sessionSnapshot: BarcodeCountSessionSnapshot) {
        // Present a list, e.g. from sessionSnapshot.recognizedBarcodes (counting still in progress).
    }

    func exitButtonTapped(for view: BarcodeCountView,
                          sessionSnapshot: BarcodeCountSessionSnapshot) {
        // The user finished — present a summary / complete the scanning.
    }
}
