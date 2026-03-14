import SwiftUI

struct ThreadRowView: View {
    let thread: ResearchThread
    let isSelected: Bool

    var body: some View {
        HStack(spacing: 0) {
            // Selection indicator — 2px leading accent border
            Rectangle()
                .fill(isSelected ? Theme.Color.accent : Color.clear)
                .frame(width: 2)

            VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                // Title — 14px, medium when selected
                Text(thread.title)
                    .font(Theme.Font.body)
                    .fontWeight(isSelected ? .medium : .regular)
                    .foregroundStyle(isSelected ? Theme.Color.textPrimary : Theme.Color.textSecondary)
                    .lineLimit(1)
                    .truncationMode(.tail)

                // Time — 12px
                Text(thread.relativeTime)
                    .font(Theme.Font.caption)
                    .foregroundStyle(Theme.Color.textSecondary)

                // Meta — 11px muted
                Text("\(thread.queryCount) \(thread.queryCount == 1 ? "query" : "queries")")
                    .font(Theme.Font.metadata)
                    .foregroundStyle(Theme.Color.textMuted)
            }
            .padding(.horizontal, Theme.Spacing.md)
            .padding(.vertical, Theme.Spacing.sm)

            Spacer()
        }
        .background(isSelected ? Theme.Color.surface : Color.clear)
    }
}
