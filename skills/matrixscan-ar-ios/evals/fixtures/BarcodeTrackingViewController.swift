//
// Legacy v6-style MatrixScan integration using BarcodeTracking.
//

import ScanditBarcodeCapture

class ScannerViewController: UIViewController {

    private lazy var context = DataCaptureContext(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
    private var camera: Camera?
    private var barcodeTracking: BarcodeTracking!
    private var captureView: DataCaptureView!
    private var overlay: BarcodeTrackingBasicOverlay!

    private var results: [String: Barcode] = [:]

    override func viewDidLoad() {
        super.viewDidLoad()
        self.title = "MatrixScan Simple"
        setupRecognition()
        startTracking()
    }

    private func startTracking() {
        results.removeAll()
        barcodeTracking.isEnabled = true
        camera?.switch(toDesiredState: .on)
    }

    private func stopTracking() {
        barcodeTracking.isEnabled = false
        camera?.switch(toDesiredState: .off)
    }

    private func setupRecognition() {
        camera = Camera.default
        context.setFrameSource(camera, completionHandler: nil)

        let cameraSettings = BarcodeTracking.recommendedCameraSettings
        cameraSettings.preferredResolution = .fullHD
        camera?.apply(cameraSettings, completionHandler: nil)

        let settings = BarcodeTrackingSettings()
        settings.set(symbology: .ean13UPCA, enabled: true)
        settings.set(symbology: .ean8, enabled: true)
        settings.set(symbology: .code39, enabled: true)
        settings.set(symbology: .code128, enabled: true)

        barcodeTracking = BarcodeTracking(context: context, settings: settings)
        barcodeTracking.addListener(self)

        captureView = DataCaptureView(context: context, frame: view.bounds)
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(captureView)
        view.sendSubviewToBack(captureView)

        overlay = BarcodeTrackingBasicOverlay(barcodeTracking: barcodeTracking, view: captureView, style: .frame)
    }
}

extension ScannerViewController: BarcodeTrackingListener {
    func barcodeTracking(
        _ barcodeTracking: BarcodeTracking,
        didUpdate session: BarcodeTrackingSession,
        frameData: FrameData
    ) {
        let barcodes = session.trackedBarcodes.values.compactMap { $0.barcode }
        DispatchQueue.main.async { [weak self] in
            barcodes.forEach {
                if let self = self, let data = $0.data, !data.isEmpty {
                    self.results[data] = $0
                }
            }
        }
    }
}
