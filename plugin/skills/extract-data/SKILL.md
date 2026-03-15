---
name: extract-data
description: Extract structured data from documents, PDFs, spreadsheets, websites, and presentations
trigger: When the user asks to extract, parse, or pull data from specific files or URLs
---

# Data Extraction Workflow

You are performing structured data extraction using the Stratagem toolkit.

## Step 1: Identify Sources

Determine what the user wants to extract from:
- **Files**: PDF, Excel (.xlsx/.csv), PowerPoint (.pptx), Word (.docx)
- **URLs**: Web pages, articles, reports
- **Filing references**: SEC EDGAR filings by ticker

## Step 2: Select Tools

| Source | Primary Tool | Fallback |
|--------|-------------|----------|
| PDF | `parse_pdf` | `Read` (for text-heavy PDFs) |
| Excel/CSV | `read_spreadsheet` | — |
| PowerPoint | `read_pptx` | — |
| Web URL | `scrape_url` | `WebFetch` |
| Images in docs | `extract_images` | — |
| SEC filings | `search_sec_filings` → `download_sec_filing` → `parse_pdf` | — |

## Step 3: Extract

For each source:
1. Use the appropriate tool to get raw content
2. If the user specified what data points they want, focus extraction on those
3. Return structured data: markdown tables, key-value pairs, or bullet lists

## Step 4: Verify

Use the **data-extractor** subagent for high-stakes extraction that requires:
- Cross-reference verification
- Multi-pass extraction
- Quality scoring

## Output

Present extracted data in the most useful format:
- Tables for tabular data
- Key-value pairs for metadata
- Formatted text for narrative content

Save extractions to `stratagem/extractions/` for later use.
