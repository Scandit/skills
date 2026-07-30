//
//  VisionViewController.swift
//
//  Source fixture: Apple VisionKit DataScannerViewController-based barcode scanner.
//  Used as input for third-party-migration eval — migrate this to SparkScan.
//

import UIKit
import VisionKit
import Vision

struct ScannedBarcode {
    let value: String
    let symbology: String
}

class ViewController: UIViewController {

    private var scannerPresented = false
    private(set) var scannedBarcodes: [ScannedBarcode] = []

    override func viewDidLoad() {
        super.viewDidLoad()
    }

    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        guard !scannerPresented else { return }
        scannerPresented = true
        startScanner()
    }

    private func showAlert(_ title: String, _ message: String) {
        let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .default))
        present(alert, animated: true)
    }

    private func startScanner() {
        guard DataScannerViewController.isSupported else {
            showAlert("Not Supported", "DataScanner is not supported on this device.")
            return
        }
        guard DataScannerViewController.isAvailable else {
            showAlert("Not Available", "Camera access may be denied. Check Settings > Privacy > Camera.")
            return
        }

        let scanner = DataScannerViewController(
            recognizedDataTypes: [
                .barcode(symbologies: [.ean13, .code128, .qr])
            ],
            isHighlightingEnabled: true
        )
        scanner.delegate = self
        present(scanner, animated: true) {
            try? scanner.startScanning()
        }
    }
}

extension ViewController: DataScannerViewControllerDelegate {
    func dataScanner(_ dataScanner: DataScannerViewController,
                     didTapOn item: RecognizedItem) {
        if case .barcode(let barcode) = item {
            print("Tapped barcode: \(barcode.payloadStringValue ?? ""), symbology: \(barcode.observation.symbology.rawValue)")
        }
    }

    func dataScanner(_ dataScanner: DataScannerViewController,
                     didAdd addedItems: [RecognizedItem],
                     allItems: [RecognizedItem]) {
        for item in addedItems {
            if case .barcode(let barcode) = item,
               let value = barcode.payloadStringValue {
                let symbology = barcode.observation.symbology.rawValue
                let alreadyScanned = scannedBarcodes.contains { $0.value == value }
                guard !alreadyScanned else { continue }
                let entry = ScannedBarcode(value: value, symbology: symbology)
                scannedBarcodes.append(entry)
                print("Saved [\(scannedBarcodes.count)]: \(value) (\(symbology))")
            }
        }
    }
}
