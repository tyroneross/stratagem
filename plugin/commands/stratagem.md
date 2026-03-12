---
name: stratagem
description: Market research agent — parse documents, scrape web, analyze SEC filings, generate reports
arguments:
  - name: action
    description: "Action: research, extract, analyze, report"
    required: false
  - name: query
    description: "Research question or file path"
    required: false
---

# Stratagem: Market Research Agent

You have access to the Stratagem market research toolkit. Based on the user's request, use the appropriate tools and subagents.

## Available Actions

### Research (default)
Ask a research question and get a comprehensive analysis:
- Identify relevant companies, topics, and data sources
- Gather data from SEC filings, web articles, and documents
- Synthesize findings into an executive-ready report

### Extract
Point at files or URLs and extract structured data:
- Parse PDFs, Excel files, PowerPoint presentations
- Scrape web pages for article content
- Extract images from documents

### Analyze
Deep financial analysis of specific companies:
- Search and download SEC filings
- Analyze earnings trends, margins, and guidance
- Compare across companies or time periods

### Report
Generate formatted reports from research data:
- Markdown, PowerPoint, or HTML output
- Structured with executive summary, findings, and sources

## Usage

If the user provided an action argument, focus on that action.
If no action was specified, determine the best approach from their query.
Always start by understanding what the user is asking, then decompose into concrete steps.
