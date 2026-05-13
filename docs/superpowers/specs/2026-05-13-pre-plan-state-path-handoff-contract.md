# Pre-Plan State, Path, and Handoff Contract

**Date**: 2026-05-13
**Status**: Proposed
**Scope**: Stratagem run harness, planning state, handoff contracts, path selection, pay-it-forward architecture rule

## Main Point

Stratagem should add a durable pre-plan contract before the `research-planner` runs. The contract should capture the run state, select the execution path, declare handoffs, name stop conditions, and define the validation surface. This turns the current prompt-guided delegation budget into an auditable harness.

The current system already has good pieces:

- `SYSTEM_PROMPT` gives the agent role structure and mission workflow.
- `_derive_delegation_budget` estimates complexity, likely specialists, and expected after-action value.
- Thread storage keeps `messages.jsonl`, `context.md`, `observations.jsonl`, and post-run `run_state.json`.
- The after-action review can identify missed specialists, weak handoffs, and durable learning opportunities.

The missing piece is before planning: a compact state object that says what kind of run this is, which path is allowed, who owns each boundary, and what must be true before the system proceeds.

## Why This Matters

Research on agent harnesses and the local build-loop architecture both point to the same conclusion: model quality matters, but reliability usually comes from the harness around the model. For Stratagem, that means the planner should not infer everything from prose every time. It should receive a small, typed run contract.

Three failure modes this addresses:

1. **State ambiguity before planning**: the system has thread context, memory, and budgets, but no single pre-plan object that says what state is authoritative for this run.
2. **Path ambiguity before execution**: a quick answer, full research run, financial analysis, artifact draft, continuation, repair, and eval run currently look too similar until the prompt has already started working.
3. **Handoff ambiguity between agents**: agents can write observations and final outputs, but handoffs are still mostly natural-language convention instead of structured inputs and outputs.

## Pay-It-Forward Architecture Rule

Default to the slightly harder architecture now when it unlocks a named future capability at tolerable cost.

Path A is minimum viable: prompt-only routing, inline prose handoffs, and post-run notes.

Path B is typed-contract extension: small schema, explicit state files, and validation hooks.

Stratagem should default to Path B when the change touches any of these surfaces:

- Agent handoffs or specialist boundaries.
- Schemas, tool outputs, or MCP contracts.
- Multi-surface behavior shared by CLI, UI, and background jobs.
- Durable state, memory, thread history, or after-action learning.
- Features that future agents will need to inspect, replay, validate, or extend.

Path A is acceptable only when at least one blocking condition is true:

- Path B would cost more than about 2x the effort for no near-term reliability gain.
- The needed dependency, storage primitive, or UI surface does not exist yet.
- The product decision is still unresolved.
- There is no named future capability that the contract unlocks.

For this spec, Path B is the right default because a typed run contract unlocks UI visibility, replay, evals, safer continuation, and better after-action learning.

## Proposed State Model

Add three durable artifacts under the active thread folder.

```text
.stratagem/
  threads/
    {thread_id}/
      messages.jsonl
      context.md
      observations.jsonl
      run_state.json
      run_contract.json
      working_state.json
      handoffs/
        plan.json
        extraction.json
        synthesis.json
        verification.json
        artifact.json
        after_action.json
```

`run_contract.json` is written once at run start and only amended through explicit revisions. `working_state.json` is updated as the run progresses. Files in `handoffs/` are append-or-replace by role, with the orchestrator as the default writer unless a specialist has an explicit write grant.

## State Layers

| Layer | File | Owner | Purpose |
|---|---|---|---|
| Session | `working_state.json` | Orchestrator | Current run phase, active path, active agent, pending questions, validation status |
| Thread | `run_contract.json`, `messages.jsonl`, `context.md` | Orchestrator | User goal, constraints, selected path, plan state, durable transcript |
| Topic | `.stratagem/topics/{topic_id}/memory.json` | Memory/after-action pipeline | Reusable findings and process lessons for the same subject area |
| Common | `.stratagem/memory.json` | Governed memory pipeline | Cross-topic process lessons and reusable agent patterns |

Single-writer discipline should be the default. Specialists can propose updates through handoff files or `record_observation`, but the orchestrator decides what becomes canonical thread state.

## Pre-Plan Path Matrix

The orchestrator should choose one primary path before the planner runs.

| Path | Use When | Planner Expectation | Required Handoffs |
|---|---|---|---|
| `answer_only` | The user asks a narrow question and no durable artifact is needed | Give a concise answer with minimal decomposition | None beyond final response |
| `research` | The user asks for strategy, market, technical, or competitive research | Decompose into source gathering, synthesis, and verification | `plan`, `extraction`, `synthesis`, `verification` |
| `artifact` | The user asks for a memo, doc, report, deck outline, or structured deliverable | Plan around output contract and audience | `plan`, `synthesis`, `artifact`, `verification` |
| `financial` | The user asks for company, market, valuation, KPI, or forecast analysis | Require numeric source discipline and assumptions | `plan`, `extraction`, `synthesis`, `verification` |
| `continuation` | The user resumes or asks to keep going from prior context | Rehydrate prior contract and state before planning | `plan`, prior relevant handoffs |
| `repair` | The user asks to fix a failed, weak, or disputed prior run | Start from failure criteria and evidence gap | `plan`, `verification`, `after_action` |
| `eval` | The user asks to test, compare, or optimize behavior | Define metric, baseline, variant, and pass criteria first | `plan`, `verification`, `after_action` |

If two paths fit, choose the path with the highest verification burden. For example, a financial memo is `financial` first and `artifact` second.

## Run Contract Schema

The first implementation can use plain dataclasses or typed dictionaries. It does not need a new dependency.

```json
{
  "schema_version": "2026-05-13",
  "run_id": "RUN_...",
  "thread_id": "THREAD_...",
  "created_at": "2026-05-13T00:00:00Z",
  "user_goal": "string",
  "selected_path": "research",
  "secondary_paths": ["artifact"],
  "known_constraints": ["local-first", "cite sources"],
  "authoritative_state": {
    "thread_context": "context.md",
    "prior_run_state": "run_state.json",
    "topic_memory": null,
    "common_memory": ".stratagem/memory.json"
  },
  "handoff_requirements": ["plan", "extraction", "synthesis", "verification"],
  "stop_conditions": ["missing source", "conflicting dates", "unclear artifact audience"],
  "validation_contract": {
    "minimum_sources": 3,
    "requires_current_web": true,
    "requires_numeric_reconciliation": false,
    "requires_artifact_review": false
  },
  "pay_it_forward": {
    "path": "B",
    "reason": "Agent handoffs and durable state unlock replay, UI status, and evals."
  }
}
```

## Handoff Contracts

Each handoff should answer the same five questions:

1. What did this agent receive?
2. What did it decide or produce?
3. What evidence supports that output?
4. What is unresolved?
5. What should the next agent do with it?

### `PlanHandoff`

```json
{
  "handoff_type": "plan",
  "owner": "research-planner",
  "inputs_used": ["run_contract.json", "context.md"],
  "selected_specialists": ["source-finder", "financial-analyst"],
  "task_graph": [
    {
      "id": "T1",
      "owner": "source-finder",
      "objective": "Find current primary sources",
      "depends_on": []
    }
  ],
  "open_questions": [],
  "stop_conditions": [],
  "next_handoff": "extraction"
}
```

### `ExtractionHandoff`

Captures source list, source quality, extracted claims, timestamps, and access limits. It should separate primary, secondary, and unavailable sources.

### `SynthesisHandoff`

Captures the answer logic: bottom-line claim, MECE supports, confidence by support, contradictions, and implications.

### `VerificationHandoff`

Captures source checks, factual checks, numerical reconciliation, citation coverage, stale-data risk, and failed checks.

### `ArtifactHandoff`

Captures output audience, format, acceptance criteria, included sections, omitted sections, and delivery path.

### `AfterActionHandoff`

Captures what improved the run, what slowed it, what was missing before planning, what should become topic memory, and what should become common memory.

## Pre-Plan Gate

Before calling the planner, Stratagem should run a small deterministic gate:

1. Normalize the user goal.
2. Detect the path and secondary paths.
3. Load thread context and relevant memory pointers.
4. Build `run_contract.json`.
5. Initialize `working_state.json`.
6. Decide whether Path A or Path B applies.
7. Stop and ask if required contract fields are missing.

The planner then receives the contract as a first-class input, not as buried prompt text.

## Stop-And-Ask Conditions

Stop before planning when any of these are true:

- The selected path depends on an audience, artifact format, company, date range, or data source that the user did not specify and cannot be safely inferred.
- The user asks for current facts and web access is unavailable.
- The user asks for financial, legal, medical, or other high-stakes analysis without enough source constraints.
- The user asks to modify external systems, send messages, purchase, delete, or publish.
- The path detector finds two incompatible primary paths.

When stopping, ask one concise question and preserve the partial `run_contract.json` with `status: "blocked"`.

## Implementation Plan

1. **Add data structures with no behavior change.**
   - Add local dataclasses or typed dictionaries for `RunContract`, `WorkingState`, and handoffs.
   - Add JSON read/write helpers under the existing thread storage boundary.

2. **Write the pre-plan contract at run start.**
   - Generate `run_contract.json` before `research-planner`.
   - Initialize `working_state.json` with phase, path, and validation contract.

3. **Inject the contract into the planner prompt.**
   - Replace implicit path instructions with a compact contract block.
   - Keep existing `SYSTEM_PROMPT` role structure, but make the contract authoritative.

4. **Persist handoffs from major phases.**
   - Start with `plan.json`, `verification.json`, and `after_action.json`.
   - Add extraction, synthesis, and artifact handoffs after the first pass is stable.

5. **Expose state to UI and continuation.**
   - The UI should read `working_state.json` for phase/status.
   - Continuation runs should read the prior contract before generating a new one.

6. **Add focused tests.**
   - Unit-test path selection.
   - Unit-test contract serialization.
   - Unit-test that planner prompt includes the selected path and stop conditions.
   - Add one continuation fixture that reuses a prior contract.

## Validation Surface

Minimum validation for the first implementation:

```bash
python -m pytest tests/test_run_contract.py
python -m pytest tests/test_query_routing_policy.py
```

Manual smoke:

```bash
stratagem "quick answer: what changed in the latest OpenAI agent docs?"
stratagem "research Tesla autonomous driving strategy and produce a memo"
stratagem "continue the prior Tesla run and tighten source verification"
```

Expected checks:

- `answer_only` does not create unnecessary handoff files.
- `research` creates a contract with plan, extraction, synthesis, and verification requirements.
- `continuation` references prior thread state.
- The final answer can cite which path was used when the user asks.

## Open Questions

- Should `run_contract.json` be immutable after creation, with revisions in `run_contract.revisions.jsonl`, or should it be mutable with a `revision` field?
- Should specialists write handoff files directly, or should all handoff writes go through the orchestrator?
- Should `record_observation` accept an optional `agent` argument so the system stops storing observations as `unknown` when tool context is missing?
- Should UI status come only from `working_state.json`, or should the event stream remain the primary live source with `working_state.json` as the recovery snapshot?
