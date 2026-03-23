import SwiftUI

struct SetupView: View {
    @StateObject private var setup = SetupManager()
    @EnvironmentObject private var appState: AppState
    @State private var showAdvanced = false
    @State private var showingFolderPicker = false
    @State private var showingDevFolderPicker = false

    var body: some View {
        VStack(spacing: 0) {
            Spacer()

            VStack(spacing: Theme.Spacing.lg) {
                // Header
                VStack(spacing: Theme.Spacing.xs) {
                    Text("Stratagem")
                        .font(.system(size: 28, weight: .bold))
                        .foregroundStyle(Theme.Color.textPrimary)

                    Text("AI-powered market research")
                        .font(Theme.Font.body)
                        .foregroundStyle(Theme.Color.textSecondary)
                }

                // Content depends on state
                switch setup.phase {
                case .welcome:
                    welcomeContent
                case .checking, .installingUv, .needsUv, .installingStratagem:
                    installingContent
                case .chooseDirectory:
                    folderContent
                case .ready:
                    readyContent
                case .failed:
                    failedContent
                }
            }
            .frame(maxWidth: 420)

            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Theme.Color.background)
        .fileImporter(
            isPresented: $showingFolderPicker,
            allowedContentTypes: [.folder]
        ) { result in
            if case .success(let url) = result {
                setup.projectDirectory = url.path
            }
        }
        .fileImporter(
            isPresented: $showingDevFolderPicker,
            allowedContentTypes: [.folder]
        ) { result in
            if case .success(let url) = result {
                setup.devModePath = url.path
            }
        }
    }

    // MARK: - Welcome (before any setup)

    private var welcomeContent: some View {
        VStack(spacing: Theme.Spacing.lg) {
            Text("Stratagem needs to install a few things before it can run research.")
                .font(Theme.Font.body)
                .foregroundStyle(Theme.Color.textSecondary)
                .multilineTextAlignment(.center)

            // Advanced: contributor mode
            advancedSection

            Button {
                Task { await setup.startSetup() }
            } label: {
                Text("Install")
                    .font(Theme.Font.body)
                    .fontWeight(.medium)
                    .foregroundStyle(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(Theme.Color.accent)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            }
            .buttonStyle(.plain)
        }
    }

    // MARK: - Installing (automatic steps)

    private var installingContent: some View {
        VStack(spacing: Theme.Spacing.lg) {
            // Progress checklist
            VStack(spacing: 0) {
                checkRow(
                    label: "Package manager",
                    status: setup.uvStatus
                )

                Divider().background(Theme.Color.border)

                checkRow(
                    label: "Research engine",
                    status: setup.stratagemStatus
                )
            }
            .background(Theme.Color.surface)
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .strokeBorder(Theme.Color.border, lineWidth: 1)
            )

            // Status text
            if !setup.statusText.isEmpty {
                HStack(spacing: Theme.Spacing.sm) {
                    ProgressView()
                        .scaleEffect(0.5)
                        .frame(width: 12, height: 12)

                    Text(setup.statusText)
                        .font(Theme.Font.metadata)
                        .foregroundStyle(Theme.Color.textMuted)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }

            // Error
            if let error = setup.errorMessage {
                errorBanner(error)
            }

            // Action: install uv if needed
            if setup.phase == .needsUv {
                VStack(spacing: Theme.Spacing.sm) {
                    Text("Stratagem needs a package manager to install research tools.")
                        .font(Theme.Font.caption)
                        .foregroundStyle(Theme.Color.textSecondary)
                        .multilineTextAlignment(.center)

                    Button {
                        Task { await setup.installUv() }
                    } label: {
                        Text("Install")
                            .font(Theme.Font.body)
                            .fontWeight(.medium)
                            .foregroundStyle(.white)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 14)
                            .background(Theme.Color.accent)
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    // MARK: - Choose Folder

    private var folderContent: some View {
        VStack(spacing: Theme.Spacing.lg) {
            VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                Text("Where should research be saved?")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(Theme.Color.textPrimary)

                Text("Reports, data exports, and downloaded files go here.")
                    .font(Theme.Font.caption)
                    .foregroundStyle(Theme.Color.textSecondary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            // Folder picker
            HStack(spacing: Theme.Spacing.sm) {
                TextField("", text: $setup.projectDirectory)
                    .textFieldStyle(.plain)
                    .font(Theme.Font.body)
                    .foregroundStyle(Theme.Color.textPrimary)
                    .padding(.horizontal, Theme.Spacing.md)
                    .padding(.vertical, 10)
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
                        .frame(width: 36, height: 36)
                }
                .buttonStyle(.plain)
                .foregroundStyle(Theme.Color.accent)
            }

            Button {
                setup.completeSetup()
            } label: {
                Text("Continue")
                    .font(Theme.Font.body)
                    .fontWeight(.medium)
                    .foregroundStyle(!setup.projectDirectory.isEmpty ? .white : Theme.Color.textMuted)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(!setup.projectDirectory.isEmpty ? Theme.Color.accent : Theme.Color.surfaceSecondary)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            }
            .buttonStyle(.plain)
            .disabled(setup.projectDirectory.isEmpty)
        }
    }

    // MARK: - Ready

    private var readyContent: some View {
        VStack(spacing: Theme.Spacing.xl) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 48))
                .foregroundStyle(.green)

            VStack(spacing: Theme.Spacing.xs) {
                Text("Ready")
                    .font(.system(size: 20, weight: .bold))
                    .foregroundStyle(Theme.Color.textPrimary)

                Text("Stratagem is set up and ready to run.")
                    .font(Theme.Font.body)
                    .foregroundStyle(Theme.Color.textSecondary)
            }

            Button {
                appState.markConfigured()
            } label: {
                Text("Start Researching")
                    .font(Theme.Font.body)
                    .fontWeight(.medium)
                    .foregroundStyle(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(Theme.Color.accent)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            }
            .buttonStyle(.plain)
        }
    }

    // MARK: - Failed

    private var failedContent: some View {
        VStack(spacing: Theme.Spacing.lg) {
            if let error = setup.errorMessage {
                errorBanner(error)
            }

            Button {
                Task { await setup.retry() }
            } label: {
                Text("Try Again")
                    .font(Theme.Font.body)
                    .fontWeight(.medium)
                    .foregroundStyle(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(Theme.Color.accent)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            }
            .buttonStyle(.plain)
        }
    }

    // MARK: - Components

    private func checkRow(label: String, status: CheckStatus) -> some View {
        HStack(spacing: Theme.Spacing.md) {
            statusIcon(for: status)
                .frame(width: 20, height: 20)

            Text(label)
                .font(Theme.Font.body)
                .foregroundStyle(Theme.Color.textPrimary)

            Spacer()

            Text(statusLabel(for: status))
                .font(Theme.Font.caption)
                .foregroundStyle(statusColor(for: status))
        }
        .padding(Theme.Spacing.md)
    }

    @ViewBuilder
    private func statusIcon(for status: CheckStatus) -> some View {
        switch status {
        case .pending:
            Circle()
                .strokeBorder(Theme.Color.border, lineWidth: 1.5)
        case .checking, .installing:
            ProgressView()
                .scaleEffect(0.6)
        case .installed:
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 16))
                .foregroundStyle(.green)
        case .missing:
            Image(systemName: "circle")
                .font(.system(size: 16))
                .foregroundStyle(.orange)
        case .failed:
            Image(systemName: "xmark.circle.fill")
                .font(.system(size: 16))
                .foregroundStyle(.red)
        }
    }

    private func statusLabel(for status: CheckStatus) -> String {
        switch status {
        case .pending: return ""
        case .checking: return "Checking..."
        case .installed: return "Installed"
        case .missing: return "Not found"
        case .installing: return "Installing..."
        case .failed(let msg): return msg
        }
    }

    private func statusColor(for status: CheckStatus) -> Color {
        switch status {
        case .installed: return .green
        case .missing, .failed: return .orange
        default: return Theme.Color.textMuted
        }
    }

    private func errorBanner(_ message: String) -> some View {
        HStack(alignment: .top, spacing: Theme.Spacing.sm) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundStyle(.orange)
                .font(.system(size: 13))

            Text(message)
                .font(Theme.Font.caption)
                .foregroundStyle(.orange)
        }
        .padding(Theme.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.orange.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    // MARK: - Advanced (contributor options)

    private var advancedSection: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
            Button {
                withAnimation(.easeInOut(duration: 0.2)) {
                    showAdvanced.toggle()
                }
            } label: {
                HStack(spacing: Theme.Spacing.xs) {
                    Image(systemName: showAdvanced ? "chevron.down" : "chevron.right")
                        .font(.system(size: 10, weight: .medium))
                    Text("For contributors")
                        .font(Theme.Font.caption)
                }
                .foregroundStyle(Theme.Color.textMuted)
            }
            .buttonStyle(.plain)

            if showAdvanced {
                VStack(alignment: .leading, spacing: Theme.Spacing.md) {
                    Toggle(isOn: $setup.developmentMode) {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Install from local source")
                                .font(Theme.Font.body)
                                .foregroundStyle(Theme.Color.textPrimary)

                            Text("Uses your local code instead of the published package")
                                .font(Theme.Font.metadata)
                                .foregroundStyle(Theme.Color.textMuted)
                        }
                    }
                    .toggleStyle(.switch)

                    if setup.developmentMode {
                        VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                            Text("SOURCE FOLDER")
                                .font(.system(size: 11, weight: .medium))
                                .foregroundStyle(Theme.Color.textMuted)

                            HStack(spacing: Theme.Spacing.sm) {
                                TextField("Path to stratagem source", text: $setup.devModePath)
                                    .textFieldStyle(.plain)
                                    .font(Theme.Font.body)
                                    .foregroundStyle(Theme.Color.textPrimary)
                                    .padding(.horizontal, Theme.Spacing.md)
                                    .padding(.vertical, 10)
                                    .background(Theme.Color.surfaceSecondary)
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
                                        .frame(width: 36, height: 36)
                                }
                                .buttonStyle(.plain)
                                .foregroundStyle(Theme.Color.accent)
                            }
                        }
                    }
                }
                .padding(Theme.Spacing.md)
                .background(Theme.Color.surface)
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .strokeBorder(Theme.Color.border, lineWidth: 1)
                )
            }
        }
    }
}

#Preview {
    SetupView()
        .environmentObject(AppState())
}
