"""Thin async SEC EDGAR client using httpx.

Replaces edgartools dependency. Hits public SEC REST APIs directly:
- Company tickers JSON for ticker→CIK resolution
- Submissions endpoint for filing metadata
- Archives for filing document download
- BeautifulSoup for HTML→markdown conversion

SEC rate limit: 10 req/sec. We use 8 req/sec with exponential backoff.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

CACHE_DIR = Path(".stratagem/cache")
TICKERS_CACHE = CACHE_DIR / "company_tickers.json"
CACHE_MAX_AGE = 86400  # 1 day

USER_AGENT = "Stratagem Research stratagem@example.com"
BASE_HEADERS = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}

# Rate limiting: max 8 requests per second
_last_request_time = 0.0
_MIN_INTERVAL = 0.125  # 1/8 second


async def _rate_limit():
    """Enforce rate limit by sleeping if needed."""
    global _last_request_time
    now = time.monotonic()
    elapsed = now - _last_request_time
    if elapsed < _MIN_INTERVAL:
        await asyncio.sleep(_MIN_INTERVAL - elapsed)
    _last_request_time = time.monotonic()


async def _get(url: str, client: httpx.AsyncClient | None = None) -> httpx.Response:
    """Rate-limited GET with retry on 429/5xx."""
    await _rate_limit()
    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(headers=BASE_HEADERS, timeout=30.0, follow_redirects=True)
    try:
        for attempt in range(3):
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp
            if resp.status_code in (429, 500, 502, 503):
                await asyncio.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
        return resp  # Return last response even if not 200
    finally:
        if own_client:
            await client.aclose()


async def _load_tickers_map() -> dict[str, dict]:
    """Load ticker→company mapping. Caches to disk for 24h."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if TICKERS_CACHE.exists():
        age = time.time() - TICKERS_CACHE.stat().st_mtime
        if age < CACHE_MAX_AGE:
            data = json.loads(TICKERS_CACHE.read_text())
            return _index_tickers(data)

    resp = await _get("https://www.sec.gov/files/company_tickers.json")
    resp.raise_for_status()
    data = resp.json()
    TICKERS_CACHE.write_text(json.dumps(data))
    return _index_tickers(data)


def _index_tickers(data: dict) -> dict[str, dict]:
    """Build ticker→{cik, name, ticker} lookup from SEC JSON."""
    result = {}
    for entry in data.values():
        ticker = entry.get("ticker", "").upper()
        if ticker:
            result[ticker] = {
                "cik": int(entry["cik_str"]),
                "name": entry.get("title", ""),
                "ticker": ticker,
            }
    return result


async def resolve_ticker(ticker: str) -> dict[str, Any]:
    """Resolve ticker symbol to CIK and company name.

    Returns: {"cik": int, "name": str, "ticker": str}
    Raises: ValueError if ticker not found.
    """
    ticker = ticker.upper()
    tickers_map = await _load_tickers_map()
    if ticker not in tickers_map:
        raise ValueError(f"Ticker '{ticker}' not found in SEC database")
    return tickers_map[ticker]


async def get_filings(
    cik: int,
    form_type: str = "10-K",
    limit: int = 5,
) -> list[dict[str, str]]:
    """Fetch filing metadata for a CIK.

    Returns list of dicts: [{form, filing_date, accession_no, primary_doc}]
    """
    url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
    resp = await _get(url)
    resp.raise_for_status()
    data = resp.json()

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])

    results = []
    for i, form in enumerate(forms):
        if form != form_type:
            continue
        results.append({
            "form": form,
            "filing_date": dates[i] if i < len(dates) else "unknown",
            "accession_no": accessions[i] if i < len(accessions) else "unknown",
            "primary_doc": primary_docs[i] if i < len(primary_docs) else "unknown",
        })
        if len(results) >= limit:
            break

    return results


async def download_filing(cik: int, accession_no: str, primary_doc: str) -> str:
    """Download a filing document and return raw HTML content.

    Args:
        cik: Company CIK number
        accession_no: Accession number (with dashes, e.g. '0000320193-24-000123')
        primary_doc: Primary document filename from filing metadata
    """
    accession_nodash = accession_no.replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodash}/{primary_doc}"
    resp = await _get(url)
    resp.raise_for_status()
    return resp.text


def filing_to_markdown(html: str) -> str:
    """Convert SEC filing HTML to readable markdown.

    Handles tables, headers, lists, and strips scripts/styles.
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove non-content elements
    for tag in soup.find_all(["script", "style", "meta", "link", "noscript"]):
        tag.decompose()

    parts: list[str] = []

    for elem in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "table", "ul", "ol", "div"]):
        tag_name = elem.name

        if tag_name.startswith("h"):
            level = int(tag_name[1])
            text = elem.get_text(strip=True)
            if text:
                parts.append(f"\n{'#' * level} {text}\n")

        elif tag_name == "table":
            parts.append(_table_to_markdown(elem))

        elif tag_name in ("ul", "ol"):
            for li in elem.find_all("li", recursive=False):
                text = li.get_text(strip=True)
                if text:
                    prefix = "-" if tag_name == "ul" else "1."
                    parts.append(f"{prefix} {text}")
            parts.append("")

        elif tag_name == "p":
            text = elem.get_text(strip=True)
            if text:
                parts.append(f"\n{text}\n")

        elif tag_name == "div":
            # Only process divs that contain direct text (not nested block elements)
            if not elem.find(["h1", "h2", "h3", "h4", "h5", "h6", "p", "table", "ul", "ol"]):
                text = elem.get_text(strip=True)
                if text and len(text) > 10:
                    parts.append(f"\n{text}\n")

    result = "\n".join(parts)
    # Clean up excessive whitespace
    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")
    return result.strip()


def _table_to_markdown(table_elem) -> str:
    """Convert an HTML table element to markdown table."""
    rows = []
    for tr in table_elem.find_all("tr"):
        cells = []
        for td in tr.find_all(["td", "th"]):
            text = td.get_text(strip=True).replace("|", "\\|")
            cells.append(text)
        if cells:
            rows.append(cells)

    if not rows:
        return ""

    # Normalize column count
    max_cols = max(len(r) for r in rows)
    for row in rows:
        while len(row) < max_cols:
            row.append("")

    lines = []
    # Header
    lines.append("| " + " | ".join(rows[0]) + " |")
    lines.append("| " + " | ".join("---" for _ in rows[0]) + " |")
    # Body
    for row in rows[1:]:
        lines.append("| " + " | ".join(row) + " |")

    return "\n" + "\n".join(lines) + "\n"
