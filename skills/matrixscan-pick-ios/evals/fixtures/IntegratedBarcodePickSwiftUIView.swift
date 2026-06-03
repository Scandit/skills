import SwiftUI
import ScanditBarcodeCapture

struct ScanView: View {
    var body: some View {
        PickViewControllerRepresentable()
            .ignoresSafeArea()
    }
}

struct PickViewControllerRepresentable: UIViewControllerRepresentable {
    func makeUIViewController(context: Context) -> PickViewController {
        PickViewController()
    }

    func updateUIViewController(_ uiViewController: PickViewController, context: Context) {}
}

// The shape your product data takes before it is turned into BarcodePickProducts.
// Replace with your real model / data source.
struct ProductDatabaseEntry {
    let identifier: String
    let quantity: Int
    let items: [String] // the barcode data strings that belong to this product
}

class PickViewController: UIViewController {
    private let context = DataCaptureContext(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
    private var barcodePickView: BarcodePickView!

    // The catalog of products to pick, and which barcode payloads map to each.
    // Replace with your real catalog / data source.
    private let productDatabase: [ProductDatabaseEntry] = [
        .init(identifier: "product_1", quantity: 2, items: ["9783598215438", "9783598215414"]),
        .init(identifier: "product_2", quantity: 3, items: ["9783598215471", "9783598215481"]),
    ]

    override func viewDidLoad() {
        super.viewDidLoad()
        setupPicking()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        barcodePickView.start()
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        barcodePickView.pause()
        if isMovingFromParent {
            barcodePickView.stop()
        }
    }

    private func setupPicking() {
        // 1. Settings + symbologies. The settings start with all symbologies disabled —
        //    enable only the ones the app needs.
        let settings = BarcodePickSettings()
        settings.set(symbology: .ean13UPCA, enabled: true)
        settings.set(symbology: .ean8, enabled: true)
        settings.set(symbology: .upce, enabled: true)
        settings.set(symbology: .code128, enabled: true)

        // 2. Build the set of products to pick.
        var products: Set<BarcodePickProduct> = []
        productDatabase.forEach { entry in
            products.insert(BarcodePickProduct(identifier: entry.identifier,
                                               quantityToPick: entry.quantity))
        }

        // 3. The product provider maps scanned barcode payloads to product identifiers,
        //    asynchronously, via the delegate below.
        let productProvider = BarcodePickAsyncMapperProductProvider(products: products,
                                                                    providerDelegate: self)

        // 4. Create the BarcodePick mode.
        let mode = BarcodePick(context: context,
                               settings: settings,
                               productProvider: productProvider)

        // 5. Create the view. It renders the camera preview and the picking UI.
        let viewSettings = BarcodePickViewSettings()
        barcodePickView = BarcodePickView(frame: view.bounds,
                                          context: context,
                                          barcodePick: mode,
                                          settings: viewSettings)
        barcodePickView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(barcodePickView)

        // 6. Observe scanning lifecycle and the finish button.
        barcodePickView.addListener(self)
        barcodePickView.uiDelegate = self

        // 7. Confirm picks. This is REQUIRED: without an action listener, a tapped item
        //    never transitions to "picked" — the SDK waits for completionHandler(true).
        barcodePickView.addActionListener(self)
    }
}

// Maps the raw barcode payloads the SDK sees to your product identifiers.
extension PickViewController: BarcodePickAsyncMapperProductProviderDelegate {
    func mapItems(_ items: [String],
                  completionHandler: @escaping ([BarcodePickProductProviderCallbackItem]) -> Void) {
        let result: [BarcodePickProductProviderCallbackItem] = items.compactMap { item in
            guard let entry = productDatabase.first(where: { $0.items.contains(item) }) else {
                return nil // unknown item — will be highlighted as not-in-list
            }
            return BarcodePickProductProviderCallbackItem(itemData: item,
                                                          productIdentifier: entry.identifier)
        }
        completionHandler(result)
    }
}

// Scanning lifecycle callbacks (optional — implement only what you need).
extension PickViewController: BarcodePickViewListener {
    func barcodePickViewDidStartScanning(_ view: BarcodePickView) {}
    func barcodePickViewDidFreezeScanning(_ view: BarcodePickView) {}
    func barcodePickViewDidPauseScanning(_ view: BarcodePickView) {}
    func barcodePickViewDidStopScanning(_ view: BarcodePickView) {}
}

// The finish button handler.
extension PickViewController: BarcodePickViewUIDelegate {
    func barcodePickViewDidTapFinishButton(_ view: BarcodePickView) {
        // Handle the finish action — e.g. pop, dismiss, present a summary.
        // In SwiftUI, the host typically owns dismissal (e.g. via @Environment(\.dismiss)).
    }
}

// Confirms (or rejects) pick / unpick actions. The completionHandler MUST be called —
// pass true to finalize the action, false to reject it. This is what makes a tapped item
// actually become "picked". A real app might validate against a backend before confirming.
extension PickViewController: BarcodePickActionListener {
    func didPickItem(withData data: String, completionHandler: @escaping (Bool) -> Void) {
        completionHandler(true)
    }

    func didUnpickItem(withData data: String, completionHandler: @escaping (Bool) -> Void) {
        completionHandler(true)
    }
}
