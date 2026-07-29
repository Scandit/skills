import UIKit
import ScanditBarcodeCapture

class ViewController: UIViewController {

    private lazy var context = {
        // Enter your Scandit License key here.
        // Your Scandit License key is available via your Scandit SDK web account.
        return DataCaptureContext(licenseKey:  "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
    }()

    private lazy var sparkScan: SparkScan = {
        let settings = SparkScanSettings()
        settings.set(symbology: .ean13UPCA, enabled: true)
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

        let viewSettings = SparkScanViewSettings()
        viewSettings.defaultHandMode = .right

        sparkScanView = SparkScanView(
            parentView: view,
            context: context,
            sparkScan: sparkScan,
            settings: viewSettings
        )

        sparkScanView.isTorchButtonVisible = true
        sparkScanView.captureButtonBackgroundColor = .blue
        sparkScanView.captureButtonTintColor = .white
        sparkScanView.captureButtonActiveBackgroundColor = .darkGray
        sparkScanView.isHandModeButtonVisible = false
        sparkScanView.isSoundModeButtonVisible = true
        sparkScanView.isHapticModeButtonVisible = true
        sparkScanView.stopCapturingText = "Stop"
        sparkScanView.startCapturingText = "Scan"
        sparkScanView.resumeCapturingText = "Resume"
        sparkScanView.scanningCapturingText = "Scanning..."
        sparkScanView.shouldShowScanAreaGuides = true
        sparkScanView.isFastFindButtonVisible = false
    }
}

extension ViewController: SparkScanListener {
    func sparkScan(_ sparkScan: SparkScan, didScanIn session: SparkScanSession, frameData: FrameData?) {
        guard let barcode = session.newlyRecognizedBarcode, let data = barcode.data else { return }
        DispatchQueue.main.async {
            print("Scanned barcode - \(data)")
            // Handle the barcode
        }
    }
}
