# Word Document Processing Reference

## Creating Reports as DOCX

Use the `create_report` tool with `format: "docx"`.

### Section Structure
Each section needs:
- `heading`: Declarative, not topical ("Revenue grew 15% YoY" not "Revenue")
- `content`: Markdown-formatted text (bullets with `- `, numbered with `1. `)
- `level`: Heading level 1-3 (2 is default for main sections)

### Content Formatting in Sections
The tool auto-detects formatting from the content string:
- Lines starting with `- ` or `* ` → bullet lists
- Lines starting with `1.` or `2.` → numbered lists
- Other lines → body paragraphs

### Report Template for Research

```
Title: "[Company/Topic] — [Analysis Type]"
Metadata: author, date, subtitle

Sections:
1. Executive Summary (level 2)
   - 3-5 bullet key findings
   - Final bullet: recommendation or next step

2. Background (level 2)
   - Context the reader needs
   - Why this analysis matters now

3-N. Analysis Sections (level 2)
   - One topic per section
   - Data tables as markdown
   - Source citations inline: [Source: 10-K, FY2024, p.45]

Final. Methodology & Sources (level 2)
   - How data was gathered
   - Source list with dates accessed
```

### Best Practices
- Professional font is applied automatically (system default)
- Date is auto-filled if not provided
- Tables in content should use markdown format — they render as text in DOCX
- For tables that must be proper Word tables, use separate PPTX or Excel output
- Footer with generation timestamp is added automatically

### When to Use DOCX vs Other Formats
| Need | Format |
|------|--------|
| Formal report for stakeholders | DOCX |
| Quick internal share | Markdown |
| Board presentation | PPTX |
| Data appendix with formulas | XLSX |
| Web-viewable report | HTML |
