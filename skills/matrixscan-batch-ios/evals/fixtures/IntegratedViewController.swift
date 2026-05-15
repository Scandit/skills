import ScanditBarcodeCapture
import UIKit

class ScanViewController: UIViewController {

    private lazy var context: DataCaptureContext = {
        DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
        return DataCaptureContext.shared
    }()
    private var camera: Camera?
    private var barcodeBatch: BarcodeBatch!
    private var captureView: DataCaptureView!
    private var overlay: BarcodeBatchBasicOverlay!

    override func viewDidLoad() {
        super.viewDidLoad()
        setupRecognition()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        barcodeBatch.isEnabled = true
        camera?.switch(toDesiredState: .on)
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        barcodeBatch.isEnabled = false
        camera?.switch(toDesiredState: .off)
    }

    private func setupRecognition() {
        camera = Camera.default
        context.setFrameSource(camera, completionHandler: nil)

        let cameraSettings = BarcodeBatch.recommendedCameraSettings
        camera?.apply(cameraSettings, completionHandler: nil)

        let settings = BarcodeBatchSettings()
        settings.set(symbology: .ean13UPCA, enabled: true)
        settings.set(symbology: .code128, enabled: true)

        barcodeBatch = BarcodeBatch(context: context, settings: settings)
        barcodeBatch.addListener(self)

        captureView = DataCaptureView(context: context, frame: view.bounds)
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(captureView)

        overlay = BarcodeBatchBasicOverlay(barcodeBatch: barcodeBatch, view: captureView)
    }
}

extension ScanViewController: BarcodeBatchListener {

    func barcodeBatch(
        _ barcodeBatch: BarcodeBatch,
        didUpdate session: BarcodeBatchSession,
        frameData: FrameData
    ) {
        let addedData = session.addedTrackedBarcodes.compactMap { $0.barcode.data }
        DispatchQueue.main.async {
            for data in addedData {
                _ = data
            }
        }
    }
}
