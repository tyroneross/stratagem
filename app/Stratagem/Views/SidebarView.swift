import SwiftUI

struct SidebarView: View {
    @ObservedObject var threadStore: ThreadStore
    @Binding var selectedThreadId: String?
    var onNewResearch: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            // New Research button — full-width (Fitts)
            Button(action: onNewResearch) {
                HStack(spacing: Theme.Spacing.sm) {
                    Image(systemName: "plus")
                        .font(.system(size: 12, weight: .semibold))
                    Text("New Research")
                        .font(Theme.Font.body)
                        .fontWeight(.medium)
                }
                .foregroundStyle(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, Theme.Spacing.sm)
                .background(Theme.Color.accent)
                .clipShape(RoundedRectangle(cornerRadius: 6))
            }
            .buttonStyle(.plain)
            .padding(Theme.Spacing.md)

            // Thread list
            if threadStore.threads.isEmpty {
                VStack(spacing: Theme.Spacing.sm) {
                    Text("No research history")
                        .font(Theme.Font.caption)
                        .foregroundStyle(Theme.Color.textMuted)
                }
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

                            // Divider between items (not after last)
                            if thread.id != threadStore.threads.last?.id {
                                Rectangle()
                                    .fill(Theme.Color.border)
                                    .frame(height: 1)
                                    .padding(.leading, Theme.Spacing.md)
                            }
                        }
                    }
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .strokeBorder(Theme.Color.border, lineWidth: 1)
                    )
                    .padding(.horizontal, Theme.Spacing.md)
                }
            }

            Spacer()
        }
        .frame(maxHeight: .infinity)
        .background(Theme.Color.surfaceSecondary)
    }
}
