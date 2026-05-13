# Handoff — Stratagem Mac App Debugging

**For:** Codex
**From:** Claude (session 2026-04-26)
**Repo:** `/Users/tyroneross/dev/git-folder/stratagem`
**App:** `/Users/tyroneross/dev/git-folder/stratagem/app` (SwiftUI macOS shell that spawns a Python backend)

## What you're being asked to investigate

Three symptoms, in priority order:

1. **🔴 HIGH — Mac app does not work when user enters text.** User typed into the input field; nothing happened (no submit, no response, no error visible to them). Root cause unknown. Reproduction is "open the app, type, observe nothing".

2. **🟡 MED — Mac app feels slow.** No quantified metric yet. User is using the Aurora Deep web UI hosted in (presumably) a WKWebView. Slowness could be CSS-driven (heavy `backdrop-filter` + animated `body::before` gradient), backend startup, or SSE rendering. Needs measurement, not guessing.

3. **⚪ LOW — Pre-existing Swift 6 concurrency warnings** at `app/Stratagem/Services/BackendManager.swift:97` and `:101`. Out of scope right now per the user — flag for a future Swift 6 sweep, do not fix in this pass.

## Architecture snapshot (verified earlier this session)

- **SwiftUI shell** (`app/Stratagem/`) launches at app start, instantiates `BackendManager`, which spawns:
  - `python -m stratagem --ui --port 8420`
  - cwd: `~/Documents/Stratagem` (auto-created on demand — see `BackendManager.swift:42-47`, fix landed earlier today)
  - python: `UserDefaults.standard.string(forKey: "pythonPath")` → managed venv at `~/Library/Application Support/Stratagem/venv/...`
- **Backend** (`src/stratagem/ui.py`, ~1400 lines, single embedded HTML) serves the web UI at `http://localhost:8420`. Recently migrated to Aurora Deep design system: glass surfaces, `backdrop-filter: blur()`, ambient gradient animation on `body::before`, indigo accent.
- **Wire-up** between Swift and the web UI is the missing piece you need to confirm — likely a `WKWebView` loading `http://localhost:8420`, but the Swift view files have not been read yet this session.

## Key files

```
app/Stratagem/
  StratagemApp.swift              — App entry
  Views/
    MainView.swift                — Primary container (most likely WKWebView host or split layout)
    ContentArea.swift
    QueryInputView.swift          — ⭐ Likely where text entry lives if input is native SwiftUI
    OutputView.swift
    SidebarView.swift
    SetupView.swift
    FlowDiagramView.swift
    ThreadRowView.swift
  Services/
    BackendManager.swift          — Spawns python backend; lines 97,101 = Swift6 warnings (skip)
    SSEClient.swift               — ⭐ If text entry POSTs to backend and streams via SSE, check here
    SetupManager.swift
    ThreadStore.swift
  Models/
    SSEEvent.swift                — SSE event shape
    ResearchState.swift
    ResearchThread.swift
    AgentNode.swift

src/stratagem/ui.py               — Embedded HTML/CSS/JS (Aurora Deep) served at :8420
```

## Hypotheses — text entry not working

Read the files above before speculating, but here's the ranked starting set:

1. **Native SwiftUI `TextField` in `QueryInputView.swift` not wired to a submit handler.** Check for `.onSubmit { ... }` or button bindings. If the binding goes to a `@State` but never calls `BackendManager` or `SSEClient`, nothing leaves the app.
2. **POST endpoint mismatch.** If the input POSTs to `http://localhost:8420/api/...`, confirm the route exists in `src/stratagem/ui.py` and matches the path the Swift code targets.
3. **WKWebView keyboard focus issue** (if the input is inside the embedded web UI): on macOS, WKWebView sometimes loses first-responder status; the user types but events never reach the form. Repro: click directly inside the field within the webview before typing.
4. **SSE never starts / errors silently.** `SSEClient.swift` may swallow errors. Check for `print()` only, no UI surface.
5. **Backend not reachable.** Backend is supposed to spawn on launch; check `BackendManager.isRunning` actually flips true. The earlier missing-cwd bug was fixed today, but `~/Library/Application Support/Stratagem/venv` may not exist on a fresh box.

## Hypotheses — slowness

1. **Aurora Deep CSS in `src/stratagem/ui.py`** — animated `body::before` (4 radial-gradients, `aurora-drift`) + many `backdrop-filter: blur(Npx)` surfaces. WKWebView on macOS pays a real GPU cost for this. Measure: open Safari Web Inspector against `http://localhost:8420`, record a timeline, look for compositor-thread frames > 16ms.
2. **Backend cold start.** Python imports the agent SDK; first request may stall. `BackendManager` polls health every 500ms × 30 = 15s window. If the user types before health check passes, nothing happens.
3. **SSE re-render storms.** If JS handlers in `ui.py` rebuild large DOM subtrees per event, that compounds with backdrop-filter cost.

## Recommended approach for Codex

1. **Read first, don't fix:** `QueryInputView.swift`, `MainView.swift`, `SSEClient.swift`, then enough of `ui.py` to find the matching POST route and the SSE event handlers.
2. **Reproduce:** Launch the app from `/Users/tyroneross/dev/git-folder/stratagem/app/Open\ Stratagem.app`. Open Console.app, filter for `Stratagem` and `python`. Type a query. Capture: Swift logs, python stderr, and (if WKWebView) attach Safari Web Inspector to the embedded webview (`Develop ▸ <hostname> ▸ localhost`).
3. **Verify the POST path** by tailing the python process and watching for the request when text is submitted. No request = Swift side never sent it. Request received but no response = backend bug.
4. **Only then propose a fix.** Minimal, root-cause, no mock data, no scope expansion. Per repo rules: attack the root cause, no defensive layers.

## Constraints (from user / CLAUDE.md)

- ❌ NO mock data anywhere in the real app. Demo-only behavior must live in a separate route or app, not gated behind `?demo=1` or env flags.
- ❌ Don't fix the Swift 6 warnings unless you happen to need to touch those exact lines for the real bug.
- ✅ Attack root cause directly. No defensive workarounds.
- ✅ Minimal effective action. No refactors.
- ✅ Verify with the actual app, not just unit tests. Type into the field, watch it work.
- ✅ Status markers (✅ verified / ⚠️ untested / ❓ uncertain) when reporting.

## What's already done this session (don't redo)

- `BackendManager.swift` cwd auto-create fix landed and verified end-to-end (deleted `~/Documents/Stratagem`, relaunched, backend came up in 2s).
- Aurora Deep web UI migration shipped, IBR contrast pass.
- Path migration `Desktop/git-folder` → `dev/git-folder` complete (UserDefaults, `_stratagem.pth`, SetupManager candidates).
- Phase A backend fixes (artifact tracking, auto-thread, force_report_critic) merged and tested.

## Bookmark / state

- Last snapshot: `SNAP_20260426_233841` (manual)
- Bookmark context: `app/.bookmark/bookmark.context.md`
- Tests: 85 passing, 7 pre-existing failures unrelated.

Good luck.
