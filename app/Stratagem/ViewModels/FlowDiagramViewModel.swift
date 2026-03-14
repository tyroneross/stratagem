import SwiftUI
import Combine

@MainActor
class FlowDiagramViewModel: ObservableObject {
    @Published var nodes: [AgentNode] = AgentNode.allAgents

    func activateAgent(_ name: String) {
        if let index = nodes.firstIndex(where: { $0.id == name }) {
            nodes[index].state = .active
        }
    }

    func completeAgent(_ name: String) {
        if let index = nodes.firstIndex(where: { $0.id == name }) {
            nodes[index].state = .completed
        }
    }

    func completeAll() {
        for i in nodes.indices {
            if nodes[i].state != .completed {
                nodes[i].state = .completed
            }
        }
    }

    func reset() {
        for i in nodes.indices {
            nodes[i].state = .idle
        }
    }

    func updateFromSets(active: Set<String>, completed: Set<String>) {
        for i in nodes.indices {
            if active.contains(nodes[i].id) {
                nodes[i].state = .active
            } else if completed.contains(nodes[i].id) {
                nodes[i].state = .completed
            } else {
                nodes[i].state = .idle
            }
        }
    }
}
