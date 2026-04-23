# Output Formats — Routing

Stratagem produces research outputs in four formats. Route each format to the right guidance source — some stays internal to this repo, some delegates to external plugins that own the full formatting spec.

## Format routing

| Format | Guidance | Tool path |
|---|---|---|
| Markdown | `content_design.md` (internal) + `pyramid_principle.md` (internal) | `mcp__stratagem__create_report` with `format: "markdown"` |
| HTML | `content_design.md` (internal) + `pyramid_principle.md` (internal) | `mcp__stratagem__create_report` with `format: "html"` |
| **Word (.docx)** | **`docx-builder` plugin** — typography, margins, tables, callouts, TOC, python-docx mechanics | Preferred: invoke `docx-builder` skill (external plugin) for polished output. Fallback: `mcp__stratagem__create_report` with `format: "docx"` for fast research artifacts. |
| **PowerPoint (.pptx)** | **`pptx-builder` plugin** — PptxGenJS, palette, theme-portable post-processing | Preferred: invoke `pptx-builder` skill (external plugin) for polished output. Fallback: `mcp__stratagem__create_pptx` or `mcp__stratagem__create_report` with `format: "pptx"` for fast fallback. |

## When to use the plugin vs the internal tool

**Use the plugin (docx-builder / pptx-builder) when:**
- The output is the final deliverable for a human reader
- Typography, spacing, hierarchy, or theme-portability matters
- The document is > 3 sections (needs TOC) or the deck is > 5 slides
- The user mentioned "polished," "presentation-ready," "final," or specified fonts/brand

**Use the internal tool when:**
- The output is an intermediate artifact for another subagent to read
- Fast fallback is preferred over typography-correct output
- Running in an environment without the plugins installed

## Structure planning before rendering

Neither the internal tool nor the plugin rendering should begin until structure is locked. For Word docs use the `doc-structure` skill (in `tyrone-writing-system` plugin) or `pyramid-long-form` (in `pyramid-principle` plugin). For decks use `deck-structure` (in `tyrone-writing-system`) or `pyramid-presentation` (in `pyramid-principle`).

## Plugins referenced

- `docx-builder` — `github.com/tyroneross/docx-builder`
- `pptx-builder` — `github.com/tyroneross/pptx-builder`
- `tyrone-writing-system` — `github.com/tyroneross/tyrone-writing-system` (voice + structure skills)
- `pyramid-principle` — deeper Pyramid logic
