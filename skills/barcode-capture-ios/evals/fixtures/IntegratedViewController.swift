import UIKit
import ScanditBarcodeCapture

class ViewController: UIViewController {

    private lazy var context: DataCaptureContext = {
        DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
        return DataCaptureContext.shared
    }()

    private var camera: Camera?
    private var barcodeCapture: BarcodeCapture!
    private var captureView: DataCaptureView!
    private var overlay: BarcodeCaptureOverlay!

    override func viewDidLoad() {
        super.viewDidLoad()

        camera = Camera.default
        camera?.apply(BarcodeCapture.recommendedCameraSettings)
        context.setFrameSource(camera)

        let settings = BarcodeCaptureSettings()
        settings.set(symbology: .ean13UPCA, enabled: true)
        settings.set(symbology: .code128, enabled: true)

        barcodeCapture = BarcodeCapture(context: context, settings: settings)
        barcodeCapture.addListener(self)

        captureView = DataCaptureView(context: context, frame: view.bounds)
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(captureView)

        overlay = BarcodeCaptureOverlay(barcodeCapture: barcodeCapture, view: captureView)
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        barcodeCapture.isEnabled = true
        camera?.switch(toDesiredState: .on)
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        barcodeCapture.isEnabled = false
        camera?.switch(toDesiredState: .off)
    }

    deinit {
        barcodeCapture.removeListener(self)
        context.removeCurrentMode()
    }
}

extension ViewController: BarcodeCaptureListener {
    func barcodeCapture(_ barcodeCapture: BarcodeCapture,
                        didScanIn session: BarcodeCaptureSession,
                        frameData: FrameData) {
        guard let barcode = session.newlyRecognizedBarcode else { return }
        barcodeCapture.isEnabled = false
        DispatchQueue.main.async {
            // handle barcode.data and barcode.symbology
            _ = barcode
        }
    }
}
