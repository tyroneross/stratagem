import SwiftUI

struct OutputView: View {
    let text: String
    let state: ResearchState

    @State private var autoScroll = true

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    if text.isEmpty && state.isRunning {
                        HStack(spacing: Theme.Spacing.sm) {
                            ProgressView()
                                .scaleEffect(0.6)
                                .frame(width: 16, height: 16)
                            Text("Starting research...")
                                .font(Theme.Font.body)
                                .foregroundStyle(Theme.Color.textMuted)
                        }
                        .padding(Theme.Spacing.md)
                    } else if text.isEmpty && !state.isRunning {
                        Text("Results will appear here")
                            .font(Theme.Font.body)
                            .foregroundStyle(Theme.Color.textMuted)
                            .padding(Theme.Spacing.md)
                    } else {
                        Text(text)
                            .font(.system(size: 13, design: .monospaced))
                            .foregroundStyle(Theme.Color.textPrimary)
                            .textSelection(.enabled)
                            .padding(Theme.Spacing.md)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }

                    // Error display
                    if case .error(let message) = state {
                        Text(message)
                            .font(Theme.Font.caption)
                            .foregroundStyle(.red)
                            .padding(Theme.Spacing.md)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(Color.red.opacity(0.1))
                    }

                    // Scroll anchor
                    Color.clear
                        .frame(height: 1)
                        .id("bottom")
                }
            }
            .onChange(of: text) { _, _ in
                if autoScroll {
                    withAnimation(.easeOut(duration: 0.1)) {
                        proxy.scrollTo("bottom", anchor: .bottom)
                    }
                }
            }
        }
        .background(Theme.Color.surface)
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(Theme.Color.border, lineWidth: 1)
        )
    }
}
