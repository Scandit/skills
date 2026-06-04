import UIKit
import ScanditBarcodeCapture

// One entry per product the scanner can RECOGNIZE: its identifier and the barcode payloads that
// map to it. Replace with your real model / data source once the product list is available.
struct ProductDatabaseEntry {
    let identifier: String
    let items: [String] // the barcode data strings that belong to this product
}

class ScanViewController: UIViewController {


    private let context = DataCaptureContext(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
    private var barcodePickView: BarcodePickView!

    // The product database: everything the scanner can recognize (barcode payload → product id).
    // It can list more than the user is asked to pick. Placeholder data — replace with the real list.
    private let productDatabase: [ProductDatabaseEntry] = [
        .init(identifier: "product_1", items: ["9783598215438", "9783598215414"]),
        .init(identifier: "product_2", items: ["9783598215471", "9783598215481"]),
        // In the database but not in `productsToPick` → resolves to .ignore (still tappable, just not
        // highlighted or counted). Drop this line if you don't want users to interact with it.
        .init(identifier: "product_3", items: ["9783598215498"]),
    ]

    // The subset the user must actually pick, each with a target quantity → highlighted (.toPick)
    // and counted. Every identifier here must exist in productDatabase above.
    private let productsToPick: [BarcodePickProduct] = [
        BarcodePickProduct(identifier: "product_1", quantityToPick: 2),
        BarcodePickProduct(identifier: "product_2", quantityToPick: 3),
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
        //    enable only the ones the app needs. These are a reasonable default retail set;
        //    trim to only what you actually scan once the real symbology list is known
        //    (fewer enabled symbologies improves scanning performance and accuracy).
        let settings = BarcodePickSettings()
        settings.set(symbology: .ean13UPCA, enabled: true)
        settings.set(symbology: .ean8, enabled: true)
        settings.set(symbology: .upce, enabled: true)
        settings.set(symbology: .code128, enabled: true)
        settings.set(symbology: .code39, enabled: true)

        // 2. The pick list is the products-to-pick subset (a Set of BarcodePickProduct).
        let products = Set(productsToPick)

        // 3. The product provider maps scanned barcode payloads to product identifiers,
        //    asynchronously, via the delegate below. It resolves against the full database,
        //    so a recognized product that isn't in `products` shows up as .ignore.
        let productProvider = BarcodePickAsyncMapperProductProvider(products: products,
                                                                    providerDelegate: self)

        // 4. Create the BarcodePick mode.
        let mode = BarcodePick(context: context,
                               settings: settings,
                               productProvider: productProvider)

        // 5. Observe pick state. Register a scanning listener on the MODE (not the view)
        //    to read picked / scanned items off the session as the user progresses.
        mode.addScanningListener(self)

        // 6. Create the view. It renders the camera preview and the picking UI.
        let viewSettings = BarcodePickViewSettings()
        barcodePickView = BarcodePickView(frame: view.bounds,
                                          context: context,
                                          barcodePick: mode,
                                          settings: viewSettings)
        barcodePickView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(barcodePickView)

        // 7. Observe view-lifecycle events and the finish button.
        barcodePickView.addListener(self)
        barcodePickView.uiDelegate = self

        // 8. Confirm picks. This is REQUIRED: without an action listener, a tapped item
        //    never transitions to "picked" — the SDK waits for completionHandler(true).
        barcodePickView.addActionListener(self)
    }
}

// Maps the raw barcode payloads the SDK sees to your product identifiers.
extension ScanViewController: BarcodePickAsyncMapperProductProviderDelegate {
    func mapItems(_ items: [String],
                  completionHandler: @escaping ([BarcodePickProductProviderCallbackItem]) -> Void) {
        let result: [BarcodePickProductProviderCallbackItem] = items.compactMap { item in
            guard let entry = productDatabase.first(where: { $0.items.contains(item) }) else {
                return nil // not in the database → .unknown (inert; the user can't interact with it)
            }
            return BarcodePickProductProviderCallbackItem(itemData: item,
                                                          productIdentifier: entry.identifier)
        }
        completionHandler(result)
    }
}

// Scanning lifecycle callbacks (optional — implement only what you need).
extension ScanViewController: BarcodePickViewListener {
    func barcodePickViewDidStartScanning(_ view: BarcodePickView) {}
    func barcodePickViewDidFreezeScanning(_ view: BarcodePickView) {}
    func barcodePickViewDidPauseScanning(_ view: BarcodePickView) {}
    func barcodePickViewDidStopScanning(_ view: BarcodePickView) {}
}

// The finish button handler.
extension ScanViewController: BarcodePickViewUIDelegate {
    func barcodePickViewDidTapFinishButton(_ view: BarcodePickView) {
        // Handle the finish action — e.g. pop, dismiss, present a summary.
        // The right call depends on how this screen was presented.
    }
}

// Confirms (or rejects) pick / unpick actions. The completionHandler MUST be called —
// pass true to finalize the action, false to reject it. This is what makes a tapped item
// actually become "picked". A real app might validate against a backend before confirming.
extension ScanViewController: BarcodePickActionListener {
    func didPickItem(withData data: String, completionHandler: @escaping (Bool) -> Void) {
        completionHandler(true)
    }

    func didUnpickItem(withData data: String, completionHandler: @escaping (Bool) -> Void) {
        completionHandler(true)
    }
}

// Observes pick state. session.pickedItems / scannedItems are Set<String> of itemData.
// Callbacks fire OFF the main queue — dispatch to main before touching UIKit.
extension ScanViewController: BarcodePickScanningListener {
    func barcodePick(_ barcodePick: BarcodePick,
                     didUpdate scanningSession: BarcodePickScanningSession) {
        // Called on every pick / unpick — the session state has changed.
        // Update your app's view of progress here.
    }

    func barcodePick(_ barcodePick: BarcodePick,
                     didComplete scanningSession: BarcodePickScanningSession) {
        // Called when the picking session ends — e.g. on view teardown or when the mode is stopped.
        // Use this for end-of-session bookkeeping.
    }
}
