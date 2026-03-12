# Pyramid Principle — Output Structure Framework

All Stratagem reports follow Barbara Minto's Pyramid Principle. This is not optional formatting — it is the logical backbone of every output.

## Core Rule

**Start with the answer.** The reader should know your conclusion before they see the evidence. Everything below the answer exists only to support it.

## SCQA Framework (Introduction Structure)

Every report opens with SCQA — this frames the entire narrative:

- **Situation**: A non-controversial statement about the current state the reader will agree with
- **Complication**: The event, shift, or tension that creates a problem or opportunity
- **Question**: The implicit or explicit question that arises from the complication
- **Answer**: The governing thought — your core conclusion. This IS the report's thesis

Example:
- S: "Enterprise AI adoption has accelerated, with 57% of organizations running agents in production."
- C: "However, single-agent systems hit fundamental limits — context saturation, serial execution bottlenecks, and cognitive overload — that degrade output quality on complex research tasks."
- Q: "How should organizations architect multi-agent systems that produce high-quality research?"
- A: "Three interlocking capabilities determine quality: orchestration pattern selection, embedded quality gates, and token-efficient operational design."

## Pyramid Structure

```
            ┌─────────────────┐
            │  Governing       │   ← Answer first (1 sentence)
            │  Thought         │
            └────────┬────────┘
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
  ┌─────────┐  ┌─────────┐  ┌─────────┐
  │ Key      │  │ Key      │  │ Key      │  ← 3-5 supporting arguments (MECE)
  │ Argument │  │ Argument │  │ Argument │
  │ 1        │  │ 2        │  │ 3        │
  └────┬─────┘  └────┬─────┘  └────┬─────┘
       │              │              │
  ┌────┴────┐    ┌────┴────┐   ┌────┴────┐
  │Evidence │    │Evidence │   │Evidence │   ← Data, sources, analysis
  │& Data   │    │& Data   │   │& Data   │
  └─────────┘    └─────────┘   └─────────┘
```

### Rules

1. **Governing Thought**: One sentence. The reader's single takeaway if they read nothing else
2. **Key Arguments**: 3-5 arguments that are MECE (Mutually Exclusive, Collectively Exhaustive). Each must directly support the governing thought
3. **Evidence**: Every argument is backed by specific data — numbers, sources, examples. No unsupported assertions
4. **Logical Ordering**: Arguments follow one of three orders:
   - **Chronological**: first → second → third (process, timeline)
   - **Structural**: component A → component B → component C (architecture, system)
   - **Importance**: most critical → second → third (recommendations)

## Report Template

```markdown
# [Title]: [Governing Thought as Subtitle]

## Executive Summary
[SCQA — Situation, Complication, Question, then the Answer]
[3-5 numbered key arguments with one sentence each]
[Overall recommendation / call to action]

## [Key Argument 1 — as a declarative headline]
[Opening: state the argument's conclusion first]
[Evidence 1 with source citation]
[Evidence 2 with source citation]
[Synthesis: what this means for the reader]

## [Key Argument 2 — as a declarative headline]
[Same structure]

## [Key Argument 3 — as a declarative headline]
[Same structure]

## Implications and Recommendations
[What the reader should DO based on these findings]
[Specific, actionable, tied back to evidence]
[Priority ordering: what to do first]

## Methodology & Limitations
[How the research was conducted]
[Data gaps, caveats, confidence levels]

## Sources
[Tiered: T1-T4 with full citations]
```

## Headline Rules

Every section heading should be a **declarative statement** — a mini-conclusion, not a topic label.

| Bad (topic label) | Good (declarative) |
|---|---|
| "Market Overview" | "Enterprise AI market will reach $52B by 2030" |
| "Challenges" | "Single agents fail at context, speed, and complexity" |
| "Recommendations" | "Start simple, invest in evaluation, manage context" |

## Adaptive Structure

The template adapts to content. Do NOT force-fit:
- **If market data dominates** → Lead with positioning and competitive insights
- **If financial data dominates** → Lead with ROI, benchmarking, valuations
- **If operational data dominates** → Lead with efficiency gains and process improvements
- **If the answer is uncertain** → Lead with the strongest hypothesis and flag competing interpretations

The pyramid structure is the skeleton. The content determines which bones are largest.

## Source Attribution

Use numbered footnote-style citations: [1], [2], [3]. Sources section lists full details with tier classification (T1-T4).

Every factual claim — every number, date, percentage, comparison — must have a citation. Uncited claims are flagged as [UNSOURCED] by the source-verifier.

## Anti-Patterns

- **Burying the lead**: Putting the conclusion at the end (reverse the order)
- **Topic labels as headings**: "Market Overview" tells the reader nothing (use declarative statements)
- **Evidence without synthesis**: Listing facts without connecting them to the argument
- **Executive summary with new information**: The exec summary summarizes — it introduces nothing new
- **More than 5 key arguments**: If you have 7 points, group them into 3-4 higher-level themes
- **MECE violation**: Two arguments that overlap, or an obvious gap in coverage
