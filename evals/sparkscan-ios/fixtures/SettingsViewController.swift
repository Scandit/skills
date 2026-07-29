import UIKit

class SettingsViewController: UIViewController {

    @IBOutlet weak var tableView: UITableView!

    private var settings: [String] = ["Account", "Notifications", "About"]

    override func viewDidLoad() {
        super.viewDidLoad()
        tableView.dataSource = self
        title = "Settings"
    }
}

extension SettingsViewController: UITableViewDataSource {
    func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        return settings.count
    }

    func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = tableView.dequeueReusableCell(withIdentifier: "Cell", for: indexPath)
        cell.textLabel?.text = settings[indexPath.row]
        return cell
    }
}
