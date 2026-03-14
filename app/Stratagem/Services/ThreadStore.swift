import Foundation

@MainActor
class ThreadStore: ObservableObject {
    @Published var threads: [ResearchThread] = []
    @Published var isLoading = false

    private var refreshTask: Task<Void, Never>?

    func fetchThreads(baseURL: String) {
        refreshTask?.cancel()
        refreshTask = Task {
            isLoading = true
            defer { isLoading = false }

            guard let url = URL(string: "\(baseURL)/api/threads") else { return }

            do {
                let (data, response) = try await URLSession.shared.data(from: url)
                guard let httpResponse = response as? HTTPURLResponse,
                      httpResponse.statusCode == 200 else { return }

                let decoder = JSONDecoder()
                let fetchedThreads = try decoder.decode([ResearchThread].self, from: data)

                if !Task.isCancelled {
                    // Sort by most recent first
                    threads = fetchedThreads.sorted { $0.lastActive > $1.lastActive }
                }
            } catch {
                // Silently fail — threads are non-critical
            }
        }
    }
}
