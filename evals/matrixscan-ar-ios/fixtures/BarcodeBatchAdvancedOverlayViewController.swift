//
// Based on MatrixScanBubblesSample (Apache License 2.0).
// StockOverlay (a custom UIView) and StockModel are user-owned types defined elsewhere in the project.
//

import ScanditBarcodeCapture
import UIKit

class ScanViewController: UIViewController {

    private enum Constants {
        static let barcodeToScreenTresholdRation: CGFloat = 0.1
        static let shelfCount = 4
        static let backRoomCount = 8
    }

    private lazy var context = {
        DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
        return DataCaptureContext.shared
    }()
    private var camera: Camera?
    private var barcodeBatch: BarcodeBatch!
    private var captureView: DataCaptureView!
    private var overlay: BarcodeBatchBasicOverlay!
    private var advancedOverlay: BarcodeBatchAdvancedOverlay!

    private var overlays: [Int: StockOverlay] = [:]

    override func viewDidLoad() {
        super.viewDidLoad()
        setupRecognition()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        unfreeze()
    }

    override func viewDidDisappear(_ animated: Bool) {
        super.viewDidDisappear(animated)
        freeze()
    }

    private func setupRecognition() {
        camera = Camera.default
        context.setFrameSource(camera, completionHandler: nil)

        let cameraSettings = BarcodeBatch.recommendedCameraSettings
        cameraSettings.preferredResolution = .uhd4k
        camera?.apply(cameraSettings, completionHandler: nil)

        let settings = BarcodeBatchSettings()
        settings.set(symbology: .ean13UPCA, enabled: true)
        settings.set(symbology: .ean8, enabled: true)
        settings.set(symbology: .upce, enabled: true)
        settings.set(symbology: .code39, enabled: true)
        settings.set(symbology: .code128, enabled: true)

        barcodeBatch = BarcodeBatch(context: context, settings: settings)
        barcodeBatch.addListener(self)

        captureView = DataCaptureView(context: context, frame: view.bounds)
        captureView.context = context
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(captureView)
        view.sendSubviewToBack(captureView)

        overlay = BarcodeBatchBasicOverlay(barcodeBatch: barcodeBatch, view: captureView, style: .dot)

        advancedOverlay = BarcodeBatchAdvancedOverlay(barcodeBatch: barcodeBatch, view: captureView)
        advancedOverlay.delegate = self
    }

    private func freeze() {
        barcodeBatch.isEnabled = false
        camera?.switch(toDesiredState: .off)
    }

    private func unfreeze() {
        barcodeBatch.isEnabled = true
        camera?.switch(toDesiredState: .on)
    }

    private func stockOverlay(for trackedCode: TrackedBarcode) -> StockOverlay {
        let identifier = trackedCode.identifier
        var overlay: StockOverlay
        if overlays.keys.contains(identifier), let existingOverlay = overlays[identifier] {
            overlay = existingOverlay
        } else {
            overlay = StockOverlay(
                with: StockModel(
                    shelfCount: Constants.shelfCount,
                    backroomCount: Constants.backRoomCount,
                    barcodeData: trackedCode.barcode.data
                )
            )
            overlays[identifier] = overlay
        }
        overlay.isHidden = !canShowOverlay(of: trackedCode)
        return overlay
    }

    private func canShowOverlay(of trackedCode: TrackedBarcode) -> Bool {
        let captureViewWidth = captureView.frame.width
        let width = trackedCode.location.width(in: captureView)
        return (width / captureViewWidth) >= Constants.barcodeToScreenTresholdRation
    }
}

extension ScanViewController: BarcodeBatchListener {
    func barcodeBatch(
        _ barcodeBatch: BarcodeBatch,
        didUpdate session: BarcodeBatchSession,
        frameData: FrameData
    ) {
        let removedTrackedBarcodes = session.removedTrackedBarcodes
        let trackedBarcodes = session.trackedBarcodes.values
        DispatchQueue.main.async {
            if !self.barcodeBatch.isEnabled {
                return
            }
            for identifier in removedTrackedBarcodes {
                self.overlays.removeValue(forKey: identifier)
            }
            for trackedCode in trackedBarcodes {
                guard let code = trackedCode.barcode.data, !code.isEmpty else {
                    return
                }
                self.overlays[trackedCode.identifier]?.isHidden = !self.canShowOverlay(of: trackedCode)
            }
        }
    }
}

extension ScanViewController: BarcodeBatchAdvancedOverlayDelegate {
    func barcodeBatchAdvancedOverlay(
        _ overlay: BarcodeBatchAdvancedOverlay,
        viewFor trackedBarcode: TrackedBarcode
    ) -> UIView? {
        stockOverlay(for: trackedBarcode)
    }

    func barcodeBatchAdvancedOverlay(
        _ overlay: BarcodeBatchAdvancedOverlay,
        anchorFor trackedBarcode: TrackedBarcode
    ) -> Anchor {
        .topCenter
    }

    func barcodeBatchAdvancedOverlay(
        _ overlay: BarcodeBatchAdvancedOverlay,
        offsetFor trackedBarcode: TrackedBarcode
    ) -> PointWithUnit {
        PointWithUnit(
            x: FloatWithUnit(value: 0, unit: .fraction),
            y: FloatWithUnit(value: -1, unit: .fraction)
        )
    }
}
