# Stratagem — Codex Project Guide

Market research agent: decompose a research question, gather data in parallel from web pages, PDFs, spreadsheets, presentations, Word documents, and SEC EDGAR filings, then synthesize the results into a report or slide deck. It ships as a Python package (`src/stratagem`) built on the Claude Agent SDK: a CLI, a local web UI, a SwiftUI macOS shell (`app/`), and an MCP server (`stratagem.server`) exposing the tools below. All MCP tools are host-neutral — callable from Codex, Claude Code, or any MCP-compatible runtime.

Plugin packaging (`plugin/` with `plugin.json`, `.mcp.json`, agent + skill files) was removed in `b7538d9`; there is no `/plugins install` path anymore.

## Running

```
uv sync
uv run stratagem "Compare NVIDIA and AMD AI accelerator revenue"   # one-shot CLI (--model, --fast, --thread, --topic, --input)
uv run stratagem --ui                                                # local web UI + SSE at http://localhost:8420
uv run python -m stratagem.server                                    # standalone stdio MCP server
```

To use the tools from Codex or another MCP host, register the server as a stdio MCP server with command `uv run python -m stratagem.server` and the repo root as its working directory.

## Capabilities (MCP tools)

| Tool | Purpose |
|------|---------|
| `parse_pdf` | Extract text, tables, and images from a PDF file; returns markdown-formatted content |
| `scrape_url` | Fetch a URL and return its main content as clean markdown; handles articles, news, and general web pages |
| `read_spreadsheet` | Read an Excel (.xlsx) or CSV file; returns contents as markdown tables with metadata |
| `read_pptx` | Read a PowerPoint file; extracts text, speaker notes, and optionally images per slide |
| `create_pptx` | Create a PowerPoint presentation from structured slide data (title, bullet, table, image slides) |
| `read_docx` | Read a Word document (.docx); extracts text, tables, and metadata as markdown |
| `extract_images` | Extract embedded images from PDF, PPTX, or DOCX files; returns metadata and base64 data |
| `search_sec_filings` | Search SEC EDGAR for company filings; returns filing metadata (date, type, URL) without downloading |
| `download_sec_filing` | Download a specific SEC filing to the local filesystem for subsequent parsing |
| `create_report` | Generate a formatted report from structured sections; outputs markdown, PowerPoint, Word, or HTML |
| `create_spreadsheet` | Create an Excel workbook from structured data; supports multiple sheets with headers and rows |
| `create_specialist` | Spawn a temporary specialist agent to handle a capability gap identified during research planning |
| `record_observation` | Record a research observation — source reliability, verified finding, process learning, or agent quality note |

Read-only tools (`parse_pdf`, `scrape_url`, `read_spreadsheet`, `read_pptx`, `read_docx`) are response-cached per unique input to avoid duplicate API calls within a session.

## Workflow

A Codex agent replicates the orchestration loop natively:

```
Research Question
    ↓
Decompose → entities / topics (Company A, Company B, Topic X)
    ↓
Parallel gather (fan out):
  ├→ search_sec_filings → download_sec_filing → parse_pdf   (for public companies)
  ├→ scrape_url                                              (web sources)
  ├→ parse_pdf / read_spreadsheet / read_pptx / read_docx   (uploaded docs)
  └→ extract_images                                          (visual assets)
    ↓
Save intermediate extractions to stratagem/extractions/ as markdown files
    ↓
Synthesize:
  ├→ financial metrics analysis
  └→ narrative synthesis
    ↓
create_report → stratagem/reports/   (md / html / docx / pptx)
create_spreadsheet → stratagem/reports/   (data tables)
```

Intermediate results use file-based handoffs (`stratagem/extractions/`), not context passing. Always verify each file was created (non-zero size at the expected absolute path) before claiming success.

## Subagents

The control agent (`src/stratagem/agent.py`, Opus by default) holds the full tool allowlist and delegates to the 12 subagents defined in `src/stratagem/subagents/definitions.py`; each subagent's prompt lives in `src/stratagem/subagents/prompts/<snake_case_name>.md` (e.g. `source_verifier.md`).

| Subagent | Purpose |
|----------|---------|
| `research-planner` | Decompose the question into a task plan before gathering |
| `data-extractor` | Extract and verify data from PDFs, websites, spreadsheets, presentations |
| `financial-analyst` | SEC filings, earnings, and financial-statement analysis |
| `research-synthesizer` | Cross-source narrative synthesis with citations |
| `executive-synthesizer` | Executive-ready briefs with strategic framing |
| `source-verifier` | Verify claims against cited sources; flag unsupported or stale claims |
| `report-critic` | Score report completeness, accuracy, structure, depth, actionability |
| `plan-validator` | Spot-check subagent output for scope/quality/source drift |
| `flowchart-architect` | Process / architecture visualization as PowerPoint via `create_pptx` |
| `design-agent` | Visual structure and layout for deliverables |
| `prompt-optimizer` | Refine research prompts for accuracy and specificity |
| `after-action-analyst` | Structured after-action review after each run |

From Codex, invoke the MCP tools directly and reuse the prompt files as role instructions; the orchestration loop is not exposed as a plugin agent or skill.
