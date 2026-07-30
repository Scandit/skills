//
// Based on MatrixScanARSimpleSample (Apache License 2.0).
//

import ScanditBarcodeCapture

class ScanViewController: UIViewController {
    private lazy var context = {
        DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
        return DataCaptureContext.shared
    }()
    private var barcodeAr: BarcodeAr!
    private var barcodeArView: BarcodeArView!

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
        settings.set(symbology: .ean8, enabled: true)
        settings.set(symbology: .upce, enabled: true)
        settings.set(symbology: .code39, enabled: true)
        settings.set(symbology: .code128, enabled: true)

        barcodeAr = BarcodeAr(context: context, settings: settings)

        let viewSettings = BarcodeArViewSettings()
        let recommendedCameraSettings = BarcodeAr.recommendedCameraSettings

        barcodeArView = BarcodeArView(
            parentView: view,
            barcodeAr: barcodeAr,
            settings: viewSettings,
            cameraSettings: recommendedCameraSettings
        )
    }
}
