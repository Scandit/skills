import SwiftUI

struct EmptySwiftUIView: View {
    var body: some View {
        VStack {
            Text("Barcode Scanner")
                .font(.title)
            Spacer()
        }
        .padding()
    }
}

#Preview {
    EmptySwiftUIView()
}
