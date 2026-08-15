import SwiftUI

struct OutputView: View {
    let text: String
    let state: ResearchState

    @State private var autoScroll = true

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    content

                    Color.clear
                        .frame(height: 1)
                        .id("bottom")
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .onChange(of: text) { _, _ in
                if autoScroll {
                    withAnimation(.easeOut(duration: 0.1)) {
                        proxy.scrollTo("bottom", anchor: .bottom)
                    }
                }
            }
        }
        .background(Theme.Color.surfaceElevated)
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(Theme.Color.border, lineWidth: 1)
        )
    }

    @ViewBuilder
    private var content: some View {
        if !text.isEmpty {
            outputText

            if case .error(let message) = state {
                errorState(message)
            }
        } else if case .error(let message) = state {
            errorState(message)
        } else if state.isRunning {
            runningState
        } else {
            emptyState
        }
    }

    private var outputText: some View {
        Text(text)
            .font(.system(size: 13, design: .monospaced))
            .lineSpacing(4)
            .foregroundStyle(Theme.Color.textPrimary)
            .textSelection(.enabled)
            .padding(Theme.Spacing.md)
            .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var runningState: some View {
        HStack(spacing: Theme.Spacing.sm) {
            ProgressView()
                .scaleEffect(0.7)
                .frame(width: 18, height: 18)

            VStack(alignment: .leading, spacing: 2) {
                Text("Starting research")
                    .font(Theme.Font.body)
                    .fontWeight(.medium)
                    .foregroundStyle(Theme.Color.textPrimary)

                Text("The first output will stream here.")
                    .font(Theme.Font.caption)
                    .foregroundStyle(Theme.Color.textSecondary)
            }
        }
        .padding(Theme.Spacing.lg)
        .frame(maxWidth: .infinity, minHeight: 180, alignment: .center)
    }

    private var emptyState: some View {
        VStack(spacing: Theme.Spacing.sm) {
            Image(systemName: "doc.text.magnifyingglass")
                .font(.system(size: 28, weight: .regular))
                .foregroundStyle(Theme.Color.textMuted)

            VStack(spacing: 2) {
                Text("Ready for research")
                    .font(Theme.Font.body)
                    .fontWeight(.medium)
                    .foregroundStyle(Theme.Color.textPrimary)

                Text("Results will appear here after a run.")
                    .font(Theme.Font.caption)
                    .foregroundStyle(Theme.Color.textSecondary)
            }
        }
        .padding(Theme.Spacing.lg)
        .frame(maxWidth: .infinity, minHeight: 220, alignment: .center)
    }

    private func errorState(_ message: String) -> some View {
        HStack(alignment: .top, spacing: Theme.Spacing.sm) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(Theme.Color.danger)
                .frame(width: 18)

            VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                Text("Research failed")
                    .font(Theme.Font.body)
                    .fontWeight(.semibold)
                    .foregroundStyle(Theme.Color.textPrimary)

                Text(message)
                    .font(Theme.Font.caption)
                    .foregroundStyle(Theme.Color.textSecondary)
                    .textSelection(.enabled)
            }

            Spacer()
        }
        .padding(Theme.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.Color.danger.opacity(0.08))
    }
}
