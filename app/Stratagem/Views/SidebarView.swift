import SwiftUI

struct SidebarView: View {
    @ObservedObject var threadStore: ThreadStore
    @Binding var selectedThreadId: String?
    var onNewResearch: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            VStack(alignment: .leading, spacing: Theme.Spacing.md) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Stratagem")
                        .font(Theme.Font.headline)
                        .foregroundStyle(Theme.Color.textPrimary)

                    Text("Research history")
                        .font(Theme.Font.metadata)
                        .foregroundStyle(Theme.Color.textMuted)
                }

                newResearchButton
            }
            .padding(Theme.Spacing.md)

            Rectangle()
                .fill(Theme.Color.border)
                .frame(height: 1)

            HStack(alignment: .firstTextBaseline) {
                Text("Threads")
                    .font(Theme.Font.caption)
                    .fontWeight(.semibold)
                    .foregroundStyle(Theme.Color.textSecondary)

                Spacer()

                Text(threadCountLabel)
                    .font(Theme.Font.metadata)
                    .foregroundStyle(Theme.Color.textMuted)
            }
            .padding(.horizontal, Theme.Spacing.md)
            .padding(.top, Theme.Spacing.md)
            .padding(.bottom, Theme.Spacing.sm)

            if threadStore.threads.isEmpty {
                emptyState
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVStack(spacing: 0) {
                        ForEach(threadStore.threads) { thread in
                            ThreadRowView(
                                thread: thread,
                                isSelected: selectedThreadId == thread.id
                            )
                            .contentShape(Rectangle())
                            .onTapGesture {
                                selectedThreadId = thread.id
                            }

                            if thread.id != threadStore.threads.last?.id {
                                Rectangle()
                                    .fill(Theme.Color.border)
                                    .frame(height: 1)
                                    .padding(.leading, Theme.Spacing.md)
                            }
                        }
                    }
                    .background(Theme.Color.surfaceElevated)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .strokeBorder(Theme.Color.border, lineWidth: 1)
                    )
                    .padding(.horizontal, Theme.Spacing.md)
                }
            }

            Spacer(minLength: 0)
        }
        .frame(maxHeight: .infinity)
        .background(Theme.Color.surfaceSecondary)
    }

    private var newResearchButton: some View {
        Button(action: onNewResearch) {
            HStack(spacing: Theme.Spacing.sm) {
                Image(systemName: "plus")
                    .font(.system(size: 12, weight: .semibold))
                Text("New Research")
                    .font(Theme.Font.body)
                    .fontWeight(.medium)
            }
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity, minHeight: 40)
            .background(Theme.Color.accent)
            .clipShape(RoundedRectangle(cornerRadius: 6))
        }
        .buttonStyle(.plain)
    }

    private var emptyState: some View {
        VStack(spacing: Theme.Spacing.sm) {
            if threadStore.isLoading {
                ProgressView()
                    .scaleEffect(0.7)
                    .frame(width: 20, height: 20)

                Text("Loading threads")
                    .font(Theme.Font.caption)
                    .foregroundStyle(Theme.Color.textMuted)
            } else {
                Image(systemName: "clock.arrow.circlepath")
                    .font(.system(size: 24))
                    .foregroundStyle(Theme.Color.textMuted)

                VStack(spacing: 2) {
                    Text("No research yet")
                        .font(Theme.Font.caption)
                        .fontWeight(.medium)
                        .foregroundStyle(Theme.Color.textSecondary)

                    Text("Completed runs will appear here.")
                        .font(Theme.Font.metadata)
                        .foregroundStyle(Theme.Color.textMuted)
                }
            }
        }
        .multilineTextAlignment(.center)
        .padding(Theme.Spacing.lg)
    }

    private var threadCountLabel: String {
        if threadStore.isLoading {
            return "Loading"
        }

        let count = threadStore.threads.count
        return count == 1 ? "1 thread" : "\(count) threads"
    }
}
