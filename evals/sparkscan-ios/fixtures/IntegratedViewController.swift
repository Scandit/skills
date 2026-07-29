import UIKit
import ScanditBarcodeCapture

class ViewController: UIViewController {

    private lazy var context = {
        DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
        return DataCaptureContext.shared
    }()

    private lazy var sparkScan: SparkScan = {
        let settings = SparkScanSettings()
        Set<Symbology>([.ean8, .ean13UPCA, .upce, .code39, .code128, .interleavedTwoOfFive]).forEach {
            settings.set(symbology: $0, enabled: true)
        }
        settings.settings(for: .code39).activeSymbolCounts = Set(7...20)
        return SparkScan(settings: settings)
    }()

    private var sparkScanView: SparkScanView!

    override func viewDidLoad() {
        super.viewDidLoad()
        setupRecognition()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        sparkScanView.prepareScanning()
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        sparkScanView.stopScanning()
    }

    private func setupRecognition() {
        sparkScan.addListener(self)
        sparkScanView = SparkScanView(
            parentView: view,
            context: context,
            sparkScan: sparkScan,
            settings: SparkScanViewSettings()
        )
    }
}

extension ViewController: SparkScanListener {
    func sparkScan(_ sparkScan: SparkScan, didScanIn session: SparkScanSession, frameData: FrameData?) {
        guard let barcode = session.newlyRecognizedBarcode, let data = barcode.data else { return }
        DispatchQueue.main.async {
            print("Scanned: \(data)")
        }
    }
}
