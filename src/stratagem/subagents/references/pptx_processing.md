# PowerPoint Processing Reference

## Reading Presentations

Use the `read_pptx` tool:
- `include_notes: true` — speaker notes often contain the real analysis
- `extract_images: true` — for charts/diagrams embedded as images

### What to Extract
- Slide titles → outline the presentation structure
- Body text → key claims and data points
- Tables → structured data, comparison matrices
- Speaker notes → detailed analysis, talking points, source citations
- Charts → described by alt-text or surrounding labels

## Creating Presentations

Use `create_pptx` with these layout types:
- `"title"` — title slide (title + subtitle)
- `"bullets"` — title + bullet points (default)
- `"table"` — title + data table (pipe-delimited content)
- `"blank"` — empty slide for custom content

### Slide Design Rules

1. **One message per slide** — the title IS the conclusion, not a topic label
   - Bad: "Revenue Analysis"
   - Good: "Revenue grew 23% driven by enterprise segment"

2. **Content limits per slide**:
   - Max 6 bullet points
   - Max 8 words per bullet
   - Max 1 chart + 1 supporting table

3. **Slide structure for research decks**:
   - Slide 1: Title + key finding + date
   - Slide 2: Executive summary (3-5 bullets)
   - Slides 3-N: One finding per slide with evidence
   - Final slide: Recommendations + next steps

4. **Table slides**: Use pipe-delimited format in content:
   ```
   Metric | Q1 | Q2 | Q3
   Revenue | $1.2B | $1.4B | $1.5B
   Margin | 42% | 44% | 45%
   ```

### Color Palette Guidance

Pick colors that match the topic. Don't default to generic blue.

| Theme | Primary | Secondary | Accent |
|-------|---------|-----------|--------|
| Finance/Corporate | `1E2761` (navy) | `CADCFC` (ice blue) | `FFFFFF` |
| Growth/Positive | `2C5F2D` (forest) | `97BC62` (moss) | `F5F5F5` |
| Risk/Alert | `B85042` (terracotta) | `E7E8D1` (sand) | `A7BEAE` |
| Technology | `065A82` (deep blue) | `1C7293` (teal) | `21295C` |
| Healthcare | `028090` (teal) | `00A896` (seafoam) | `02C39A` |

### Speaker Notes
Always add speaker notes with:
- Source citations for every data point
- Context the presenter needs
- Backup data not shown on slide
