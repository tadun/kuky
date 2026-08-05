import SwiftUI

@main
struct KukyAppApp: App {
    @State private var client = RobotClient()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(client)
                .preferredColorScheme(.dark)
        }
    }
}
