"""SEC EDGAR tools — search and download SEC filings."""

from typing import Any
from pathlib import Path

from claude_agent_sdk import tool


def _ensure_edgar_identity():
    """Set SEC EDGAR User-Agent identity if not already configured."""
    try:
        from edgar import set_identity
        set_identity("Stratagem Research stratagem@example.com")
    except Exception:
        pass


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
        from edgar import Company
    except ImportError:
        return _error("edgartools not installed. Run: pip install edgartools")

    _ensure_edgar_identity()

    try:
        company = Company(ticker)
    except Exception as e:
        return _error(f"Failed to look up {ticker}: {e}")

    try:
        filings = company.get_filings(form=form_type)
    except Exception as e:
        return _error(f"Failed to search filings for {ticker}: {e}")

    sections = [
        f"# SEC Filings: {ticker} ({form_type})",
        f"**Company**: {company.name}",
        f"**CIK**: {company.cik}",
        "",
    ]

    results = []
    for i, filing in enumerate(filings):
        if i >= limit:
            break
        info = {
            "index": i,
            "form": str(getattr(filing, "form", form_type)),
            "filed": str(getattr(filing, "filing_date", "unknown")),
            "accession": str(getattr(filing, "accession_no", "unknown")),
        }
        results.append(info)
        sections.append(f"### [{i}] {info['form']} — Filed {info['filed']}")
        sections.append(f"Accession: {info['accession']}")
        sections.append("")

    if not results:
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
            "output_dir": {"type": "string", "description": "Directory to save filing", "default": ".stratagem/filings"},
        },
        "required": ["ticker"],
    },
)
async def download_sec_filing(args: dict[str, Any]) -> dict[str, Any]:
    ticker = args["ticker"].upper()
    form_type = args.get("form_type", "10-K")
    filing_index = args.get("filing_index", 0)
    output_dir = args.get("output_dir", ".stratagem/filings")

    try:
        from edgar import Company
    except ImportError:
        return _error("edgartools not installed. Run: pip install edgartools")

    _ensure_edgar_identity()

    try:
        company = Company(ticker)
        filings = company.get_filings(form=form_type)
    except Exception as e:
        return _error(f"Failed to look up filings for {ticker}: {e}")

    # Get the specific filing
    target = None
    count = 0
    for count_i, filing in enumerate(filings):
        count = count_i + 1
        if count_i == filing_index:
            target = filing
            break

    if target is None:
        return _error(f"Filing index {filing_index} not found. {count} {form_type} filings available.")

    # Create output directory
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    filed_date = str(getattr(target, "filing_date", "unknown"))
    accession = str(getattr(target, "accession_no", "unknown")).replace("-", "")

    # Try to get the filing document
    try:
        # Try to get the HTML/text content of the filing
        filing_obj = target.obj()

        # Save as HTML if available
        html_content = None
        if hasattr(filing_obj, "html"):
            html_content = filing_obj.html()
        elif hasattr(filing_obj, "text"):
            html_content = filing_obj.text()
        elif hasattr(filing_obj, "markdown"):
            html_content = filing_obj.markdown()

        if html_content:
            filename = f"{ticker}_{form_type}_{filed_date}.html"
            filepath = out_dir / filename
            filepath.write_text(html_content, encoding="utf-8")

            return {"content": [{"type": "text", "text": "\n".join([
                f"# Downloaded: {ticker} {form_type}",
                f"**Filed**: {filed_date}",
                f"**Accession**: {accession}",
                f"**Saved to**: {filepath}",
                f"**Size**: {filepath.stat().st_size:,} bytes",
                "",
                f"Use `Read` tool to view the content at: {filepath}",
            ])}]}

    except Exception as e:
        # Primary download method failed, try fallback approaches
        primary_error = str(e)

    # Fallback: try to get attachments/documents
    try:
        documents = list(target.attachments) if hasattr(target, "attachments") else []
        if not documents and hasattr(target, "documents"):
            documents = list(target.documents)

        saved_files = []
        for doc in documents[:5]:  # Limit to first 5 documents
            try:
                doc_name = getattr(doc, "document", getattr(doc, "filename", f"doc_{len(saved_files)}"))
                doc_content = doc.download() if hasattr(doc, "download") else str(doc)

                filename = f"{ticker}_{form_type}_{filed_date}_{doc_name}"
                # Sanitize filename
                filename = "".join(c for c in filename if c.isalnum() or c in "._-")
                filepath = out_dir / filename

                if isinstance(doc_content, bytes):
                    filepath.write_bytes(doc_content)
                else:
                    filepath.write_text(str(doc_content), encoding="utf-8")

                saved_files.append(str(filepath))
            except Exception:
                continue  # Skip individual documents that fail to download

        if saved_files:
            sections = [
                f"# Downloaded: {ticker} {form_type}",
                f"**Filed**: {filed_date}",
                f"**Files saved**:",
            ]
            for f in saved_files:
                sections.append(f"  - {f}")
            sections.append("")
            sections.append("Use `parse_pdf` or `Read` to extract content from these files.")
            return {"content": [{"type": "text", "text": "\n".join(sections)}]}

    except Exception:
        pass  # Attachment download failed, try text fallback

    # Last resort: save whatever text representation we can get
    try:
        text_repr = str(target)
        filename = f"{ticker}_{form_type}_{filed_date}.txt"
        filepath = out_dir / filename
        filepath.write_text(text_repr, encoding="utf-8")

        return {"content": [{"type": "text", "text": "\n".join([
            f"# Downloaded: {ticker} {form_type}",
            f"**Filed**: {filed_date}",
            f"**Saved to**: {filepath} (text representation)",
            "",
            "Note: Could not download the full filing document. The text representation has been saved.",
            f"Use `Read` to view: {filepath}",
        ])}]}
    except Exception as e:
        return _error(f"Failed to download filing: {e}")


def _error(msg: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": f"Error: {msg}"}], "isError": True}
