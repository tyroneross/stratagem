import SwiftUI

@MainActor
class ResearchViewModel: ObservableObject {
    @Published var query = ""
    @Published var selectedModel = "opus"
    @Published var state: ResearchState = .idle
    @Published var outputText = ""
    @Published var activeAgents: Set<String> = []
    @Published var completedAgents: Set<String> = []

    private let sseClient = SSEClient()
    private var streamTask: Task<Void, Never>?

    let availableModels = ["opus", "sonnet", "haiku"]

    var canRun: Bool {
        !query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !state.isRunning
    }

    func run(baseURL: String, threadId: String? = nil) {
        guard canRun else { return }

        state = .running
        outputText = ""
        activeAgents = []
        completedAgents = []

        let encodedPrompt = query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? query
        var urlString = "\(baseURL)/api/research?prompt=\(encodedPrompt)&model=\(selectedModel)"
        if let threadId = threadId {
            urlString += "&thread_id=\(threadId)"
        }

        guard let url = URL(string: urlString) else {
            state = .error("Invalid URL")
            return
        }

        streamTask = Task {
            do {
                let stream = await sseClient.stream(url: url)
                for try await event in stream {
                    handleEvent(event)
                }
                // If we got here without a done event, mark complete
                if state.isRunning {
                    state = .complete(turns: 0, durationMs: 0, cost: nil)
                }
            } catch {
                if !Task.isCancelled {
                    state = .error(error.localizedDescription)
                }
            }
        }
    }

    func stop() {
        streamTask?.cancel()
        streamTask = nil
        Task {
            await sseClient.cancel()
        }
        if state.isRunning {
            state = .idle
        }
    }

    func reset() {
        query = ""
        outputText = ""
        state = .idle
        activeAgents = []
        completedAgents = []
    }

    private func handleEvent(_ event: SSEEvent) {
        switch event {
        case .text(let content):
            outputText += content
        case .agentStart(let name, _, _):
            activeAgents.insert(name)
            completedAgents.remove(name)
        case .agentEnd(let name):
            activeAgents.remove(name)
            completedAgents.insert(name)
        case .tool:
            break // Tool events handled by flow diagram
        case .done(let turns, let durationMs, let cost):
            activeAgents.removeAll()
            // Mark all known agents as completed
            for agent in AgentNode.allAgents {
                completedAgents.insert(agent.id)
            }
            state = .complete(turns: turns, durationMs: durationMs, cost: cost)
        case .error(let message):
            state = .error(message)
        }
    }
}
