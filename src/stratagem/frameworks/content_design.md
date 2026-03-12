# Content Design — Calm Precision for Research Reports

Reports must be easy to read, scan, and act on. These rules apply to all Stratagem output — markdown, docx, html, and presentation formats.

## Hierarchy (Three-Line Pattern)

Every section follows a visual hierarchy:
- **Title** (largest, bold): The declarative headline — a mini-conclusion
- **Body** (standard size): The analysis and evidence
- **Metadata** (smallest, muted): Sources, dates, confidence markers

## Signal Over Noise

### Content ≥ Chrome (70% Rule)
At least 70% of the report should be substantive content. Minimize:
- Decorative dividers and formatting
- Redundant headers and sub-headers
- Boilerplate language ("In this section, we will discuss...")
- Repetition of the question being answered

### Status = Inline Text, Not Decoration
Express confidence and verification status with text markers:
- ✅ Verified against source
- ⚠️ Supported but not directly verified
- ❓ Uncertain / needs verification
- [UNSOURCED] No citation available

### Numbers Need Context
Never present a number without:
- **Comparison**: relative to what? (YoY, vs peers, vs benchmark)
- **Direction**: up, down, flat, accelerating
- **Magnitude**: significant or marginal? ($1.2B vs $1.2M matters)

Format for scanning: `$1.2B` not `$1,234,567,890`. Use `+15% YoY` not `grew significantly`.

## Smart Brevity

### Headlines: WHO + WHAT + KEY DETAIL
- 20-85 characters optimal for scannability
- Action verbs: "surges", "declines", "outperforms", "emerges"
- Include the key number if one exists

| Before (vague) | After (smart brevity) |
|---|---|
| "Revenue Performance" | "Revenue surges 23% to $94.8B on AI demand" |
| "Competitive Analysis" | "Three competitors control 67% of market" |
| "Industry Trends" | "Enterprise AI adoption doubles YoY to 40%" |

### Paragraphs: One Idea Each
- Lead sentence = the point
- 2-4 supporting sentences = evidence
- No paragraph should make more than one claim

### Bullet Lists: For Parallel Items Only
Use bullets when items are:
- The same type (all recommendations, all findings, all risks)
- Scannable independently (each stands alone)
- 3-7 items (fewer → prose; more → group into categories)

## Progressive Disclosure

### Show Less, Reveal on Demand
Structure reports so readers can go as deep as they want:
1. **Executive Summary** → Full answer in 1 page (most readers stop here)
2. **Key Arguments** → Supporting logic with evidence (managers read this)
3. **Detailed Analysis** → Full evidence, methodology, caveats (analysts read this)
4. **Sources & Appendix** → Raw data, full citations (researchers reference this)

Each level should be self-contained — a reader at any level gets a complete picture at that depth.

## Tables Over Prose for Structured Data

When comparing 3+ items across 2+ dimensions, use a table. Never write:
> "Company A has revenue of $10B and 5% growth. Company B has revenue of $8B and 12% growth."

Instead:
| Company | Revenue | Growth |
|---|---|---|
| A | $10B | 5% |
| B | $8B | 12% |

## Visual Rhythm

### Consistent Spacing
- Sections separated by one blank line
- Subsections separated by paragraph spacing
- No double-blank-lines or excessive whitespace

### Scannable Structure
A reader skimming only headings and bold text should get:
- The governing thought
- All key arguments
- The main recommendation
- Key numbers

Bold sparingly: only conclusions, key numbers, and action items.

## Formatting by Output Type

### Markdown
- H1 for title, H2 for key arguments, H3 for subsections
- Inline bold for emphasis, not CAPS or italics
- Code blocks for data, formulas, or structured output
- Horizontal rules only between major sections

### Word Document (docx)
- Calibri 10.5pt body, proper heading styles (not manual bold)
- Tables with "Light Grid" style, not borders everywhere
- Page breaks between major sections only
- Headers and footers with document metadata

### HTML
- Semantic heading tags (h1-h3)
- CSS classes for hierarchy, not inline styles
- Responsive: readable at 320px to 1440px
- Print stylesheet: removes navigation, preserves content

## Anti-Patterns

- **Wall of text**: No paragraph longer than 5 sentences
- **Orphan bullets**: A single bullet point (use prose instead)
- **Nested bullets beyond 2 levels**: Flatten the hierarchy
- **Decorative formatting**: Bold/italic/underline for emphasis only, never decoration
- **Jargon without definition**: Define on first use
- **Passive voice for findings**: "Revenue grew" not "Revenue was observed to have grown"
- **Vague qualifiers**: "significant", "substantial", "notable" — replace with numbers
