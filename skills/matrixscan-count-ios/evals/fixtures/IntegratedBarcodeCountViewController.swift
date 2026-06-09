import UIKit
import ScanditBarcodeCapture

class ScanViewController: UIViewController {

    private lazy var context: DataCaptureContext = {
        DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
        return DataCaptureContext.shared
    }()

    private var camera: Camera?
    private var barcodeCount: BarcodeCount!
    private var barcodeCountView: BarcodeCountView!

    // The app's own running tally. The BarcodeCountSession is only valid inside the listener
    // callback, so we copy the recognized barcodes out into this list.
    private var allRecognizedBarcodes: [Barcode] = []

    override func viewDidLoad() {
        super.viewDidLoad()
        setupRecognition()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        camera?.switch(toDesiredState: .on)
    }

    override func viewDidDisappear(_ animated: Bool) {
        super.viewDidDisappear(animated)
        camera?.switch(toDesiredState: .off)
    }

    private func setupRecognition() {
        // Camera: BarcodeCountView does NOT own it — create it, apply the recommended settings,
        // and set it as the context's frame source.
        let cameraSettings = BarcodeCount.recommendedCameraSettings
        camera = Camera.default
        camera?.apply(cameraSettings)
        context.setFrameSource(camera)

        // Settings start with all symbologies disabled — enable only the ones the app needs.
        let settings = BarcodeCountSettings()
        settings.set(symbology: .ean13UPCA, enabled: true)
        settings.set(symbology: .ean8, enabled: true)
        settings.set(symbology: .upce, enabled: true)
        settings.set(symbology: .code128, enabled: true)
        settings.set(symbology: .code39, enabled: true)

        barcodeCount = BarcodeCount(context: context, settings: settings)
        barcodeCount.addListener(self)

        // The BarcodeCountView is the built-in AR counting UI. It does NOT add itself.
        barcodeCountView = BarcodeCountView(frame: view.bounds,
                                            context: context,
                                            barcodeCount: barcodeCount)
        barcodeCountView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(barcodeCountView)

        barcodeCountView.uiDelegate = self
    }
}

extension ScanViewController: BarcodeCountListener {
    func barcodeCount(_ barcodeCount: BarcodeCount,
                      didScanIn session: BarcodeCountSession,
                      frameData: FrameData) {
        // The session is only valid inside this callback — copy out what you need now.
        let recognizedBarcodes = session.recognizedBarcodes
        // Invoked on an internal recognition thread; hop to main before touching app state.
        DispatchQueue.main.async {
            self.allRecognizedBarcodes = recognizedBarcodes
        }
    }
}

extension ScanViewController: BarcodeCountViewUIDelegate {
    func listButtonTapped(for view: BarcodeCountView) {
        // Present a list of allRecognizedBarcodes (counting still in progress).
    }

    func exitButtonTapped(for view: BarcodeCountView) {
        // The user finished — present a summary / complete the scanning.
    }
}
