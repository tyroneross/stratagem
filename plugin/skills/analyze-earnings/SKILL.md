---
name: analyze-earnings
description: Analyze company earnings by fetching SEC filings, extracting financial metrics, and producing financial analysis
trigger: When the user asks about earnings, financial results, revenue trends, margins, or specific company financial performance
---

# Earnings Analysis Workflow

You are performing financial earnings analysis using the Stratagem toolkit.

## Step 1: Identify Targets

From the user's question, determine:
- Which company/companies (by ticker symbol)
- Which time periods (latest quarter, annual, multi-year trend)
- Which metrics matter most (revenue, margins, EPS, guidance)

## Step 2: Fetch Filings

For each company:
1. `search_sec_filings` with the ticker and appropriate form type:
   - **10-K** for annual reports
   - **10-Q** for quarterly reports
   - **8-K** for material events
2. `download_sec_filing` for the specific filing(s) needed
3. `parse_pdf` to extract the content

## Step 3: Analyze

Use the **financial-analyst** subagent to:
- Extract key financial metrics
- Calculate growth rates and margins
- Compare to prior periods
- Summarize management guidance and commentary

## Step 4: Comparative Analysis (if multiple companies)

If comparing companies:
- Normalize metrics for comparison (revenue scale, margin percentages)
- Identify relative strengths and weaknesses
- Note industry-specific factors

## Step 5: Output

Generate a financial analysis report with:
- Headline numbers table
- Key takeaways (bulleted)
- Detailed analysis by section (revenue, profitability, cash flow, guidance)
- Risks and concerns
- Source citations

Save to `stratagem/reports/` and present key findings to the user.
