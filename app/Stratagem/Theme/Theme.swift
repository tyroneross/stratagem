import SwiftUI

enum Theme {
    enum Color {
        static let background = SwiftUI.Color(nsColor: .windowBackgroundColor)

        static let surface = SwiftUI.Color(
            light: NSColor(hex: "#F9FAFB"),
            dark: NSColor(hex: "#111827")
        )

        static let surfaceSecondary = SwiftUI.Color(
            light: NSColor(hex: "#F3F4F6"),
            dark: NSColor(hex: "#1F2937")
        )

        static let border = SwiftUI.Color(
            light: NSColor(hex: "#E5E7EB"),
            dark: NSColor(hex: "#374151")
        )

        static let textPrimary = SwiftUI.Color(
            light: NSColor(hex: "#111827"),
            dark: NSColor(hex: "#F9FAFB")
        )

        static let textSecondary = SwiftUI.Color(
            light: NSColor(hex: "#6B7280"),
            dark: NSColor(hex: "#9CA3AF")
        )

        static let textMuted = SwiftUI.Color(
            light: NSColor(hex: "#9CA3AF"),
            dark: NSColor(hex: "#6B7280")
        )

        static let accent = SwiftUI.Color(
            light: NSColor(hex: "#0D9488"),
            dark: NSColor(hex: "#14B8A6")
        )

        static let accentLight = SwiftUI.Color(
            light: NSColor(hex: "#5EEAD4"),
            dark: NSColor(hex: "#2DD4BF")
        )

        // Node states
        static let nodeIdleFill = SwiftUI.Color(
            light: NSColor(hex: "#F3F4F6"),
            dark: NSColor(hex: "#374151")
        )

        static let nodeIdleStroke = SwiftUI.Color(
            light: NSColor(hex: "#D1D5DB"),
            dark: NSColor(hex: "#4B5563")
        )

        static let nodeIdleText = SwiftUI.Color(
            light: NSColor(hex: "#6B7280"),
            dark: NSColor(hex: "#9CA3AF")
        )

        static let nodeActiveFill = SwiftUI.Color(
            light: NSColor(hex: "#2563EB"),
            dark: NSColor(hex: "#3B82F6")
        )

        static let nodeActiveStroke = SwiftUI.Color(
            light: NSColor(hex: "#1D4ED8"),
            dark: NSColor(hex: "#2563EB")
        )

        static let nodeActiveText = SwiftUI.Color.white

        static let nodeCompletedFill = SwiftUI.Color(
            light: NSColor(hex: "#DBEAFE"),
            dark: NSColor(hex: "#1E3A5F")
        )

        static let nodeCompletedStroke = SwiftUI.Color(
            light: NSColor(hex: "#93C5FD"),
            dark: NSColor(hex: "#3B82F6")
        )

        static let nodeCompletedText = SwiftUI.Color(
            light: NSColor(hex: "#1D4ED8"),
            dark: NSColor(hex: "#93C5FD")
        )
    }

    enum Font {
        static let title = SwiftUI.Font.system(size: 16, weight: .bold)
        static let body = SwiftUI.Font.system(size: 14)
        static let caption = SwiftUI.Font.system(size: 12)
        static let metadata = SwiftUI.Font.system(size: 11)
    }

    enum Spacing {
        static let xs: CGFloat = 4
        static let sm: CGFloat = 8
        static let md: CGFloat = 16
        static let lg: CGFloat = 24
        static let xl: CGFloat = 32
        static let xxl: CGFloat = 48
    }
}

// MARK: - SwiftUI Color Extension

extension SwiftUI.Color {
    init(light: NSColor, dark: NSColor) {
        self.init(nsColor: NSColor(name: nil) { appearance in
            switch appearance.name {
            case .darkAqua, .vibrantDark, .accessibilityHighContrastDarkAqua, .accessibilityHighContrastVibrantDark:
                return dark
            default:
                return light
            }
        })
    }
}

// MARK: - NSColor Extension

extension NSColor {
    convenience init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }

        self.init(
            red: CGFloat(r) / 255,
            green: CGFloat(g) / 255,
            blue:  CGFloat(b) / 255,
            alpha: CGFloat(a) / 255
        )
    }
}
