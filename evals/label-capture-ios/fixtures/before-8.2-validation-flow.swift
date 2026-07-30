import ScanditBarcodeCapture
import ScanditLabelCapture
import UIKit

class ScanViewController: UIViewController {
    private var context: DataCaptureContext!
    private var camera: Camera?
    private var labelCapture: LabelCapture!
    private var captureView: DataCaptureView!
    private var validationFlowOverlay: LabelCaptureValidationFlowOverlay!

    @IBOutlet weak var containerView: UIView!

    override func viewDidLoad() {
        super.viewDidLoad()
        try? setupRecognition()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        camera?.switch(toDesiredState: .on)
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        camera?.switch(toDesiredState: .off)
    }

    private func setupRecognition() throws {
        let settings = try LabelCaptureSettings {
            LabelDefinition("Perishable Product") {
                CustomBarcode(name: "Barcode", symbologies: [.ean13UPCA])
                ExpiryDateText(name: "Expiry Date")
            }
        }

        DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
        context = DataCaptureContext.shared

        camera = Camera.default
        context.setFrameSource(camera, completionHandler: nil)
        camera?.apply(LabelCapture.recommendedCameraSettings)

        labelCapture = LabelCapture(context: context, settings: settings)

        captureView = DataCaptureView(context: context, frame: containerView.bounds)
        captureView.autoresizingMask = [.flexibleHeight, .flexibleWidth]
        containerView.insertSubview(captureView, at: 0)

        validationFlowOverlay = LabelCaptureValidationFlowOverlay(
            labelCapture: labelCapture,
            view: captureView
        )
        validationFlowOverlay.delegate = self
    }
}

extension ScanViewController: LabelCaptureValidationFlowDelegate {
    func labelCaptureValidationFlowOverlay(
        _ overlay: LabelCaptureValidationFlowOverlay,
        didCaptureLabelWith fields: [LabelField]
    ) {
        // Handle captured fields
    }
}
