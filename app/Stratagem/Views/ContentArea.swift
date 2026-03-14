import SwiftUI

struct ContentArea: View {
    @ObservedObject var viewModel: ResearchViewModel
    @ObservedObject var backendManager: BackendManager
    var currentThreadId: String?

    var body: some View {
        VStack(spacing: 0) {
            // Flow diagram area
            FlowDiagramView(
                activeAgents: viewModel.activeAgents,
                completedAgents: viewModel.completedAgents,
                isRunning: viewModel.state.isRunning
            )
            .frame(height: 180)
            .padding(.horizontal, Theme.Spacing.md)
            .padding(.top, Theme.Spacing.md)

            // Divider
            Rectangle()
                .fill(Theme.Color.border)
                .frame(height: 1)
                .padding(.horizontal, Theme.Spacing.md)

            // Output
            OutputView(text: viewModel.outputText, state: viewModel.state)
                .padding(.horizontal, Theme.Spacing.md)

            // Query input at bottom
            QueryInputView(
                viewModel: viewModel,
                onRun: {
                    viewModel.run(
                        baseURL: backendManager.baseURL,
                        threadId: currentThreadId
                    )
                },
                onStop: {
                    viewModel.stop()
                }
            )
        }
        .background(Theme.Color.background)
    }
}
