# Stratagem — Session Context

## Session Date
2026-03-12

## What Was Done (This Session)

### CLI Agent Process Display (complete)
- Updated `_print_message()` in `agent.py` with colored ANSI output
- Shows: `▸ agent-name [model] action` when an agent starts
- Shows: `✓ agent-name done` when complete
- Non-agent tool calls shown dimly as `[tool-name]`
- Duration formatted as seconds or minutes
- Model colors: opus=yellow, sonnet=blue, haiku=green

### Speed Optimization (complete)
- Added `--fast` flag: uses Sonnet for orchestrator instead of Opus (~2-3x faster)
- Updated interactive REPL to show current mode: `[fast]`, `[opus]`, etc.
- UI dropdown simplified: Opus (default), Sonnet (fast), Haiku (fastest)

### UI Fixes (complete)
- Fixed stale process on port 8420
- Removed duplicate Opus option from model selector
- Verified UI serves correctly with proper dark/light mode, progress panel, agent chips
- Health endpoint: `/api/health` returns `{"status": "ok"}`

### Previous Session Work (carried forward)
- Design agent with Calm Precision principles
- Interactive REPL mode (no quotes needed)
- Research planner with intent identification + follow-ups
- Progress bar + agent chips in UI with model tags
- Fixed CLAUDECODE env var blocking (both agent.py and __main__.py)
- Architecture review: fixed tool access gaps, downgraded 3 agents to Sonnet
- NavGator integration (21 components, 29 connections)
- Bug fixes, DOCX support, live tests

## Current State
- **Tests**: 17/17 passing (integration tests)
- **Live tests**: 9/9 passing (requires network)
- **UI**: Running on http://localhost:8420 (start: `stratagem --ui`)
- **CLI**: `stratagem` command available globally via symlink
- **Git**: Uncommitted changes in agent.py, __main__.py, ui.py

## Files Modified This Session
| File | Change |
|------|--------|
| `src/stratagem/agent.py` | Added CLI agent display with ANSI colors, _AGENT_MODELS, _AGENT_ACTIONS, _extract_agent_name |
| `src/stratagem/__main__.py` | Added `--fast` flag, mode display in REPL header |
| `src/stratagem/ui.py` | Fixed model selector (3 options: Opus/Sonnet/Haiku with labels) |

## Architecture Summary
- **12 agents**: 1 control (Opus) + 11 subagents (9 Sonnet, 2 Opus)
- **9 MCP tools**: parse_pdf, scrape_url, read_spreadsheet, read_pptx, create_pptx, extract_images, search_sec_filings, download_sec_filing, create_report
- **4 phases**: Plan → Execute → Validate → Report
- **Frameworks**: Pyramid Principle, Calm Precision content design

## Pending / Not Done
1. **Run actual research query** — from terminal:
   ```bash
   cd ~/Desktop/git-folder/stratagem && source .venv/bin/activate
   stratagem --fast what are the best practices for AI architecture
   ```
2. **IBR scan** — validate UI with Interface Built Right
3. **Calm Precision deep audit** — apply full audit checklist to UI
4. **Commit changes** — agent display, --fast flag, UI fixes
5. **Architecture review remaining**: C1 (framework docs unused), I1 (standardize prompts to XML), I6/I7 (DOCX/HTML markdown handling)

## Key Decisions
- `--fast` uses Sonnet orchestrator (2-3x faster, slightly less capable)
- CLI shows agent activity with colored ANSI — no extra dependencies
- Model selector in UI shows speed context: "fast", "fastest"
- Agent process display in CLI mirrors UI agent chips conceptually

## CLI Usage
```bash
stratagem                           # Interactive REPL (opus)
stratagem --fast                    # Interactive REPL (sonnet, faster)
stratagem what is the market for X  # Direct query
stratagem --ui                      # Web UI on localhost:8420
stratagem --architecture            # Generate NavGator data
```
