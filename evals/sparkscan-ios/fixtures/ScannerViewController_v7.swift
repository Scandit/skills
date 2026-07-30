import ScanditBarcodeCapture

class ScannerViewController: UIViewController {

    private lazy var context = {
        DataCaptureContext.initialize(licenseKey: "-- LICENSE KEY --")
        return DataCaptureContext.shared
    }()

    private lazy var sparkScan: SparkScan = {
        let settings = SparkScanSettings()
        settings.set(symbology: .ean13UPCA, enabled: true)
        settings.set(symbology: .code128, enabled: true)
        return SparkScan(settings: settings)
    }()

    private var sparkScanView: SparkScanView!

    override func viewDidLoad() {
        super.viewDidLoad()
        setupScanning()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        sparkScanView.prepareScanning()
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        sparkScanView.stopScanning()
    }

    private func setupScanning() {
        sparkScan.addListener(self)

        let viewSettings = SparkScanViewSettings()

        sparkScanView = SparkScanView(
            parentView: view,
            context: context,
            sparkScan: sparkScan,
            settings: viewSettings
        )

        sparkScanView.isTorchControlVisible = true
        sparkScanView.triggerButtonCollapsedColor = .blue
        sparkScanView.triggerButtonExpandedColor = .blue
        sparkScanView.triggerButtonAnimationColor = .blue
        sparkScanView.triggerButtonTintColor = .white
        sparkScanView.isBarcodeFindButtonVisible = false
    }
}

extension ScannerViewController: SparkScanListener {
    func sparkScan(_ sparkScan: SparkScan, didScanIn session: SparkScanSession, frameData: FrameData?) {
        guard let barcode = session.newlyRecognizedBarcode, let data = barcode.data else { return }
        DispatchQueue.main.async {
            print("Scanned: \(data)")
        }
    }
}
