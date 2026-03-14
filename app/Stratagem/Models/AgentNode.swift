import Foundation

enum AgentPhase: String, CaseIterable {
    case planning = "PLAN"
    case execution = "EXECUTE"
    case quality = "QUALITY"
    case delivery = "DELIVER"
}

enum AgentState {
    case idle
    case active
    case completed
}

struct AgentNode: Identifiable {
    let id: String          // e.g. "research-planner"
    let displayName: String // e.g. "Planner"
    let phase: AgentPhase
    let model: String       // "opus" or "sonnet"
    let action: String      // e.g. "planning research approach"
    var state: AgentState = .idle
}

// All agents, ordered by phase then display order
extension AgentNode {
    static let allAgents: [AgentNode] = [
        // PLAN
        AgentNode(id: "research-planner", displayName: "Planner", phase: .planning, model: "sonnet", action: "planning research approach"),
        // EXECUTE
        AgentNode(id: "data-extractor", displayName: "Extractor", phase: .execution, model: "sonnet", action: "extracting data"),
        AgentNode(id: "financial-analyst", displayName: "Financials", phase: .execution, model: "opus", action: "analyzing financials"),
        AgentNode(id: "research-synthesizer", displayName: "Synthesizer", phase: .execution, model: "opus", action: "synthesizing findings"),
        AgentNode(id: "executive-synthesizer", displayName: "Exec Brief", phase: .execution, model: "sonnet", action: "creating executive brief"),
        AgentNode(id: "flowchart-architect", displayName: "Visuals", phase: .execution, model: "sonnet", action: "designing visuals"),
        AgentNode(id: "prompt-optimizer", displayName: "Optimizer", phase: .execution, model: "sonnet", action: "refining prompts"),
        // QUALITY
        AgentNode(id: "plan-validator", displayName: "Validator", phase: .quality, model: "sonnet", action: "checking for drift"),
        AgentNode(id: "source-verifier", displayName: "Verifier", phase: .quality, model: "sonnet", action: "verifying sources"),
        // DELIVER
        AgentNode(id: "report-critic", displayName: "Critic", phase: .delivery, model: "sonnet", action: "evaluating report quality"),
        AgentNode(id: "design-agent", displayName: "Designer", phase: .delivery, model: "sonnet", action: "designing layout"),
    ]

    static func agentsForPhase(_ phase: AgentPhase) -> [AgentNode] {
        allAgents.filter { $0.phase == phase }
    }
}
