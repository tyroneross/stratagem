# Stratagem — Codex Project Guide

Market research plugin: decompose a research question, gather data in parallel from web pages, PDFs, spreadsheets, presentations, Word documents, and SEC EDGAR filings, then synthesize the results into a report or slide deck. The plugin ships as an MCP server (`stratagem.server`) plus a `research-orchestrator` agent and four workflow skills. All MCP tools are host-neutral — callable from Codex, Claude Code, or any MCP-compatible runtime.

## Installation

```
/plugins install ~/dev/git-folder/stratagem/plugin
```

The MCP server starts automatically via `uv run python -m stratagem.server` from the repo root.

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

## Agents and skills

| Component | Kind | Purpose |
|-----------|------|---------|
| `research-orchestrator` | Agent (Opus) | Decomposes research questions, fans out extraction work, directs synthesis, routes final output to `create_report` or `create_pptx` |
| `research` | Skill | Full multi-source market / company / industry research workflow → executive-ready report |
| `analyze-earnings` | Skill | SEC filing search + download + financial metric extraction for earnings analysis |
| `extract-data` | Skill | Structured data extraction from PDFs, spreadsheets, presentations, documents, or URLs |
| `flowchart` | Skill | Process / workflow / system architecture visualization → PowerPoint slide deck via `create_pptx` |

The `research-orchestrator` agent holds the full tool allowlist. Skills are prompt-level workflows that route through the same MCP tools — use them from Claude Code; invoke tools directly from Codex.
