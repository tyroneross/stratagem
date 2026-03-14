import SwiftUI
import UniformTypeIdentifiers

struct SetupView: View {
    @StateObject private var setupManager = SetupManager()
    @EnvironmentObject private var appState: AppState
    @State private var isValidated = false
    @State private var showingFolderPicker = false
    @State private var showingDevFolderPicker = false

    var body: some View {
        VStack(spacing: 0) {
            // Header
            VStack(spacing: Theme.Spacing.sm) {
                Text("Stratagem")
                    .font(Theme.Font.title)
                    .foregroundStyle(Theme.Color.textPrimary)

                Text("AI-driven task planning and execution")
                    .font(Theme.Font.caption)
                    .foregroundStyle(Theme.Color.textSecondary)
            }
            .padding(.top, Theme.Spacing.xxl)
            .padding(.bottom, Theme.Spacing.xl)

            // Configuration form
            VStack(alignment: .leading, spacing: Theme.Spacing.lg) {
                // Python detection status
                HStack(spacing: Theme.Spacing.md) {
                    Image(systemName: statusIcon)
                        .foregroundStyle(statusColor)
                        .font(Theme.Font.body)

                    VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                        Text(statusText)
                            .font(Theme.Font.body)
                            .foregroundStyle(Theme.Color.textPrimary)

                        if !setupManager.pythonPath.isEmpty {
                            Text(setupManager.pythonPath)
                                .font(Theme.Font.caption)
                                .foregroundStyle(Theme.Color.textMuted)
                        }
                    }

                    Spacer()

                    if setupManager.isChecking {
                        ProgressView()
                            .scaleEffect(0.7)
                            .frame(width: 20, height: 20)
                    } else if setupManager.pythonPath.isEmpty {
                        Button("Detect") {
                            Task {
                                await setupManager.detectEnvironment()
                            }
                        }
                        .buttonStyle(.plain)
                        .foregroundStyle(Theme.Color.accent)
                        .font(Theme.Font.body)
                    }
                }
                .padding(Theme.Spacing.md)
                .background(Theme.Color.surface)
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .strokeBorder(Theme.Color.border, lineWidth: 1)
                )

                // Project directory
                VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                    Text("Project Directory")
                        .font(Theme.Font.caption)
                        .foregroundStyle(Theme.Color.textMuted)

                    HStack(spacing: Theme.Spacing.sm) {
                        TextField("", text: $setupManager.projectDirectory)
                            .textFieldStyle(.plain)
                            .font(Theme.Font.body)
                            .foregroundStyle(Theme.Color.textPrimary)
                            .padding(.horizontal, Theme.Spacing.md)
                            .padding(.vertical, Theme.Spacing.sm)
                            .background(Theme.Color.surface)
                            .clipShape(RoundedRectangle(cornerRadius: 6))
                            .overlay(
                                RoundedRectangle(cornerRadius: 6)
                                    .strokeBorder(Theme.Color.border, lineWidth: 1)
                            )

                        Button {
                            showingFolderPicker = true
                        } label: {
                            Image(systemName: "folder")
                                .font(Theme.Font.body)
                        }
                        .buttonStyle(.plain)
                        .foregroundStyle(Theme.Color.accent)
                    }
                }

                Divider()
                    .background(Theme.Color.border)

                // Development mode
                VStack(alignment: .leading, spacing: Theme.Spacing.md) {
                    Toggle(isOn: $setupManager.developmentMode) {
                        VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                            Text("Development Mode")
                                .font(Theme.Font.body)
                                .foregroundStyle(Theme.Color.textPrimary)

                            Text("Install stratagem from local source with -e flag")
                                .font(Theme.Font.caption)
                                .foregroundStyle(Theme.Color.textMuted)
                        }
                    }
                    .toggleStyle(.switch)
                    .onChange(of: setupManager.developmentMode) { oldValue, newValue in
                        if newValue && setupManager.devModePath.isEmpty {
                            setupManager.devModePath = (setupManager.projectDirectory as NSString).deletingLastPathComponent + "/stratagem"
                        }
                    }

                    if setupManager.developmentMode {
                        VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                            Text("Source Path")
                                .font(Theme.Font.caption)
                                .foregroundStyle(Theme.Color.textMuted)

                            HStack(spacing: Theme.Spacing.sm) {
                                TextField("", text: $setupManager.devModePath)
                                    .textFieldStyle(.plain)
                                    .font(Theme.Font.body)
                                    .foregroundStyle(Theme.Color.textPrimary)
                                    .padding(.horizontal, Theme.Spacing.md)
                                    .padding(.vertical, Theme.Spacing.sm)
                                    .background(Theme.Color.surface)
                                    .clipShape(RoundedRectangle(cornerRadius: 6))
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 6)
                                            .strokeBorder(Theme.Color.border, lineWidth: 1)
                                    )

                                Button {
                                    showingDevFolderPicker = true
                                } label: {
                                    Image(systemName: "folder")
                                        .font(Theme.Font.body)
                                }
                                .buttonStyle(.plain)
                                .foregroundStyle(Theme.Color.accent)
                            }
                        }
                        .padding(.leading, Theme.Spacing.lg)
                    }
                }

                // Error message
                if let errorMessage = setupManager.errorMessage {
                    Text(errorMessage)
                        .font(Theme.Font.caption)
                        .foregroundStyle(.red)
                        .padding(Theme.Spacing.md)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color.red.opacity(0.1))
                        .clipShape(RoundedRectangle(cornerRadius: 6))
                }
            }
            .padding(.horizontal, Theme.Spacing.xxl)
            .frame(maxWidth: 600)

            Spacer()

            // Continue button
            Button {
                Task {
                    if await setupManager.validateSetup() {
                        setupManager.saveConfiguration()
                        appState.markConfigured()
                    }
                }
            } label: {
                Text(setupManager.isChecking ? "Validating..." : "Continue")
                    .font(Theme.Font.body)
                    .fontWeight(.medium)
                    .foregroundStyle(canContinue ? .white : Theme.Color.textMuted)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, Theme.Spacing.md)
                    .background(canContinue ? Theme.Color.accent : Theme.Color.surfaceSecondary)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            }
            .buttonStyle(.plain)
            .disabled(!canContinue)
            .frame(maxWidth: 600)
            .padding(.horizontal, Theme.Spacing.xxl)
            .padding(.bottom, Theme.Spacing.xl)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Theme.Color.background)
        .fileImporter(
            isPresented: $showingFolderPicker,
            allowedContentTypes: [.folder]
        ) { result in
            if case .success(let url) = result {
                setupManager.projectDirectory = url.path
            }
        }
        .fileImporter(
            isPresented: $showingDevFolderPicker,
            allowedContentTypes: [.folder]
        ) { result in
            if case .success(let url) = result {
                setupManager.devModePath = url.path
            }
        }
        .task {
            if setupManager.pythonPath.isEmpty {
                await setupManager.detectEnvironment()
            }
        }
    }

    private var canContinue: Bool {
        !setupManager.pythonPath.isEmpty &&
        !setupManager.projectDirectory.isEmpty &&
        !setupManager.isChecking &&
        (!setupManager.developmentMode || !setupManager.devModePath.isEmpty)
    }

    private var statusIcon: String {
        if setupManager.isChecking {
            return "arrow.triangle.2.circlepath"
        } else if setupManager.uvAvailable && !setupManager.pythonPath.isEmpty {
            return "checkmark.circle.fill"
        } else if !setupManager.pythonPath.isEmpty {
            return "checkmark.circle"
        } else {
            return "exclamationmark.triangle"
        }
    }

    private var statusColor: Color {
        if setupManager.isChecking {
            return Theme.Color.textSecondary
        } else if setupManager.uvAvailable && !setupManager.pythonPath.isEmpty {
            return .green
        } else if !setupManager.pythonPath.isEmpty {
            return .orange
        } else {
            return .red
        }
    }

    private var statusText: String {
        if setupManager.isChecking {
            return "Detecting Python environment..."
        } else if setupManager.uvAvailable && !setupManager.pythonPath.isEmpty {
            return "Python environment ready (uv)"
        } else if !setupManager.pythonPath.isEmpty {
            return "Python found (uv recommended)"
        } else {
            return "Python not found"
        }
    }
}

#Preview {
    SetupView()
        .environmentObject(AppState())
}
