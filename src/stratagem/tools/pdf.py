"""PDF parsing tool — text, tables, and image extraction."""

from typing import Any
import base64
import io

from claude_agent_sdk import tool


@tool(
    "parse_pdf",
    "Extract text, tables, and images from a PDF file. Returns markdown-formatted content.",
    {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Absolute path to the PDF file"},
            "extract_tables": {"type": "boolean", "description": "Extract tables as markdown", "default": False},
            "extract_images": {"type": "boolean", "description": "Extract embedded images as base64", "default": False},
            "pages": {"type": "string", "description": "Page range: 'all', '1-5', '3', '10-20'", "default": "all"},
        },
        "required": ["file_path"],
    },
)
async def parse_pdf(args: dict[str, Any]) -> dict[str, Any]:
    file_path = args["file_path"]
    extract_tables = args.get("extract_tables", False)
    extract_images = args.get("extract_images", False)
    pages_spec = args.get("pages", "all")

    try:
        from pypdf import PdfReader
    except ImportError:
        return _error("pypdf not installed. Run: pip install pypdf")

    try:
        reader = PdfReader(file_path)
    except FileNotFoundError:
        return _error(f"File not found: {file_path}")
    except Exception as e:
        return _error(f"Failed to open PDF: {e}")

    total_pages = len(reader.pages)
    page_indices = _parse_page_range(pages_spec, total_pages)

    sections: list[str] = []
    sections.append(f"# PDF: {file_path}")
    sections.append(f"**Pages**: {total_pages} total, extracting {len(page_indices)}")
    sections.append("")

    # Text extraction via pypdf
    for i in page_indices:
        page = reader.pages[i]
        text = page.extract_text() or ""
        if text.strip():
            sections.append(f"## Page {i + 1}")
            sections.append(text.strip())
            sections.append("")

    # Table extraction via pdfplumber
    if extract_tables:
        try:
            import pdfplumber

            with pdfplumber.open(file_path) as pdf:
                for i in page_indices:
                    if i < len(pdf.pages):
                        tables = pdf.pages[i].extract_tables()
                        for t_idx, table in enumerate(tables):
                            if table:
                                sections.append(f"### Table (Page {i + 1}, #{t_idx + 1})")
                                sections.append(_table_to_markdown(table))
                                sections.append("")
        except ImportError:
            sections.append("\n> pdfplumber not installed — table extraction skipped.")
        except Exception as e:
            sections.append(f"\n> Table extraction error: {e}")

    # Image extraction via pypdf
    images_data: list[dict] = []
    if extract_images:
        for i in page_indices:
            page = reader.pages[i]
            if hasattr(page, "images"):
                for img_idx, image in enumerate(page.images):
                    try:
                        b64 = base64.b64encode(image.data).decode("ascii")
                        images_data.append({
                            "page": i + 1,
                            "index": img_idx,
                            "name": getattr(image, "name", f"image_{img_idx}"),
                            "size": len(image.data),
                            "base64": b64[:200] + "..." if len(b64) > 200 else b64,
                        })
                    except Exception:
                        continue

        if images_data:
            sections.append(f"### Images Extracted: {len(images_data)}")
            for img in images_data:
                sections.append(f"- Page {img['page']}: {img['name']} ({img['size']} bytes)")

    content = "\n".join(sections)
    return {"content": [{"type": "text", "text": content}]}


def _parse_page_range(spec: str, total: int) -> list[int]:
    if spec == "all":
        return list(range(total))

    indices = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            s = max(0, int(start) - 1)
            e = min(total, int(end))
            indices.extend(range(s, e))
        else:
            idx = int(part) - 1
            if 0 <= idx < total:
                indices.append(idx)
    return sorted(set(indices))


def _table_to_markdown(table: list[list]) -> str:
    if not table:
        return ""

    # Clean cells
    rows = []
    for row in table:
        rows.append([str(cell or "").strip().replace("\n", " ") for cell in row])

    if not rows:
        return ""

    # Build markdown table
    header = rows[0]
    col_count = len(header)
    lines = ["| " + " | ".join(header) + " |"]
    lines.append("| " + " | ".join(["---"] * col_count) + " |")

    for row in rows[1:]:
        # Pad row to match header
        padded = row + [""] * (col_count - len(row))
        lines.append("| " + " | ".join(padded[:col_count]) + " |")

    return "\n".join(lines)


def _error(msg: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": f"Error: {msg}"}], "isError": True}
