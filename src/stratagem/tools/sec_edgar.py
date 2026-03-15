"""SEC EDGAR tools — search and download SEC filings.

Uses direct SEC REST API calls via sec_client.py (replaces edgartools).
"""

from typing import Any
from pathlib import Path

from claude_agent_sdk import tool

from stratagem.tools.sec_client import (
    resolve_ticker,
    get_filings,
    download_filing,
    filing_to_markdown,
)


@tool(
    "search_sec_filings",
    "Search SEC EDGAR for company filings. Returns filing metadata (date, type, URL) without downloading content. Use download_sec_filing to retrieve specific filings.",
    {
        "type": "object",
        "properties": {
            "ticker": {"type": "string", "description": "Company ticker symbol (e.g., 'AAPL', 'CSCO')"},
            "form_type": {"type": "string", "description": "SEC form type: 10-K, 10-Q, 8-K, etc.", "default": "10-K"},
            "limit": {"type": "integer", "description": "Maximum number of filings to return", "default": 5},
        },
        "required": ["ticker"],
    },
)
async def search_sec_filings(args: dict[str, Any]) -> dict[str, Any]:
    ticker = args["ticker"].upper()
    form_type = args.get("form_type", "10-K")
    limit = args.get("limit", 5)

    try:
        company = await resolve_ticker(ticker)
    except ValueError as e:
        return _error(str(e))
    except Exception as e:
        return _error(f"Failed to look up {ticker}: {e}")

    try:
        filings = await get_filings(company["cik"], form_type, limit)
    except Exception as e:
        return _error(f"Failed to search filings for {ticker}: {e}")

    sections = [
        f"# SEC Filings: {ticker} ({form_type})",
        f"**Company**: {company['name']}",
        f"**CIK**: {company['cik']}",
        "",
    ]

    for i, filing in enumerate(filings):
        sections.append(f"### [{i}] {filing['form']} — Filed {filing['filing_date']}")
        sections.append(f"Accession: {filing['accession_no']}")
        sections.append("")

    if not filings:
        sections.append(f"No {form_type} filings found for {ticker}.")

    sections.append(f"\n*Use `download_sec_filing` with ticker='{ticker}' and filing_index=N to download a specific filing.*")

    return {"content": [{"type": "text", "text": "\n".join(sections)}]}


@tool(
    "download_sec_filing",
    "Download a specific SEC filing to local filesystem. Use search_sec_filings first to find available filings, then use parse_pdf or Read to extract content.",
    {
        "type": "object",
        "properties": {
            "ticker": {"type": "string", "description": "Company ticker symbol"},
            "form_type": {"type": "string", "description": "SEC form type", "default": "10-K"},
            "filing_index": {"type": "integer", "description": "Index from search_sec_filings results", "default": 0},
            "output_dir": {"type": "string", "description": "Directory to save filing", "default": "stratagem/filings"},
        },
        "required": ["ticker"],
    },
)
async def download_sec_filing(args: dict[str, Any]) -> dict[str, Any]:
    ticker = args["ticker"].upper()
    form_type = args.get("form_type", "10-K")
    filing_index = args.get("filing_index", 0)
    output_dir = args.get("output_dir", "stratagem/filings")

    try:
        company = await resolve_ticker(ticker)
    except ValueError as e:
        return _error(str(e))
    except Exception as e:
        return _error(f"Failed to look up {ticker}: {e}")

    try:
        filings = await get_filings(company["cik"], form_type, limit=filing_index + 1)
    except Exception as e:
        return _error(f"Failed to search filings for {ticker}: {e}")

    if filing_index >= len(filings):
        return _error(f"Filing index {filing_index} not found. {len(filings)} {form_type} filings available.")

    filing = filings[filing_index]
    accession_no = filing["accession_no"]
    primary_doc = filing["primary_doc"]
    filed_date = filing["filing_date"]

    # Download the filing
    try:
        html_content = await download_filing(company["cik"], accession_no, primary_doc)
    except Exception as e:
        return _error(f"Failed to download filing: {e}")

    # Convert to markdown
    md_content = filing_to_markdown(html_content)

    # Save both HTML and markdown
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    html_filename = f"{ticker}_{form_type}_{filed_date}.html"
    md_filename = f"{ticker}_{form_type}_{filed_date}.md"

    html_path = out_dir / html_filename
    md_path = out_dir / md_filename

    html_path.write_text(html_content, encoding="utf-8")
    md_path.write_text(md_content, encoding="utf-8")

    return {"content": [{"type": "text", "text": "\n".join([
        f"# Downloaded: {ticker} {form_type}",
        f"**Filed**: {filed_date}",
        f"**Accession**: {accession_no}",
        f"**Saved to**: {html_path}",
        f"**Markdown**: {md_path}",
        f"**Size**: {html_path.stat().st_size:,} bytes (HTML), {md_path.stat().st_size:,} bytes (markdown)",
        "",
        f"Use `Read` tool to view the markdown at: {md_path}",
    ])}]}


def _error(msg: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": f"Error: {msg}"}], "isError": True}
