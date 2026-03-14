import Foundation

enum SSEEvent {
    case text(String)
    case agentStart(name: String, action: String, model: String)
    case agentEnd(name: String)
    case tool(name: String)
    case done(turns: Int, durationMs: Int, cost: String?)
    case error(String)

    static func parse(from jsonData: Data) -> SSEEvent? {
        // Parse JSON, switch on "type" field
        guard let dict = try? JSONSerialization.jsonObject(with: jsonData) as? [String: Any],
              let type = dict["type"] as? String else {
            return nil
        }
        switch type {
        case "text":
            return .text(dict["content"] as? String ?? "")
        case "agent_start":
            return .agentStart(
                name: dict["name"] as? String ?? "",
                action: dict["action"] as? String ?? "",
                model: dict["model"] as? String ?? "sonnet"
            )
        case "agent_end":
            return .agentEnd(name: dict["name"] as? String ?? "")
        case "tool":
            return .tool(name: dict["name"] as? String ?? "")
        case "done":
            return .done(
                turns: dict["turns"] as? Int ?? 0,
                durationMs: dict["duration_ms"] as? Int ?? 0,
                cost: dict["cost"] as? String
            )
        case "error":
            return .error(dict["message"] as? String ?? "Unknown error")
        default:
            return nil
        }
    }
}
