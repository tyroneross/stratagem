import SwiftUI

struct ContentArea: View {
    @ObservedObject var viewModel: ResearchViewModel
    @ObservedObject var backendManager: BackendManager
    var currentThreadId: String?

    var body: some View {
        VStack(spacing: 0) {
            header

            Rectangle()
                .fill(Theme.Color.border)
                .frame(height: 1)

            VStack(alignment: .leading, spacing: Theme.Spacing.md) {
                if !backendManager.isRunning {
                    backendNotice
                }

                flowSection

                outputSection
                    .frame(maxHeight: .infinity)
            }
            .padding(.horizontal, Theme.Spacing.md)
            .padding(.vertical, Theme.Spacing.md)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)

            Rectangle()
                .fill(Theme.Color.border)
                .frame(height: 1)

            QueryInputView(
                viewModel: viewModel,
                isBackendReady: backendManager.isRunning,
                backendError: backendManager.errorMessage,
                onRun: {
                    guard backendManager.isRunning else { return }
                    viewModel.run(baseURL: backendManager.baseURL, threadId: currentThreadId)
                },
                onStop: {
                    viewModel.stop()
                }
            )
        }
        .background(Theme.Color.background)
    }

    private var header: some View {
        HStack(alignment: .center, spacing: Theme.Spacing.md) {
            VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                Text("Research Workspace")
                    .font(Theme.Font.largeTitle)
                    .foregroundStyle(Theme.Color.textPrimary)

                Text(workspaceSubtitle)
                    .font(Theme.Font.caption)
                    .foregroundStyle(Theme.Color.textSecondary)
            }

            Spacer()

            statusPill(
                label: backendStatusLabel,
                systemImage: backendManager.isRunning ? "checkmark.circle.fill" : "clock.fill",
                color: backendStatusColor
            )
        }
        .padding(.horizontal, Theme.Spacing.lg)
        .padding(.vertical, Theme.Spacing.md)
    }

    private var flowSection: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
            sectionHeader(title: "Agent Flow", detail: flowDetail)

            FlowDiagramView(
                activeAgents: viewModel.activeAgents,
                completedAgents: viewModel.completedAgents,
                isRunning: viewModel.state.isRunning
            )
            .frame(height: 156)
            .frame(maxWidth: .infinity)
            .background(Theme.Color.surface)
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .strokeBorder(Theme.Color.border, lineWidth: 1)
            )
            .accessibilityLabel("Agent flow")
        }
    }

    private var outputSection: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
            sectionHeader(title: "Output", detail: outputDetail)

            OutputView(text: viewModel.outputText, state: viewModel.state)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        }
    }

    private var backendNotice: some View {
        HStack(alignment: .top, spacing: Theme.Spacing.sm) {
            Image(systemName: backendManager.errorMessage == nil ? "clock" : "exclamationmark.triangle.fill")
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(backendStatusColor)
                .frame(width: 18)

            VStack(alignment: .leading, spacing: 2) {
                Text(backendManager.errorMessage == nil ? "Starting backend" : "Backend issue")
                    .font(Theme.Font.caption)
                    .fontWeight(.semibold)
                    .foregroundStyle(Theme.Color.textPrimary)

                Text(backendManager.errorMessage ?? "Research will be available when the local engine is ready.")
                    .font(Theme.Font.caption)
                    .foregroundStyle(Theme.Color.textSecondary)
                    .lineLimit(2)
            }

            Spacer()
        }
        .padding(Theme.Spacing.md)
        .background(Theme.Color.surfaceElevated)
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(backendStatusColor.opacity(0.35), lineWidth: 1)
        )
    }

    private func sectionHeader(title: String, detail: String) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: Theme.Spacing.sm) {
            Text(title)
                .font(Theme.Font.headline)
                .foregroundStyle(Theme.Color.textPrimary)

            Text(detail)
                .font(Theme.Font.metadata)
                .foregroundStyle(Theme.Color.textMuted)

            Spacer()
        }
    }

    private func statusPill(label: String, systemImage: String, color: Color) -> some View {
        HStack(spacing: Theme.Spacing.xs) {
            Image(systemName: systemImage)
                .font(.system(size: 11, weight: .semibold))

            Text(label)
                .font(Theme.Font.metadata)
                .fontWeight(.medium)
        }
        .foregroundStyle(color)
        .padding(.horizontal, Theme.Spacing.sm)
        .padding(.vertical, Theme.Spacing.xs)
        .background(color.opacity(0.1))
        .clipShape(Capsule())
        .accessibilityLabel(label)
    }

    private var workspaceSubtitle: String {
        switch viewModel.state {
        case .idle:
            return currentThreadId == nil ? "New research session" : "Existing research thread"
        case .running:
            return "Research in progress"
        case .complete:
            return "Research complete"
        case .error:
            return "Research needs attention"
        }
    }

    private var flowDetail: String {
        if viewModel.state.isRunning {
            let activeCount = viewModel.activeAgents.count
            return activeCount == 1 ? "1 active agent" : "\(activeCount) active agents"
        }

        if !viewModel.completedAgents.isEmpty {
            return "\(viewModel.completedAgents.count) completed"
        }

        return "Waiting"
    }

    private var outputDetail: String {
        switch viewModel.state {
        case .idle:
            return "No current result"
        case .running:
            return "Streaming"
        case .complete(let turns, let durationMs, _):
            return "\(turns) turns in \(formatDuration(durationMs))"
        case .error:
            return "Error"
        }
    }

    private var backendStatusLabel: String {
        if backendManager.isRunning {
            return "Backend ready"
        }
        return backendManager.errorMessage == nil ? "Starting backend" : "Backend issue"
    }

    private var backendStatusColor: Color {
        if backendManager.isRunning {
            return Theme.Color.success
        }
        return backendManager.errorMessage == nil ? Theme.Color.warning : Theme.Color.danger
    }

    private func formatDuration(_ ms: Int) -> String {
        if ms < 1000 { return "\(ms)ms" }
        let seconds = Double(ms) / 1000.0
        if seconds < 60 { return String(format: "%.1fs", seconds) }
        let minutes = Int(seconds) / 60
        let remainingSec = Int(seconds) % 60
        return "\(minutes)m \(remainingSec)s"
    }
}
