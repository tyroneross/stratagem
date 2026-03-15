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
        // Validate stored python path is an actual file — handles migration
        // from old config ("uv run python") and broken venvs
        if let path = UserDefaults.standard.string(forKey: "pythonPath"),
            FileManager.default.fileExists(atPath: path)
        {
            self.isConfigured = true
        } else {
            UserDefaults.standard.removeObject(forKey: "pythonPath")
            self.isConfigured = false
        }
    }

    func markConfigured() {
        isConfigured = true
    }
}
