//
//  AVFoundationViewController.swift
//
//  Source fixture: an AVFoundation AVCaptureMetadataOutput multi-barcode scanner
//  that accumulates every barcode it sees into a dedup-by-value list.
//  Used as input for the third-party-migration eval — migrate this to MatrixScan
//  Batch (BarcodeBatch), which tracks every visible barcode simultaneously.
//

import UIKit
import AVFoundation

struct ScannedBarcode: Hashable {
    let value: String
    let symbology: String
}

class ViewController: UIViewController {

    private let session = AVCaptureSession()
    private var previewLayer: AVCaptureVideoPreviewLayer!

    // Accumulated, de-duplicated set of everything seen so far.
    private(set) var scannedBarcodes: [ScannedBarcode] = []
    private var seenValues = Set<String>()

    @IBOutlet weak var countLabel: UILabel!

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
        // Multi-barcode: every type we care about, tracked at once.
        metadataOutput.metadataObjectTypes = [.ean13, .code128, .qr]

        previewLayer = AVCaptureVideoPreviewLayer(session: session)
        previewLayer.frame = view.layer.bounds
        previewLayer.videoGravity = .resizeAspectFill
        view.layer.addSublayer(previewLayer)
    }

    private func symbologyName(for type: AVMetadataObject.ObjectType) -> String {
        switch type {
        case .ean13: return "EAN-13"
        case .code128: return "Code 128"
        case .qr: return "QR"
        default: return "Unknown"
        }
    }
}

extension ViewController: AVCaptureMetadataOutputObjectsDelegate {
    func metadataOutput(_ output: AVCaptureMetadataOutput,
                        didOutput metadataObjects: [AVMetadataObject],
                        from connection: AVCaptureConnection) {
        // AVFoundation reports every barcode in frame on each callback.
        for object in metadataObjects {
            guard let readable = object as? AVMetadataMachineReadableCodeObject,
                  let value = readable.stringValue else { continue }

            guard !seenValues.contains(value) else { continue }
            seenValues.insert(value)

            let entry = ScannedBarcode(value: value, symbology: symbologyName(for: readable.type))
            scannedBarcodes.append(entry)
        }
        countLabel.text = "\(scannedBarcodes.count) unique barcodes"
    }
}
