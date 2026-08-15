import SwiftUI

struct ThreadRowView: View {
    let thread: ResearchThread
    let isSelected: Bool

    var body: some View {
        HStack(spacing: 0) {
            Rectangle()
                .fill(isSelected ? Theme.Color.accent : Color.clear)
                .frame(width: 3)

            VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                Text(thread.title)
                    .font(Theme.Font.body)
                    .fontWeight(isSelected ? .medium : .regular)
                    .foregroundStyle(isSelected ? Theme.Color.textPrimary : Theme.Color.textSecondary)
                    .lineLimit(1)
                    .truncationMode(.tail)

                Text(thread.relativeTime)
                    .font(Theme.Font.caption)
                    .foregroundStyle(Theme.Color.textSecondary)

                Text("\(thread.queryCount) \(thread.queryCount == 1 ? "query" : "queries")")
                    .font(Theme.Font.metadata)
                    .foregroundStyle(Theme.Color.textMuted)
            }
            .padding(.horizontal, Theme.Spacing.md)
            .padding(.vertical, Theme.Spacing.sm)

            Spacer()
        }
        .frame(minHeight: 64)
        .background(isSelected ? Theme.Color.surfaceSecondary : Color.clear)
    }
}
