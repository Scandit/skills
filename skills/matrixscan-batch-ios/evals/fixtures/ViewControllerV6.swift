//
//  ViewControllerV6.swift
//
//  Source fixture: a Scandit SDK v6 MatrixScan view controller using the old
//  BarcodeTracking API. Used as input for the version-migration eval —
//  migrate this to the v7+ BarcodeBatch API.
//

import UIKit
import ScanditBarcodeCapture

class ViewController: UIViewController {

    // v6-style context construction (deprecated constructor)
    private let context = DataCaptureContext(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

    private var camera: Camera?
    private var barcodeTracking: BarcodeTracking!
    private var captureView: DataCaptureView!
    private var overlay: BarcodeTrackingBasicOverlay!

    override func viewDidLoad() {
        super.viewDidLoad()

        // v6-style camera setup: explicit CameraSettings with .auto resolution
        let cameraSettings = CameraSettings()
        cameraSettings.preferredResolution = .auto
        camera = Camera.default
        camera?.apply(cameraSettings)
        context.setFrameSource(camera)

        let settings = BarcodeTrackingSettings()
        settings.set(symbology: .ean13UPCA, enabled: true)
        settings.set(symbology: .code128, enabled: true)

        barcodeTracking = BarcodeTracking(context: context, settings: settings)
        barcodeTracking.addListener(self)

        captureView = DataCaptureView(context: context, frame: view.bounds)
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(captureView)

        overlay = BarcodeTrackingBasicOverlay(barcodeTracking: barcodeTracking, view: captureView)
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        barcodeTracking.isEnabled = true
        camera?.switch(toDesiredState: .on)
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        barcodeTracking.isEnabled = false
        camera?.switch(toDesiredState: .off)
    }

    deinit {
        barcodeTracking.removeListener(self)
    }
}

extension ViewController: BarcodeTrackingListener {
    func barcodeTracking(_ barcodeTracking: BarcodeTracking,
                         didUpdate session: BarcodeTrackingSession,
                         frameData: FrameData) {
        let addedData = session.addedTrackedBarcodes.compactMap { $0.barcode.data }
        DispatchQueue.main.async {
            for data in addedData {
                _ = data
            }
        }
    }
}
