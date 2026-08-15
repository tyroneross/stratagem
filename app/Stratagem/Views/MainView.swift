import SwiftUI

struct MainView: View {
    @StateObject private var backendManager = BackendManager()
    @StateObject private var viewModel = ResearchViewModel()
    @StateObject private var threadStore = ThreadStore()
    @State private var selectedThreadId: String?
    @State private var sidebarVisible = true

    var body: some View {
        HSplitView {
            if sidebarVisible {
                SidebarView(
                    threadStore: threadStore,
                    selectedThreadId: $selectedThreadId,
                    onNewResearch: {
                        selectedThreadId = nil
                        viewModel.reset()
                    }
                )
                .frame(minWidth: 220, idealWidth: 260, maxWidth: 300)
            }

            ContentArea(
                viewModel: viewModel,
                backendManager: backendManager,
                currentThreadId: selectedThreadId
            )
            .frame(minWidth: 600)
        }
        .background(Theme.Color.background)
        .toolbar {
            ToolbarItem(placement: .navigation) {
                Button {
                    withAnimation(.easeInOut(duration: 0.2)) {
                        sidebarVisible.toggle()
                    }
                } label: {
                    Image(systemName: "sidebar.left")
                }
            }

            ToolbarItem(placement: .automatic) {
                HStack(spacing: Theme.Spacing.xs) {
                    Image(systemName: backendManager.isRunning ? "checkmark.circle.fill" : "clock.fill")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(toolbarStatusColor)

                    Text(toolbarStatusLabel)
                        .font(Theme.Font.metadata)
                        .foregroundStyle(Theme.Color.textMuted)
                }
            }
        }
        .task {
            await backendManager.start()
        }
        .onChange(of: backendManager.isRunning) { _, isRunning in
            if isRunning {
                threadStore.fetchThreads(baseURL: backendManager.baseURL)
            }
        }
    }

    private var toolbarStatusLabel: String {
        if backendManager.isRunning {
            return "Backend ready"
        }
        return backendManager.errorMessage == nil ? "Starting backend" : "Backend issue"
    }

    private var toolbarStatusColor: Color {
        if backendManager.isRunning {
            return Theme.Color.success
        }
        return backendManager.errorMessage == nil ? Theme.Color.warning : Theme.Color.danger
    }
}
