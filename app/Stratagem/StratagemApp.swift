import SwiftUI

@main
struct StratagemApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            Group {
                if appState.isConfigured {
                    MainView()
                } else {
                    SetupView()
                }
            }
            .environmentObject(appState)
            .frame(minWidth: 1200, minHeight: 720)
        }
        .windowResizability(.contentMinSize)
        .defaultSize(width: 1200, height: 720)
        .commands {
            CommandGroup(replacing: .newItem) {}
        }
    }
}

@MainActor
class AppState: ObservableObject {
    @Published var isConfigured: Bool

    init() {
        self.isConfigured = UserDefaults.standard.string(forKey: "pythonPath") != nil
    }

    func markConfigured() {
        isConfigured = true
    }
}
