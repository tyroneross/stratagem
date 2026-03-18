# Agent Memory System — Design Spec

**Date**: 2026-03-15
**Status**: Reviewed
**Scope**: Agent-owned memory, dynamic agent tiers, CLI/UI parity, file input/output, identity reframe

## Context

Stratagem is a strategic research system (reframed from market research) serving product strategists, corporate strategists, and technology leaders. It uses MECE decomposition and Pyramid Principle as structural foundations — no prescribed frameworks.

This spec adds an agent-owned memory system so agents learn from past runs, a tiered dynamic agent lifecycle, unified CLI/UI state, and file input/output controls.

## Design Principles

- **Agents own their memory** — each agent decides what's worth remembering via `record_observation`. Trusted with good judgment.
- **Trust but verify** — quality agents (source-verifier, plan-validator, report-critic) spot-check observations as part of their normal work.
- **Scaffold + pointer** — compact summary always injected, detail files retrieved on demand. Research-backed (see Evidence section).
- **CLI/UI parity** — both write the same `.stratagem/` state files. No separate paths.
- **Calm Precision** — all new UI surfaces follow Calm Precision design system: Gestalt grouping, Fitts' law sizing, progressive disclosure, content ≥ chrome, status via text color not badges.

## Design Rationale

This system intentionally separates **doing the work** from **learning from the work**.

### Why a separate meta-learning agent exists

The `after-action-analyst` is not a research worker or builder. It is a debrief and advisory agent. That separation is deliberate:

- **Execution agents optimize for task completion**. They are biased toward momentum and local success.
- **A debrief agent optimizes for reuse**. It can step back, compare outcome versus mission, and ask what should change next time.
- **An advisory agent diagnoses bottlenecks**. It can look for slow paths, redundant handoffs, or missing delegation patterns that made the run slower than necessary.
- **An advisory agent can draft guidance without owning implementation**. It can recommend specs, prompts, or operating notes for other agents to write or execute later.
- **This prevents memory pollution**. If every agent writes directly into long-term shared memory without review, the system accumulates noise, duplicates, and overfit tactics.

The model is closer to a project retrospective or after-action review than a normal subagent dispatch. Research, validation, and delivery happen in the main loop. Learning happens after the loop, once the evidence from the run is available.

### Why memory is split by scope

Memory is split into **thread**, **topic**, **common**, and emerging **agent-local** concerns because not all lessons generalize equally:

- **Thread memory** captures what happened in one run.
- **Topic memory** captures things that are likely to matter again for the same subject area.
- **Common memory** stores cross-topic process lessons.
- **Agent-local memory** is the right future home for capability-specific tactics ("how financial-analyst should work better"), distinct from subject-matter facts.

This prevents the common failure mode where project-specific facts leak into global policy and distort later runs.

### Why the after-action review runs post-task

The debrief runs after the main answer is produced because:

- mid-run retrospection competes with task execution for context and tokens
- the full mission record is only available at the end
- post-run review can inspect the entire run: prompt, tools, observations, dynamic agents, rationale, and output

This keeps the main research loop focused while still making learning first-class.

### Why the system uses artifact-based learning

Learning is persisted as files (`observations.jsonl`, `run_state.json`, `after_action.md`) rather than hidden prompt drift:

- artifacts are inspectable
- artifacts can be versioned, audited, and replayed
- artifacts allow future promotion, pruning, and decay policies
- artifacts make the system safer to evolve than implicit "the model just remembers"

This is the main reusable design pattern for future agent systems: make learning explicit, structured, and reviewable.

### Why promotion is governed instead of automatic everywhere

The system does not treat every useful local behavior as a global best practice. Promotion is gated because:

- repeated success is a better signal than a single good run
- topic-specific tactics often do not generalize
- quality signals should be available before memory is broadened

That is why the architecture uses:

- temporary runtime specialists
- topic-scoped persistence first
- broader promotion only after repeated use and quality evidence

### Reusable pattern for future agent designs

If this pattern is reused in other agent systems, keep the same core structure:

1. **Work agents** execute the mission.
2. **Quality agents** verify correctness and drift.
3. **A debrief agent** performs the retrospective after the mission.
4. **Memory scopes** prevent overgeneralization.
5. **Promotion rules** decide what becomes durable capability.

In other words: do not let "memory" mean "everything gets remembered." Make learning a governed pipeline.

### Why the after-action agent is advisory, not implementational

The `after-action-analyst` should primarily:

- diagnose what slowed the run down
- recommend faster execution patterns
- identify missing specialists or weak delegation boundaries
- suggest what specs, prompts, or guidance docs should be written

It should not automatically become the builder for those follow-on tasks. That would blur retrospection with execution again.

The cleaner pattern is:

- **after-action-analyst** identifies and frames the problem
- **another specialist** implements the fix, writes the spec, or updates the prompt if approved

This keeps the meta-learning layer focused on judgment, not task ownership.

## 1. Storage Architecture

Three-layer hybrid: thread state, topic memory, common memory.

```
.stratagem/
├── memory.json                   # Common: dynamic agent catalog, global process learnings
├── agent_config.json             # Model overrides, memory_budget, output_dir (existing, extended)
├── topics/
│   ├── index.json                # Registry: topic_id → title, thread_ids[], tags[]
│   └── {topic_id}/
│       ├── memory.json           # Aggregated: sources, findings, process learnings
│       └── agents.json           # Topic-scoped dynamic agents (tier 1)
├── agents/
│   └── {name}.json               # Persistent dynamic agents (tier 2)
└── threads/{id}/
    ├── messages.jsonl            # (existing)
    ├── context.md                # (existing)
    ├── run_state.json            # NEW: tool calls, timing, cost, input files, output dir
    └── observations.jsonl        # NEW: agent observations (append-only log)
```

### Layer Responsibilities

| Layer | Scope | Lifetime | Contents |
|-------|-------|----------|----------|
| Thread | Single run | Permanent (archivable) | Raw observations, run state, tool calls |
| Topic | Group of related threads | Grows with use | Aggregated sources, findings, process, topic agents |
| Common | Global | Persistent | Dynamic agent catalog (tier 2), cross-topic process learnings |

## 2. Observation Model

### MCP Tool: `record_observation`

Single tool, all agents can call it during their work.

```
record_observation(
    category: "source" | "finding" | "process" | "agent"
    content: str              # What was observed
    confidence: float         # 0.0-1.0, agent's self-assessment
    tags: list[str]           # Searchable labels
    scope: "thread" | "topic" | "common" = "thread"
    related_to: str | None    # Link to prior observation ID (for corrections/confirmations)
)
```

**Categories:**

| Category | Who writes | Example |
|----------|-----------|---------|
| `source` | data-extractor, source-verifier | "SEC EDGAR 10-K filings have 2-week lag for recent quarters" |
| `finding` | synthesizer, financial-analyst | "Apple R&D spend grew 12% YoY — verified against 10-K" |
| `process` | any agent | "scrape_url failed on reuters.com (paywall), WebSearch fallback worked" |
| `agent` | orchestrator | "patent-analyst (dynamic) produced high-quality IP landscape — recommend persistence" |

### Storage Format

Append-only JSONL per thread (`observations.jsonl`). Each entry:

```json
{
  "id": "OBS_20260315_103045_a1b2",
  "timestamp": "2026-03-15T10:30:45Z",
  "agent": "data-extractor",
  "category": "source",
  "content": "reuters.com requires subscription for full articles",
  "confidence": 0.8,
  "tags": ["reuters", "paywall", "source-reliability"],
  "scope": "thread",
  "related_to": null
}
```

### Quality Agent Spot-Checks

Quality agents (source-verifier, plan-validator, report-critic) can call `record_observation` with `related_to` pointing at an existing observation to confirm, correct, or flag it:

```
OBS_..._001  [source] conf:0.8  "reuters.com requires subscription for full articles"
OBS_..._047  [source] conf:0.9  "Confirmed: reuters.com 403s on automated requests"  related_to:OBS_..._001
```

No special mechanism — trust-but-verify is natural agent behavior using the same tool.

### Error Handling

| Scenario | Behavior |
|----------|----------|
| No active thread | Write to a temp buffer; flush to thread file when thread is created or discard at run end |
| Duplicate content (exact category + content match) | Skip append, return existing observation ID |
| `related_to` references nonexistent ID | Accept the observation, store the `related_to` value as-is. Orphan links are harmless — the observation stands on its own |
| Invalid confidence (outside 0.0-1.0) | Clamp to range (negative → 0.0, >1.0 → 1.0) |
| Empty content | Reject with error message |
| I/O failure (disk full, permissions) | Log warning, continue run. Observations are valuable but not critical path — a failed write should never halt research |

## 3. Memory Injection & Recall

### Scaffold + Pointer Pattern

**At run start** (`run_research`):
1. Identify topic — match thread to topic via `topics/index.json`
2. Load topic memory (`topics/{id}/memory.json`)
3. Load common memory (`memory.json`)
4. Build scaffold (compact summary with explicit file pointers)
5. Inject into `SYSTEM_PROMPT` as `## Research Memory` section, at context start

**Scaffold format** (~500-800 tokens, always injected):

```markdown
## Research Memory

### Topic: AI chip competitive landscape
Runs: 3 | Last: 2026-03-14 | Confidence: high
Sources: 4 tracked (2 reliable, 1 paywalled, 1 stale)
Findings: 7 verified, 2 uncertain
Process: 3 learnings
Details: .stratagem/topics/ai-chips/memory.json

### Available Specialists
- patent-analyst (sonnet) — IP landscape [topic-scoped, 2 runs, quality: 0.82]
- regulatory-analyst (sonnet) — compliance [persistent, 5 runs]
Catalog: .stratagem/agents/

### Common Memory
Process learnings: 2 entries
Details: .stratagem/memory.json
```

**Detail retrieval**: Agents use `Read` tool to load pointer files when they need depth. No special retrieval mechanism — agents already know how to read files.

### Token Budget

- **Scaffold**: 500-800 tokens (stable regardless of memory size)
- **Total memory budget**: Configurable, default **8000 tokens**
- **Configuration**: `agent_config.json` field `memory_budget`
- **CLI override**: `--memory-budget N`
- **Scaling**: Bump default as models improve; scaffold stays stable

### Topic Matching

Start simple:
- CLI: `--topic TOPIC_ID` flag
- UI: Topic selector dropdown
- If no `--topic` flag and no UI topic selection: planner includes a `suggested_topic` field in its plan output (a short kebab-case slug like `ai-chip-landscape`). Orchestrator uses this to create or match a topic entry in the index. If user specified `--topic`, that takes precedence — planner suggestion is ignored.
- Automatic similarity matching: future enhancement, not in scope

### Post-Run Aggregation

After `run_research` completes:
1. Read thread's `observations.jsonl`
2. Merge new observations into `topics/{id}/memory.json` with dedup:
   - **Dedup rule**: exact match on `(category, content)` tuple. If a match exists, keep the entry with higher confidence. Update `related_to` links if the newer observation adds a quality verification.
   - No semantic/fuzzy matching — exact string match only. Keeps it deterministic and fast.
3. Update common memory if any `scope: "common"` observations exist
4. Update topic index with thread linkage and timestamp
5. Check dynamic agent promotion criteria (see Section 4)

### Observation Count Tracking

`run_state.json` field `agents_dispatched[].observation_count` is computed during post-run aggregation by filtering `observations.jsonl` entries by the `agent` field. Not tracked in real-time.

## 4. Dynamic Agent Tiers

### Three Tiers

| Tier | Storage | Lifetime | Loaded when |
|------|---------|----------|-------------|
| 1: Topic-scoped | `topics/{id}/agents.json` | Available when topic resumes | Run matches topic |
| 2: Persistent | `.stratagem/agents/{name}.json` | Available across all runs, updatable | Every run |
| 3: Permanent | `subagents/definitions.py` + prompt file | First-class codebase agent | Always (static import) |

### Agent Definition Schema (Tier 1 & 2)

```json
{
  "name": "patent-analyst",
  "description": "Analyze patent filings and IP landscapes",
  "prompt": "You are a patent analysis specialist...",
  "model": "sonnet",
  "tools": ["Read", "Write", "WebSearch", "Bash"],
  "tier": 2,
  "created": "2026-03-15T10:30:00Z",
  "origin_topic": "ai-chips",
  "usage": {
    "total_runs": 5,
    "topics": ["ai-chips", "gpu-market"]
  },
  "quality": {
    "avg_confidence": 0.82,
    "spot_checks": 2,
    "last_checked": "2026-03-14"
  },
  "_quality_notes": "spot_checks increments when a quality agent writes an observation with related_to pointing at any observation from this agent's runs. avg_confidence averages the confidence scores of those spot-check observations. last_checked is the timestamp of the most recent spot-check."
}
```

### Promotion Criteria

**Tier 1 → Tier 2 (topic → persistent):**
- Used 3+ times across different threads within a topic
- Quality gate: if spot-checks exist, average confidence ≥ 0.7. If no spot-checks, use the agent's own `category:agent` observation confidence as proxy (agents self-assess). If neither exists, promotion is blocked until at least one quality signal is recorded.
- Orchestrator records `agent` category observation recommending persistence
- Automatic — system checks criteria after each run

**Tier 2 → Tier 3 (persistent → permanent):**
- Used across 3+ different topics
- Manual trigger only — orchestrator recommends, user confirms
- Generates prompt file in `subagents/prompts/`, adds entry to `definitions.py`
- This is a codebase change requiring a git commit, not just a runtime operation

### Runtime → Persistence Handoff

When `create_specialist` creates an agent during a run:
1. Agent is added to `_active_run_agents` dict (in-memory only, immediately dispatchable)
2. Agent name is recorded in `run_state.json` under `dynamic_agents_created`
3. **Post-run**: if a topic is assigned, the agent definition is persisted to `topics/{id}/agents.json` as tier 1. The full definition (name, description, prompt, model, tools) is saved — not just a reference.
4. If no topic is assigned, the agent definition is still saved to `run_state.json` under a `dynamic_agent_definitions` field so it can be recovered if the thread is later assigned to a topic.

This means `create_specialist` remains a pure in-memory operation during the run (no file I/O mid-research). Persistence happens in the post-run aggregation step.

### Loading at Run Start

`run_research` loads agents in order:
1. Permanent agents from `SUBAGENTS` dict (tier 3) — already loaded
2. Persistent agents from `.stratagem/agents/*.json` (tier 2)
3. Topic-scoped agents from `topics/{id}/agents.json` (tier 1) — if topic identified

All merge into `_active_run_agents` dict. Name collisions: **most specific scope wins** — tier 1 (topic-scoped) overrides tier 2 (persistent), which overrides tier 3 (permanent). This allows topic-specific variations of an agent (e.g., a topic-scoped `patent-analyst` with a specialized prompt for semiconductor IP overriding the generic persistent version).

## 5. CLI/UI Parity

Both CLI and UI write the same state files. The UI reads what's there.

### Shared State

| Capability | CLI Flag | UI Control | State File |
|------------|----------|------------|------------|
| Run state | `--thread` | Auto thread_id | `threads/{id}/run_state.json` |
| Observations | Agents call tool | Same | `threads/{id}/observations.jsonl` |
| Topic | `--topic TOPIC_ID` | Topic selector | `topics/index.json` |
| Model overrides | `--model-override NAME:MODEL` | Detail panel | `agent_config.json` |
| Memory budget | `--memory-budget N` | Config section | `agent_config.json` |
| Input files | `--input FILE [FILE...]` | File list | `run_state.json` |
| Output dir | `--output-dir PATH` | Output selector | `agent_config.json` |

### New CLI Flags

Added to `__main__.py`:
- `--topic TOPIC_ID` — assign run to a topic
- `--input FILE [FILE...]` — attach files for agents to use
- `--memory-budget N` — override default token budget for this run
- `--model-override NAME:MODEL` — per-agent model override (repeatable)

### Principle

A CLI run's observations show up in the UI's thread history. A UI model override applies to CLI runs. One source of truth.

## 6. File Input & Output

### Input Files

User points agents at specific files:
- **CLI**: `--input report.pdf financials.xlsx`
- **UI**: Compact file list below textarea, `+ Add files` button

Input files are:
1. Resolved to absolute paths at run start. If a path doesn't exist, warn in the prompt ("File not found: ...") but don't fail — the agent may still have useful context from the filename.
2. Recorded in `run_state.json` as `input_files: [{path, size_bytes, type, exists}]`
3. Injected into orchestrator prompt with basic metadata:
   ```
   ## Input Files
   - /path/to/report.pdf (PDF, 2.4MB)
   - /path/to/financials.xlsx (Excel, 340KB)
   ```
4. Planner sees them and assigns extraction tasks accordingly

### Output Location

- **CLI**: `--output-dir PATH` (already exists)
- **UI**: Output directory text field in config section
- **Config**: Stored in `agent_config.json` as `output_dir`
- **Default**: `.stratagem/reports/`

Both pass through to `run_research()` `output_dir` parameter.

## 7. UI Surfaces (Calm Precision)

All new UI follows Calm Precision design system.

### Memory Scaffold Display

When viewing a thread's context:
- Progressive disclosure — collapsed summary by default, expand for detail
- Hierarchy: Topic name (14-16px bold) → Run count + last active (12-14px) → Source/finding counts (11-12px muted)
- Status via text color only — no background badges
- Confidence: green text for high, muted for uncertain
- Content ≥ chrome: memory content is the interface, not decorative UI

### Config Section

Memory budget, output dir, agent model overrides. **Placement**: Collapsible section below the controls bar and above the phase diagram — same level as the input area. Collapsed by default (Hick's law: reduce visible options until needed).

- Grouped under single expandable section (Gestalt: single border around related controls)
- Dividers between controls, never individual borders on each
- Action button (Save): muted/inactive until a value changes, then visually prominent
- No modal — inline editing, same pattern as detail panel
- 8pt grid spacing, 4.5:1 contrast

### Topic Selector

- Dropdown near the prompt area
- Shows existing topics + "New topic" option
- 44px touch targets on mobile, 24px desktop
- Selected state: text-gray-900 font-medium + 2px bottom border (not background pills)

### File Input

- Compact list below textarea
- `+ Add files` button: muted until clicked, compact (not full-width — it's a quick action)
- File chips: filename + remove button, monospace, 12px
- No drag-and-drop (over-engineering for v1)

## 8. run_state.json Schema

Captured automatically per thread, no agent action needed:

```json
{
  "thread_id": "web_1710500000",
  "topic_id": "ai-chips",
  "started": "2026-03-15T10:30:00Z",
  "completed": "2026-03-15T10:35:42Z",
  "model": "opus",
  "model_overrides": {"data-extractor": "haiku"},
  "input_files": ["/path/to/report.pdf"],
  "output_dir": "/path/to/reports",
  "memory_budget": 8000,
  "agents_dispatched": [
    {
      "name": "research-planner",
      "model": "sonnet",
      "started": "2026-03-15T10:30:05Z",
      "completed": "2026-03-15T10:30:28Z",
      "tools_used": ["Read", "WebSearch"],
      "observation_count": 2
    }
  ],
  "tools_used": {"mcp__stratagem__scrape_url": 4, "WebSearch": 7, "Read": 12},
  "total_turns": 23,
  "duration_ms": 342000,
  "cost_usd": 0.4521,
  "dynamic_agents_created": ["patent-analyst"],
  "dynamic_agent_definitions": {
    "patent-analyst": {
      "description": "Analyze patent filings and IP landscapes",
      "prompt": "You are a patent analysis specialist...",
      "model": "sonnet",
      "tools": ["Read", "Write", "WebSearch", "Bash"]
    }
  },
  "observations_count": 14
}
```

## 9. Orchestrator Prompt Additions

Added to `SYSTEM_PROMPT` in `agent.py`:

```markdown
## Memory

You have access to research memory from prior runs on this topic. The scaffold summary is injected above. For full details, use Read to load the pointer files listed in the scaffold.

When you or your agents discover something worth remembering:
- Source reliability (paywalls, stale data, good sources) → record_observation category:source
- Key verified findings → record_observation category:finding
- Process learnings (what worked/failed) → record_observation category:process
- Agent quality assessments → record_observation category:agent

Quality agents (source-verifier, plan-validator, report-critic) may spot-check observations using related_to links. This is routine — not an override.

## Dynamic Specialists

If research-planner identifies a capability gap, create a temporary specialist using create_specialist.
Created specialists are in-memory only during the run. After the run:
- If a topic is assigned, the specialist is persisted as tier 1 (topic-scoped)
- After 3+ uses with quality signals, it auto-promotes to tier 2 (persistent across topics)
- Tier 3 (permanent codebase agent) requires your recommendation + user confirmation
```

## 10. Evidence: Scaffold + Pointer

Research supporting this architecture:

| Source | Finding | Tier |
|--------|---------|------|
| Lost in the Middle (Liu et al., TACL 2024) | >30% accuracy drop mid-context. Start/end = high performance zone | T1 |
| MemGPT (Packer et al., 2023) | Two-tier memory (main + external) outperforms single-tier | T1 |
| Generative Agents (Park et al., UIST 2023) | Without reflection summaries, agents degenerate in 48h | T1 |
| Hierarchical Process Memory (Trends Cog Sci, 2015) | Human cognition: compressed working memory + drill-down to details | T1 |
| RAG vs Long-Context (EMNLP 2024) | Hybrid (summary + retrieval) matches full-context at lower cost | T1 |
| ACON (2025, under review ICLR 2026) | 26-54% savings, but naive summarization loses rare critical details — use explicit pointers | T2 (TAG:INFERRED pending publication) |

**Design implication**: Scaffold at context start (high-accuracy zone), explicit file pointers (prevent detail loss), configurable budget (scales with model capability).

## 11. Scope Boundaries

### In Scope
- `record_observation` MCP tool
- Memory storage (thread, topic, common layers)
- Scaffold + pointer injection in `run_research`
- Post-run aggregation (thread → topic → common)
- Dynamic agent tier 1 & 2 persistence + loading
- Tier promotion logic (1→2 automatic, 2→3 manual)
- CLI flags: `--topic`, `--input`, `--memory-budget`, `--model-override`
- UI: topic selector, file input, config section, memory display
- `run_state.json` capture
- Orchestrator + planner prompt updates
- All UI follows Calm Precision

### Out of Scope
- Automatic topic matching via embedding similarity
- Tier 3 promotion automation (always manual)
- Vector search / semantic retrieval over observations
- Memory editing UI (read-only display for v1)
- Observation deletion or expiry
- Cross-project memory sharing
- Agent prompt editing from UI
- Multi-topic threads (a thread belongs to exactly one topic or none; cross-topic queries should be decomposed by the planner into separate tasks)

## 12. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| SDK copies agents dict | Dynamic agents not dispatchable mid-run | Fallback: orchestrator handles task directly (already noted in Phase 3) |
| Agents don't call record_observation reliably | Sparse memory | Strong prompt guidance + quality agents note their own observations |
| Topic memory grows unbounded | Slow scaffold generation | Cap aggregated observations per topic (configurable, default 200) |
| Observation quality varies | Noisy memory | Quality agent spot-checks + confidence scoring + aggregation dedup |
| Scaffold pointer files missing/moved | Agent Read fails | Graceful degradation — scaffold notes availability, agents handle missing files |

## 13. Files to Create/Modify

### New Files
| File | Purpose |
|------|---------|
| `tools/memory.py` | `record_observation` MCP tool |
| `memory.py` | Memory loading, scaffold generation, post-run aggregation |
| `topics.py` | Topic registry CRUD, topic-thread linkage |

### Modified Files
| File | Changes |
|------|---------|
| `agent.py` | Memory injection in `run_research`, `_active_run_agents` loads tier 1+2, prompt additions, input files injection, topic param |
| `server.py` | Register `record_observation` in ALL_TOOLS |
| `ui.py` | Topic selector, file input, config section, memory display, new API endpoints |
| `__main__.py` | New CLI flags: `--topic`, `--input`, `--memory-budget`, `--model-override` |
| `subagents/prompts/research_planner.md` | Memory-aware planning guidance |
| `tests/test_integration.py` | Tool count 11→12 (`record_observation`), component count 23→24, new memory/topic/aggregation tests |
