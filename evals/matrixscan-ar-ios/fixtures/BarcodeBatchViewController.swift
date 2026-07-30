//
// Based on MatrixScanSimpleSample (Apache License 2.0).
//

import ScanditBarcodeCapture

class ScannerViewController: UIViewController {

    private lazy var context = {
        DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
        return DataCaptureContext.shared
    }()
    private var camera: Camera?
    private var barcodeBatch: BarcodeBatch!
    private var captureView: DataCaptureView!
    private var overlay: BarcodeBatchBasicOverlay!

    private var results: [String: Barcode] = [:]

    override func viewDidLoad() {
        super.viewDidLoad()
        self.title = "MatrixScan Simple"
        setupRecognition()
        startTracking()
    }

    override func prepare(for segue: UIStoryboardSegue, sender: Any?) {
        guard let resultsViewController = segue.destination as? ResultViewController else {
            return
        }
        resultsViewController.codes = Array(results.values)
        stopTracking()
    }

    @IBAction func unwindToScanner(segue: UIStoryboardSegue) {
        startTracking()
    }

    private func startTracking() {
        results.removeAll()
        barcodeBatch.isEnabled = true
        camera?.switch(toDesiredState: .on)
    }

    private func stopTracking() {
        barcodeBatch.isEnabled = false
        camera?.switch(toDesiredState: .off)
    }

    private func setupRecognition() {
        camera = Camera.default
        context.setFrameSource(camera, completionHandler: nil)

        let cameraSettings = BarcodeBatch.recommendedCameraSettings
        cameraSettings.preferredResolution = .fullHD
        camera?.apply(cameraSettings, completionHandler: nil)

        let settings = BarcodeBatchSettings()
        settings.set(symbology: .ean13UPCA, enabled: true)
        settings.set(symbology: .ean8, enabled: true)
        settings.set(symbology: .upce, enabled: true)
        settings.set(symbology: .code39, enabled: true)
        settings.set(symbology: .code128, enabled: true)

        barcodeBatch = BarcodeBatch(context: context, settings: settings)
        barcodeBatch.addListener(self)

        captureView = DataCaptureView(context: context, frame: view.bounds)
        captureView.context = context
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(captureView)
        view.sendSubviewToBack(captureView)

        overlay = BarcodeBatchBasicOverlay(barcodeBatch: barcodeBatch, view: captureView, style: .frame)
    }
}

extension ScannerViewController: BarcodeBatchListener {
    func barcodeBatch(
        _ barcodeBatch: BarcodeBatch,
        didUpdate session: BarcodeBatchSession,
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
