---
name: research
description: Conduct market research by gathering, analyzing, and synthesizing data from multiple sources into executive-ready reports
trigger: When the user asks to research a market, company, industry trend, competitive landscape, or any topic requiring multi-source analysis
---

# Research Workflow

You are conducting market research using the Stratagem toolkit. Follow this workflow:

## Step 1: Decompose the Question

Break the research question into:
- **Target entities** (companies, products, markets)
- **Data points needed** (revenue, market share, trends, competitive position)
- **Source types required** (SEC filings, news articles, industry reports, financial data)

## Step 2: Gather Data

Use the appropriate tools for each source type:

**For SEC filings:**
1. `search_sec_filings` to find available filings
2. `download_sec_filing` to save specific filings locally
3. `parse_pdf` or `Read` to extract content

**For web sources:**
- `scrape_url` to extract article content
- Use `WebSearch` to find relevant URLs first

**For documents:**
- `parse_pdf` for PDF files
- `read_spreadsheet` for Excel/CSV data
- `read_pptx` for presentations

## Step 3: Extract & Verify

Use the **data-extractor** subagent for structured data extraction with verification passes.

## Step 4: Synthesize

Use the **research-synthesizer** subagent to combine findings into a coherent narrative, or the **executive-synthesizer** for a concise executive brief.

## Step 5: Generate Report

Use `create_report` to produce the final output:
- Default: markdown report saved to `.stratagem/reports/`
- Option: PPTX for presentations
- Option: HTML for web-ready output

## Output

Save the final report to `.stratagem/reports/` and present a summary to the user with key findings.
