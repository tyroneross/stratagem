# PDF Processing Reference

## Reading PDFs

Use the `parse_pdf` tool with these options:
- `extract_tables: true` — uses pdfplumber for structured table extraction
- `extract_images: true` — extracts embedded images as base64
- `pages: "1-5"` — limit to specific pages for large documents

### Table Extraction Best Practices
- Always extract tables when the PDF contains financial data, specifications, or comparisons
- Tables come back as markdown — verify row/column alignment before using values
- For complex multi-page tables, extract page-by-page and merge manually

### Handling Large PDFs
- For 10-K/10-Q filings (100+ pages): extract by section, not all at once
- Use page ranges to target specific sections:
  - Cover + TOC: pages 1-5
  - Financial statements: find via TOC, typically pages 40-80
  - Risk factors: typically pages 10-30
  - MD&A: typically pages 20-50

### Scanned PDFs
If `parse_pdf` returns empty/garbled text, the PDF may be scanned images. Workarounds:
1. Try `extract_images: true` to get the page images
2. Note in output: "[Source appears to be scanned — text extraction may be incomplete]"

## Creating PDFs

### From Markdown
Use the `create_report` tool with `format: "markdown"` — readers can convert to PDF externally.

### From Structured Data
Use `create_report` with `format: "html"` for printable output, or `format: "docx"` which converts cleanly to PDF.

## Quality Checks After Extraction
- Do extracted numbers match what's visible in the source?
- Are table headers aligned with the correct columns?
- Are footnotes captured (they often appear as separate text blocks)?
- Are currency/unit symbols preserved?
