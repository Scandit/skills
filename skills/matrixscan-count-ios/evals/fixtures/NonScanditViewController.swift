import UIKit

class ScanViewController: UIViewController {

    @IBOutlet private weak var titleLabel: UILabel!

    override func viewDidLoad() {
        super.viewDidLoad()
        titleLabel.text = "Scan a barcode"
    }
}
