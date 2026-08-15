import SwiftUI

struct QueryInputView: View {
    @ObservedObject var viewModel: ResearchViewModel
    let isBackendReady: Bool
    let backendError: String?
    var onRun: () -> Void
    var onStop: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
            HStack(alignment: .firstTextBaseline) {
                Text("Question")
                    .font(Theme.Font.caption)
                    .fontWeight(.semibold)
                    .foregroundStyle(Theme.Color.textPrimary)

                Spacer()

                if let statusText {
                    Text(statusText)
                        .font(Theme.Font.metadata)
                        .foregroundStyle(statusColor)
                        .lineLimit(1)
                        .truncationMode(.tail)
                }
            }

            TextField("Ask a market research question...", text: $viewModel.query, axis: .vertical)
                .textFieldStyle(.plain)
                .font(Theme.Font.body)
                .foregroundStyle(Theme.Color.textPrimary)
                .padding(Theme.Spacing.md)
                .frame(minHeight: 72, maxHeight: 132)
                .lineLimit(3...6)
                .background(Theme.Color.surfaceElevated)
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .strokeBorder(inputBorderColor, lineWidth: 1)
                )
                .onSubmit {
                    if canSubmit {
                        onRun()
                    }
            }

            HStack(spacing: Theme.Spacing.sm) {
                HStack(spacing: Theme.Spacing.xs) {
                    Text("Model")
                        .font(Theme.Font.metadata)
                        .foregroundStyle(Theme.Color.textMuted)

                    Picker("", selection: $viewModel.selectedModel) {
                        ForEach(viewModel.availableModels, id: \.self) { model in
                            Text(model.capitalized).tag(model)
                        }
                    }
                    .pickerStyle(.segmented)
                    .frame(width: 220)
                    .disabled(viewModel.state.isRunning)
                    .accessibilityLabel("Model")
                }

                Spacer()

                if case .complete(let turns, let durationMs, let cost) = viewModel.state {
                    HStack(spacing: Theme.Spacing.xs) {
                        Text("\(turns) turns")
                        Text("·")
                        Text(formatDuration(durationMs))
                        if let cost = cost {
                            Text("·")
                            Text("$\(cost)")
                        }
                    }
                    .font(Theme.Font.metadata)
                    .foregroundStyle(Theme.Color.textMuted)
                }

                if viewModel.state.isRunning {
                    Button(action: onStop) {
                        HStack(spacing: Theme.Spacing.xs) {
                            Image(systemName: "stop.fill")
                                .font(.system(size: 10))
                            Text("Stop")
                        }
                        .font(Theme.Font.body)
                        .fontWeight(.medium)
                        .foregroundStyle(.white)
                        .frame(minWidth: 96, minHeight: 36)
                        .background(Theme.Color.danger)
                        .clipShape(RoundedRectangle(cornerRadius: 6))
                    }
                    .buttonStyle(.plain)
                } else {
                    Button(action: onRun) {
                        HStack(spacing: Theme.Spacing.xs) {
                            Image(systemName: "play.fill")
                                .font(.system(size: 10))
                            Text("Run")
                        }
                        .font(Theme.Font.body)
                        .fontWeight(.medium)
                        .foregroundStyle(canSubmit ? .white : Theme.Color.textMuted)
                        .frame(minWidth: 96, minHeight: 36)
                        .background(canSubmit ? Theme.Color.accent : Theme.Color.surfaceSecondary)
                        .clipShape(RoundedRectangle(cornerRadius: 6))
                    }
                    .buttonStyle(.plain)
                    .disabled(!canSubmit)
                    .keyboardShortcut(.return, modifiers: .command)
                }
            }
        }
        .padding(Theme.Spacing.md)
    }

    private var canSubmit: Bool {
        viewModel.canRun && isBackendReady
    }

    private var statusText: String? {
        if let backendError, !backendError.isEmpty {
            return backendError
        }

        if !isBackendReady {
            return "Starting backend"
        }

        if case .error(let message) = viewModel.state {
            return message
        }

        return nil
    }

    private var statusColor: Color {
        hasErrorStatus ? Theme.Color.danger : Theme.Color.warning
    }

    private var hasErrorStatus: Bool {
        if let backendError, !backendError.isEmpty {
            return true
        }

        if case .error = viewModel.state {
            return true
        }

        return false
    }

    private var inputBorderColor: Color {
        canSubmit || viewModel.query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            ? Theme.Color.border
            : Theme.Color.warning.opacity(0.55)
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
