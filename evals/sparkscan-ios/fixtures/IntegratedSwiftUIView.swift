import SwiftUI
import ScanditBarcodeCapture

class SparkScanViewController: UIViewController, SparkScanListener {
    private var dataCaptureContext: DataCaptureContext!
    private var sparkScan: SparkScan!
    private var sparkScanView: SparkScanView!

    override func viewDidLoad() {
        super.viewDidLoad()

        DataCaptureContext.initialize(withLicenseKey: "YOUR_LICENSE_KEY")
        dataCaptureContext = DataCaptureContext.shared

        let settings = SparkScanSettings()
        settings.setSymbology(.ean13UPCA, enabled: true)
        settings.setSymbology(.code128, enabled: true)

        sparkScan = SparkScan(settings: settings)
        sparkScan.addListener(self)

        let viewSettings = SparkScanViewSettings()
        sparkScanView = SparkScanView(
            frame: view.bounds,
            dataCaptureContext: dataCaptureContext,
            sparkScan: sparkScan,
            settings: viewSettings
        )

        view.addSubview(sparkScanView)
        sparkScanView.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            sparkScanView.topAnchor.constraint(equalTo: view.topAnchor),
            sparkScanView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            sparkScanView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            sparkScanView.bottomAnchor.constraint(equalTo: view.bottomAnchor)
        ])
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        sparkScanView.prepareScanning()
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        sparkScanView.stopScanning()
    }

    func sparkScan(_ sparkScan: SparkScan, didScanIn session: SparkScanSession, frameData: FrameData?) {
        if let barcode = session.newlyRecognizedBarcode {
            DispatchQueue.main.async {
                // Handle barcode scan
            }
        }
    }
}

struct IntegratedSwiftUIView: View {
    let sparkScanViewController = SparkScanViewController()

    var body: some View {
        ZStack {
            VStack {
                Text("Barcode Scanner")
                    .font(.title)
                    .padding()

                Spacer()
            }
        }
        .withSparkScan(sparkScanViewController)
    }
}

#Preview {
    IntegratedSwiftUIView()
}
