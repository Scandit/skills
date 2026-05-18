//
//  AVFoundationViewController.swift
//
//  Source fixture: AVFoundation AVCaptureMetadataOutput-based barcode scanner.
//  Used as input for third-party-migration eval — migrate this to BarcodeCapture.
//

import UIKit
import AVFoundation

struct ScannedBarcode {
    let value: String
    let symbology: String
}

class ViewController: UIViewController {

    private let session = AVCaptureSession()
    private var previewLayer: AVCaptureVideoPreviewLayer!

    private(set) var scannedBarcodes: [ScannedBarcode] = []

    @IBOutlet weak var resultLabel: UILabel!

    override func viewDidLoad() {
        super.viewDidLoad()
        setupCamera()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        if !session.isRunning {
            DispatchQueue.global(qos: .userInitiated).async {
                self.session.startRunning()
            }
        }
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        if session.isRunning {
            session.stopRunning()
        }
    }

    private func setupCamera() {
        guard let videoDevice = AVCaptureDevice.default(for: .video),
              let videoInput = try? AVCaptureDeviceInput(device: videoDevice),
              session.canAddInput(videoInput) else {
            print("Camera not available")
            return
        }
        session.addInput(videoInput)

        let metadataOutput = AVCaptureMetadataOutput()
        guard session.canAddOutput(metadataOutput) else {
            print("Cannot add metadata output")
            return
        }
        session.addOutput(metadataOutput)

        metadataOutput.setMetadataObjectsDelegate(self, queue: .main)
        metadataOutput.metadataObjectTypes = [.ean13, .code128, .qr]

        previewLayer = AVCaptureVideoPreviewLayer(session: session)
        previewLayer.frame = view.layer.bounds
        previewLayer.videoGravity = .resizeAspectFill
        view.layer.addSublayer(previewLayer)
    }
}

extension ViewController: AVCaptureMetadataOutputObjectsDelegate {
    func metadataOutput(_ output: AVCaptureMetadataOutput,
                        didOutput metadataObjects: [AVMetadataObject],
                        from connection: AVCaptureConnection) {
        guard let readable = metadataObjects.first as? AVMetadataMachineReadableCodeObject,
              let value = readable.stringValue else { return }

        let symbology = readable.type.rawValue
        let alreadyScanned = scannedBarcodes.contains { $0.value == value }
        guard !alreadyScanned else { return }

        let entry = ScannedBarcode(value: value, symbology: symbology)
        scannedBarcodes.append(entry)
        resultLabel.text = "Last scan: \(value) (\(scannedBarcodes.count) total)"
    }
}
