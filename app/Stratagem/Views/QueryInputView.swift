import SwiftUI

struct QueryInputView: View {
    @ObservedObject var viewModel: ResearchViewModel
    var onRun: () -> Void
    var onStop: () -> Void

    var body: some View {
        VStack(spacing: Theme.Spacing.sm) {
            // Query text area
            TextEditor(text: $viewModel.query)
                .font(Theme.Font.body)
                .foregroundStyle(Theme.Color.textPrimary)
                .scrollContentBackground(.hidden)
                .padding(Theme.Spacing.sm)
                .frame(minHeight: 60, maxHeight: 120)
                .background(Theme.Color.surface)
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .strokeBorder(Theme.Color.border, lineWidth: 1)
                )
                .overlay(alignment: .topLeading) {
                    if viewModel.query.isEmpty {
                        Text("Enter your research question...")
                            .font(Theme.Font.body)
                            .foregroundStyle(Theme.Color.textMuted)
                            .padding(.horizontal, Theme.Spacing.md)
                            .padding(.vertical, Theme.Spacing.md)
                            .allowsHitTesting(false)
                    }
                }

            // Controls row
            HStack(spacing: Theme.Spacing.sm) {
                // Model picker
                Picker("", selection: $viewModel.selectedModel) {
                    ForEach(viewModel.availableModels, id: \.self) { model in
                        Text(model.capitalized).tag(model)
                    }
                }
                .pickerStyle(.segmented)
                .frame(width: 200)

                Spacer()

                // Status
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

                // Run / Stop button
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
                        .padding(.horizontal, Theme.Spacing.md)
                        .padding(.vertical, Theme.Spacing.sm)
                        .background(Color.red.opacity(0.8))
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
                        .foregroundStyle(viewModel.canRun ? .white : Theme.Color.textMuted)
                        .padding(.horizontal, Theme.Spacing.md)
                        .padding(.vertical, Theme.Spacing.sm)
                        .background(viewModel.canRun ? Theme.Color.accent : Theme.Color.surfaceSecondary)
                        .clipShape(RoundedRectangle(cornerRadius: 6))
                    }
                    .buttonStyle(.plain)
                    .disabled(!viewModel.canRun)
                    .keyboardShortcut(.return, modifiers: .command)
                }
            }
        }
        .padding(Theme.Spacing.md)
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
