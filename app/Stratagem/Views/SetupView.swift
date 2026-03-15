import SwiftUI

struct SetupView: View {
    @StateObject private var setup = SetupManager()
    @EnvironmentObject private var appState: AppState
    @State private var showDevOptions = false
    @State private var showingFolderPicker = false
    @State private var showingDevFolderPicker = false

    var body: some View {
        VStack(spacing: 0) {
            Spacer()

            Group {
                switch setup.phase {
                case .welcome:
                    welcomeScreen
                case .checking, .installingUv, .installingStratagem, .needsUv:
                    setupScreen
                case .chooseDirectory:
                    directoryScreen
                case .ready:
                    readyScreen
                case .failed(let message):
                    failedScreen(message)
                }
            }
            .frame(maxWidth: 440)

            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Theme.Color.background)
    }

    // MARK: - Welcome

    private var welcomeScreen: some View {
        VStack(spacing: Theme.Spacing.xl) {
            VStack(spacing: Theme.Spacing.sm) {
                Text("Stratagem")
                    .font(.system(size: 28, weight: .bold))
                    .foregroundStyle(Theme.Color.textPrimary)

                Text("AI-powered market research")
                    .font(Theme.Font.body)
                    .foregroundStyle(Theme.Color.textSecondary)
            }

            Button {
                Task { await setup.startSetup() }
            } label: {
                Text("Get Started")
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
        .padding(.horizontal, Theme.Spacing.xl)
        .transition(.opacity)
    }

    // MARK: - Setup (checking + installing)

    private var setupScreen: some View {
        VStack(spacing: Theme.Spacing.lg) {
            VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                Text("Setting Up")
                    .font(.system(size: 20, weight: .bold))
                    .foregroundStyle(Theme.Color.textPrimary)

                Text("Preparing your research environment")
                    .font(Theme.Font.body)
                    .foregroundStyle(Theme.Color.textSecondary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            // Checklist — single border around group, dividers between
            VStack(spacing: 0) {
                checklistItem(
                    title: "Package Manager",
                    subtitle: uvSubtitle,
                    status: setup.uvStatus,
                    showAction: setup.phase == .needsUv
                )

                Divider()
                    .background(Theme.Color.border)

                checklistItem(
                    title: "Research Engine",
                    subtitle: stratagemSubtitle,
                    status: setup.stratagemStatus,
                    showAction: false
                )
            }
            .background(Theme.Color.surface)
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .strokeBorder(Theme.Color.border, lineWidth: 1)
            )

            // Progress text
            if !setup.statusText.isEmpty {
                HStack(spacing: Theme.Spacing.sm) {
                    if setup.phase == .installingUv || setup.phase == .installingStratagem
                        || setup.phase == .checking
                    {
                        ProgressView()
                            .scaleEffect(0.5)
                            .frame(width: 12, height: 12)
                    }

                    Text(setup.statusText)
                        .font(Theme.Font.metadata)
                        .foregroundStyle(Theme.Color.textMuted)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .padding(.horizontal, Theme.Spacing.xl)
        .transition(.opacity)
    }

    // MARK: - Directory

    private var directoryScreen: some View {
        VStack(spacing: Theme.Spacing.lg) {
            VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                Text("Research Folder")
                    .font(.system(size: 20, weight: .bold))
                    .foregroundStyle(Theme.Color.textPrimary)

                Text("Where should Stratagem save research data?")
                    .font(Theme.Font.body)
                    .foregroundStyle(Theme.Color.textSecondary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            // Folder path + picker
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

            // Developer options — progressive disclosure
            VStack(alignment: .leading, spacing: Theme.Spacing.md) {
                Button {
                    withAnimation(.easeInOut(duration: 0.2)) {
                        showDevOptions.toggle()
                    }
                } label: {
                    HStack(spacing: Theme.Spacing.xs) {
                        Image(systemName: showDevOptions ? "chevron.down" : "chevron.right")
                            .font(.system(size: 10, weight: .medium))
                        Text("Developer Options")
                            .font(Theme.Font.caption)
                    }
                    .foregroundStyle(Theme.Color.textMuted)
                }
                .buttonStyle(.plain)

                if showDevOptions {
                    devOptionsPanel
                }
            }

            // Continue
            Button {
                setup.completeSetup()
            } label: {
                Text("Continue")
                    .font(Theme.Font.body)
                    .fontWeight(.medium)
                    .foregroundStyle(canContinue ? .white : Theme.Color.textMuted)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(canContinue ? Theme.Color.accent : Theme.Color.surfaceSecondary)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            }
            .buttonStyle(.plain)
            .disabled(!canContinue)
        }
        .padding(.horizontal, Theme.Spacing.xl)
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
        .transition(.opacity)
    }

    // MARK: - Ready

    private var readyScreen: some View {
        VStack(spacing: Theme.Spacing.xl) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 48))
                .foregroundStyle(Theme.Color.accent)

            VStack(spacing: Theme.Spacing.xs) {
                Text("You're All Set")
                    .font(.system(size: 20, weight: .bold))
                    .foregroundStyle(Theme.Color.textPrimary)

                Text("Stratagem is ready for research")
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
        .padding(.horizontal, Theme.Spacing.xl)
        .transition(.opacity)
    }

    // MARK: - Failed

    private func failedScreen(_ message: String) -> some View {
        VStack(spacing: Theme.Spacing.lg) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 36))
                .foregroundStyle(.orange)

            VStack(spacing: Theme.Spacing.sm) {
                Text("Setup Interrupted")
                    .font(.system(size: 20, weight: .bold))
                    .foregroundStyle(Theme.Color.textPrimary)

                Text(message)
                    .font(Theme.Font.body)
                    .foregroundStyle(Theme.Color.textSecondary)
                    .multilineTextAlignment(.center)
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
        .padding(.horizontal, Theme.Spacing.xl)
        .transition(.opacity)
    }

    // MARK: - Checklist Item

    private func checklistItem(
        title: String,
        subtitle: String,
        status: CheckStatus,
        showAction: Bool
    ) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
            HStack(spacing: Theme.Spacing.md) {
                statusIcon(for: status)
                    .frame(width: 20, height: 20)

                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(Theme.Font.body)
                        .fontWeight(.medium)
                        .foregroundStyle(Theme.Color.textPrimary)

                    Text(subtitle)
                        .font(Theme.Font.caption)
                        .foregroundStyle(Theme.Color.textMuted)
                }

                Spacer()
            }

            // Inline install prompt for uv
            if showAction {
                VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
                    Text(
                        "Stratagem needs this to install and manage research packages."
                    )
                    .font(Theme.Font.caption)
                    .foregroundStyle(Theme.Color.textSecondary)
                    .padding(.leading, 36)

                    Button {
                        Task { await setup.installUv() }
                    } label: {
                        Text("Install uv")
                            .font(Theme.Font.body)
                            .fontWeight(.medium)
                            .foregroundStyle(.white)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 10)
                            .background(Theme.Color.accent)
                            .clipShape(RoundedRectangle(cornerRadius: 6))
                    }
                    .buttonStyle(.plain)
                    .padding(.leading, 36)
                }
            }
        }
        .padding(Theme.Spacing.md)
    }

    // MARK: - Dev Options Panel

    private var devOptionsPanel: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.md) {
            Toggle(isOn: $setup.developmentMode) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Development Mode")
                        .font(Theme.Font.body)
                        .foregroundStyle(Theme.Color.textPrimary)

                    Text("Install from local source with editable flag")
                        .font(Theme.Font.metadata)
                        .foregroundStyle(Theme.Color.textMuted)
                }
            }
            .toggleStyle(.switch)

            if setup.developmentMode {
                VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                    Text("SOURCE PATH")
                        .font(.system(size: 11, weight: .medium))
                        .foregroundStyle(Theme.Color.textMuted)

                    HStack(spacing: Theme.Spacing.sm) {
                        TextField("", text: $setup.devModePath)
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
                .padding(.leading, Theme.Spacing.md)
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

    // MARK: - Helpers

    @ViewBuilder
    private func statusIcon(for status: CheckStatus) -> some View {
        switch status {
        case .pending:
            Image(systemName: "circle")
                .font(.system(size: 16))
                .foregroundStyle(Theme.Color.textMuted)
        case .checking, .installing:
            ProgressView()
                .scaleEffect(0.6)
        case .installed:
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 16))
                .foregroundStyle(.green)
        case .missing:
            Image(systemName: "xmark.circle.fill")
                .font(.system(size: 16))
                .foregroundStyle(.orange)
        case .failed:
            Image(systemName: "exclamationmark.circle.fill")
                .font(.system(size: 16))
                .foregroundStyle(.red)
        }
    }

    private var canContinue: Bool {
        !setup.projectDirectory.isEmpty
            && (!setup.developmentMode || !setup.devModePath.isEmpty)
    }

    private var uvSubtitle: String {
        switch setup.uvStatus {
        case .pending: return "Not checked"
        case .checking: return "Checking..."
        case .installed: return "Ready"
        case .missing: return "Not installed"
        case .installing: return "Installing..."
        case .failed(let msg): return msg
        }
    }

    private var stratagemSubtitle: String {
        switch setup.stratagemStatus {
        case .pending: return "Waiting"
        case .checking: return "Checking..."
        case .installed: return "Ready"
        case .missing: return "Not installed"
        case .installing:
            return setup.statusText.isEmpty ? "Installing..." : setup.statusText
        case .failed(let msg): return msg
        }
    }
}

#Preview {
    SetupView()
        .environmentObject(AppState())
}
