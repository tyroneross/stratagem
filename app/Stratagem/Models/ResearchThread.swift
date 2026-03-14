import Foundation

struct ResearchThread: Identifiable, Codable, Equatable {
    let id: String
    var title: String
    var created: String       // ISO timestamp
    var lastActive: String    // ISO timestamp
    var queryCount: Int

    enum CodingKeys: String, CodingKey {
        case id, title, created
        case lastActive = "last_active"
        case queryCount = "query_count"
    }

    var relativeTime: String {
        // Parse ISO date and return relative time
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        guard let date = formatter.date(from: lastActive) ?? ISO8601DateFormatter().date(from: lastActive) else {
            return lastActive
        }
        let interval = Date().timeIntervalSince(date)
        if interval < 60 { return "Just now" }
        if interval < 3600 { return "\(Int(interval / 60))m ago" }
        if interval < 86400 { return "\(Int(interval / 3600))h ago" }
        if interval < 172800 { return "Yesterday" }
        return "\(Int(interval / 86400))d ago"
    }
}
