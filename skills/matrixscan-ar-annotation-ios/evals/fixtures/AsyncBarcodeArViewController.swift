import ScanditBarcodeCapture

class ScanViewController: UIViewController {
    private lazy var context = {
        // Enter your Scandit License key here.
        // Your Scandit License key is available via your Scandit SDK web account.
        DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
        return DataCaptureContext.shared
    }()
    private var barcodeAr: BarcodeAr!
    private var barcodeArView: BarcodeArView!
    @IBOutlet weak var containerView: UIView!

    override func viewDidLoad() {
        super.viewDidLoad()
        setupRecognition()

        Task {
            await loadConfiguration()
        }
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        barcodeArView.start()
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        barcodeArView.stop()
    }

    func setupRecognition() {
        let settings = BarcodeArSettings()
        settings.set(symbology: .ean13UPCA, enabled: true)

        barcodeAr = BarcodeAr(context: context, settings: settings)

        let viewSettings = BarcodeArViewSettings()
        let recommendedCameraSettings = BarcodeAr.recommendedCameraSettings

        barcodeArView = BarcodeArView(
            parentView: containerView,
            barcodeAr: barcodeAr,
            settings: viewSettings,
            cameraSettings: recommendedCameraSettings
        )
    }

    private func loadConfiguration() async {
        // Simulated async setup work that establishes the async style of this file.
        try? await Task.sleep(nanoseconds: 1)
    }
}
