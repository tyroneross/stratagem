import Foundation

enum ResearchState: Equatable {
    case idle
    case running
    case complete(turns: Int, durationMs: Int, cost: String?)
    case error(String)

    var isRunning: Bool {
        if case .running = self { return true }
        return false
    }
}
