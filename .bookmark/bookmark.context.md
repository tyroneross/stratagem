# Stratagem — Session Context

## Session Date
2026-03-14

## What Was Done (This Session)

### Native macOS Desktop App (complete — all 6 phases)
Built `app/` directory with 20 Swift files — a native SwiftUI macOS app wrapping the existing Python backend via subprocess + SSE streaming.

**Phase 1: Scaffold + Backend**
- `project.yml` (XcodeGen), `StratagemApp.swift`, entitlements, `Theme.swift`
- `BackendManager.swift` — subprocess lifecycle, port finding, health check
- `SetupManager.swift` — first-launch Python/venv detection
- `SetupView.swift` — configuration UI with folder picker, dev mode toggle

**Phase 2: SSE Client + Models**
- `AgentNode.swift` — 11 agents across 4 phases (compile-time constants)
- `SSEEvent.swift` — typed enum parsing backend SSE events
- `SSEClient.swift` — actor-based URLSession.bytes streaming
- `ResearchState.swift`, `ResearchThread.swift` — state models

**Phase 3: Research Interface**
- `ResearchViewModel.swift` — orchestrates query → SSE → state
- `QueryInputView.swift` — textarea + model picker + Run/Stop (Cmd+Enter)
- `OutputView.swift` — streaming text with auto-scroll
- `ContentArea.swift` — stacks flow diagram + output + query input
- `MainView.swift` — HSplitView with sidebar toggle + backend status

**Phase 4: Flow Diagram**
- `FlowDiagramViewModel.swift` — agent state management
- `FlowDiagramView.swift` — Canvas-rendered 4-phase columns (Plan→Execute→Quality→Deliver) with pulse animation on active nodes, animated dash arrows

**Phase 5: Sidebar + Chat History**
- `ThreadStore.swift` — fetches from `/api/threads`
- `SidebarView.swift` — thread list + "New Research" button
- `ThreadRowView.swift` — three-line hierarchy with 2px leading accent selection

**Phase 6: DMG + Polish**
- `package-dmg.sh` — builds .app then creates DMG with Applications symlink
- `Assets.xcassets` — placeholder app icon manifest

### Verified
- ✅ `xcodegen generate` → Stratagem.xcodeproj created
- ✅ `xcodebuild -scheme Stratagem -configuration Release build` → BUILD SUCCEEDED
- ✅ App launched from build directory (setup screen shown)
- ✅ `stratagem --version` → 0.1.0 (CLI unchanged)
- ✅ Zero changes to `src/stratagem/`

### IBR Test — Not Applicable
- IBR validates web UIs via HTTP/browser — cannot scan native SwiftUI apps
- Could scan the Python backend's web UI (`stratagem --ui`) but that's the existing interface

## Current State
- **App**: Built and launched (Release, arm64, 1MB binary)
- **Location**: `app/` — 20 Swift files, project.yml, package-dmg.sh
- **Build**: `cd app && xcodegen generate && xcodebuild -scheme Stratagem build`
- **Tests**: Python tests unchanged (61 pass)
- **Git**: All app/ files uncommitted

## Files Created This Session
| Directory | Files | Purpose |
|-----------|-------|---------|
| `app/` | `project.yml`, `package-dmg.sh` | Build config, DMG packaging |
| `app/Stratagem/` | `StratagemApp.swift`, `Stratagem.entitlements` | App entry, security |
| `app/Stratagem/Theme/` | `Theme.swift` | Adaptive color tokens, fonts, spacing |
| `app/Stratagem/Models/` | `AgentNode`, `SSEEvent`, `ResearchState`, `ResearchThread` | Data models |
| `app/Stratagem/Services/` | `BackendManager`, `SetupManager`, `SSEClient`, `ThreadStore` | Backend/networking |
| `app/Stratagem/ViewModels/` | `ResearchViewModel`, `FlowDiagramViewModel` | State management |
| `app/Stratagem/Views/` | `MainView`, `SetupView`, `ContentArea`, `FlowDiagramView`, `QueryInputView`, `OutputView`, `SidebarView`, `ThreadRowView` | UI |
| `app/Stratagem/Assets.xcassets/` | App icon placeholder | Assets |

## Key Decisions
- Swift 5.9 (not 6.0) — avoids strict concurrency issues with subprocess management
- Non-sandboxed — needs Process spawning + filesystem access
- XcodeGen for project generation (same pattern as FlowDoro)
- Backend launched as `uv run python -m stratagem --ui --port 8420`
- SSE client uses URLSession.bytes (zero dependencies)
- All 11 agents hardcoded (no /api/graph call needed)
- Canvas rendering for flow diagram (same approach as web UI SVG)

## Pending / Not Done
1. **Live test against running backend** — app launched but backend needs stratagem project dir
2. **App icon** — placeholder manifest, no actual images
3. **Commit all changes** — app/ directory + memory updates
4. **DMG packaging** — `bash app/package-dmg.sh` (untested)

## Architecture
```
app/
  project.yml                     # XcodeGen → Stratagem.xcodeproj
  package-dmg.sh                  # DMG build script
  Stratagem/
    StratagemApp.swift            # @main, AppState, window config
    Stratagem.entitlements        # Non-sandboxed + unsigned memory
    Theme/Theme.swift             # Colors, fonts, spacing (8pt grid)
    Models/                       # AgentNode, SSEEvent, ResearchState, ResearchThread
    Services/                     # BackendManager, SetupManager, SSEClient, ThreadStore
    ViewModels/                   # ResearchViewModel, FlowDiagramViewModel
    Views/                        # MainView, SetupView, ContentArea, FlowDiagramView,
                                  # QueryInputView, OutputView, SidebarView, ThreadRowView
    Assets.xcassets/              # App icon (placeholder)
```
