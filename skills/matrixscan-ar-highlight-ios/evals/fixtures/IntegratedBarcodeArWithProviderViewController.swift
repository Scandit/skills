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
        settings.set(symbology: .code128, enabled: true)

        barcodeAr = BarcodeAr(context: context, settings: settings)

        let viewSettings = BarcodeArViewSettings()
        let recommendedCameraSettings = BarcodeAr.recommendedCameraSettings

        barcodeArView = BarcodeArView(
            parentView: containerView,
            barcodeAr: barcodeAr,
            settings: viewSettings,
            cameraSettings: recommendedCameraSettings
        )
        barcodeArView.highlightProvider = self
    }
}

extension ScanViewController: BarcodeArHighlightProvider {
    func highlight(
        for barcode: Barcode,
        completionHandler: @escaping ((any UIView & BarcodeArHighlight)?) -> Void
    ) {
        let highlight = BarcodeArRectangleHighlight(barcode: barcode)
        completionHandler(highlight)
    }
}
