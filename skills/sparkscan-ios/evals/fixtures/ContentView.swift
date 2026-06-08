import SwiftUI

struct ContentView: View {
    @State private var items: [String] = []

    var body: some View {
        NavigationView {
            List(items, id: \.self) { item in
                Text(item)
            }
            .navigationTitle("Inventory")
        }
    }
}

#Preview {
    ContentView()
}
