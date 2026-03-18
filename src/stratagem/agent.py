"""Main agent setup — configures query() with all tools and subagents."""

import asyncio
import json
import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Awaitable, Callable

# Stratagem is its own agent, not a nested Claude Code session.
os.environ.pop("CLAUDECODE", None)

from claude_agent_sdk import (
    query,
    AgentDefinition,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

from stratagem.server import create_stratagem_server, get_all_allowed_tools
from stratagem.subagents.definitions import SUBAGENTS

# Mutable agents dict for the active run — read by create_specialist tool
_active_run_agents: dict | None = None

# Dynamic agents created during this run — persisted on completion
_dynamic_agents_created: dict = {}

# Default system prompt for the control agent
SYSTEM_PROMPT = """You are Stratagem, the control agent for a strategic research system. You plan, delegate to specialist subagents, track progress, and ensure quality. You do NOT do detailed extraction or analysis yourself.

You serve product strategists, corporate strategists, and technology leaders. Questions may span competitive analysis, product strategy, technology landscape, financial analysis, market sizing, or any domain requiring structured research. You don't impose frameworks — you research, structure findings using MECE decomposition and Pyramid Principle, and deliver evidence-based answers.

## Workflow

1. **Plan**: Delegate to research-planner → get structured task plan. Relay follow-up questions if query is ambiguous.
2. **Execute**: Delegate tasks to specialists per the plan. Run parallel where possible. Save intermediates to `.stratagem/`.
   - data-extractor (PDFs, websites, documents) · financial-analyst (SEC filings, financials — when relevant) · research-synthesizer (MECE + Pyramid narrative) · executive-synthesizer (SCQA briefs) · flowchart-architect (visuals) · design-agent (layout, Calm Precision) · prompt-optimizer (refine weak queries)
3. **Validate**: plan-validator checks for drift · source-verifier validates claims against cited sources
4. **Report**: create_report → report-critic evaluates (threshold: 4.0/5.0). Revise if below. Default: markdown + docx to `.stratagem/reports/`.
5. **Learn**: after-action-analyst conducts a post-run debrief and records lessons for future runs.

Default to subagents. Use agent teams only when research-planner recommends it (cross-referencing, adversarial review, quality gates). Dispatch financial-analyst only when the question involves financial data — it is not the default lens.

## Tools

Document: parse_pdf, read_spreadsheet, read_pptx, create_pptx, extract_images · Web: scrape_url, WebSearch, WebFetch · SEC: search_sec_filings, download_sec_filing · Output: create_report (md/pptx/html/docx), create_spreadsheet · Files: Read, Write, Glob, Grep · Compute: Bash

## Output Frameworks — MANDATORY

**Pyramid Principle** (all reports): Governing thought upfront → SCQA intro → 3-5 MECE arguments as declarative headlines → evidence with [N] citations → actionable recommendations. Headings are statements ("AI market reaches $52B by 2030"), not labels ("Market Overview").

**Content Design**: Numbers need context ($1.2B, +15% YoY). One idea per paragraph. Tables over prose for 3+ comparisons. Smart brevity: WHO+WHAT+KEY DETAIL 20-85 chars. Bold only conclusions/key numbers. Progressive disclosure: exec summary → arguments → evidence → sources.

## Calculation Policy

All math/statistics/financial calculations MUST run as Python scripts in `.stratagem/scripts/`. Execute via Bash, use verified output in reports. LLM estimation is directional only — Python output is source of truth.

## Dynamic Specialists

If research-planner identifies a capability gap, you may create a temporary specialist using `create_specialist`. Criteria:
- Genuine gap — no existing agent covers the task adequately
- Substantial task — not a one-off query you could handle directly
- Clear instructions — the specialist prompt should be focused and actionable

After creation, dispatch the new specialist by name like any other agent.

## Memory

You have access to research memory from prior runs on this topic. The scaffold summary is injected above. For full details, use Read to load the pointer files listed in the scaffold.

When you or your agents discover something worth remembering:
- Source reliability (paywalls, stale data, good sources) → record_observation category:source
- Key verified findings → record_observation category:finding
- Process learnings (what worked/failed) → record_observation category:process
- Agent quality assessments → record_observation category:agent

Quality agents (source-verifier, plan-validator, report-critic) may spot-check observations using related_to links. This is routine — not an override.

## Principles

- Context isolation per subagent · Progress to `.stratagem/progress.md` · Minimal intervention — intervene on drift/failure only
- Compound error: each agent adds variance — only add agents that reduce total variance · 2+ independent sources for key claims
- Fail fast — adapt plan, don't retry blindly
- Require structured handoffs — planner, validators, critic, and debrief should leave explicit next-step guidance, not just prose summaries

## Artifact Verification — MANDATORY

**Never claim a file was created without verifying it exists.**

After file-creation (create_report, create_pptx, create_spreadsheet, Write):
1. Verify with Glob or `ls -la <absolute_path>` — confirm exists and non-zero size
2. Report absolute path and size to user

**Always use absolute paths.** If a tool fails: report the failure, explain any fallback, verify fallback result. "⚠️ Unable to create the file" is always acceptable.

## Rationale Logging

Before final answer, include `## Rationale` (2-5 lines): approach chosen and why, key decisions, what worked/didn't.

## Output Standards

Save to the output directory (see Output Location). Pyramid structure mandatory. [N] citations for all claims. Markers: ✅ verified · ⚠️ uncertain · ❓ needs verification. Data freshness dates. Numbers: $1.2B, +15% YoY.
"""


def _log_memory_persistence_error(*, cwd: Path, thread_id: str | None, exc: Exception) -> None:
    """Record non-fatal memory persistence failures for later debugging."""
    log_dir = cwd / ".stratagem" / "logs"
    log_path = log_dir / "memory_errors.log"
    entry = {
        "timestamp": datetime.now().isoformat(),
        "thread_id": thread_id,
        "error": repr(exc),
        "traceback": traceback.format_exc(),
    }
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def _tail_text_lines(path: Path, count: int) -> list[str]:
    """Read the last N text lines from a file."""
    if count <= 0 or not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            lines = [line.rstrip("\n") for line in f]
    except OSError:
        return []
    return [line for line in lines[-count:] if line.strip()]


def _derive_delegation_budget(
    *,
    prompt: str,
    input_files: list[str] | None,
    thread_id: str | None,
) -> dict[str, object]:
    """Derive orchestration limits from task shape.

    The goal is not perfect classification. It is to give the control agent an
    explicit operating envelope so delegation is less improvised.
    """
    text = prompt.lower()
    complexity = 0

    complex_signals = (
        "compare",
        "competitive",
        "landscape",
        "market sizing",
        "strategy",
        "strategic",
        "financial",
        "earnings",
        "10-k",
        "10q",
        "due diligence",
        "build vs buy",
        "technology",
        "multi",
    )
    if any(token in text for token in complex_signals):
        complexity += 2
    if len(prompt) > 400:
        complexity += 1
    if input_files and len(input_files) >= 2:
        complexity += 1
    if thread_id:
        complexity += 1

    if complexity >= 4:
        mode = "deep"
        budget = {
            "mode": mode,
            "max_agent_dispatches": 7,
            "max_parallel_tasks": 4,
            "max_validation_passes": 2,
            "max_dynamic_specialists": 2,
            "planner_mode": "required",
        }
    elif complexity >= 2:
        mode = "standard"
        budget = {
            "mode": mode,
            "max_agent_dispatches": 5,
            "max_parallel_tasks": 3,
            "max_validation_passes": 1,
            "max_dynamic_specialists": 1,
            "planner_mode": "recommended",
        }
    else:
        mode = "lean"
        budget = {
            "mode": mode,
            "max_agent_dispatches": 3,
            "max_parallel_tasks": 2,
            "max_validation_passes": 1,
            "max_dynamic_specialists": 0,
            "planner_mode": "skip-if-simple",
        }

    budget["finance_bias"] = any(token in text for token in ("financial", "earnings", "10-k", "10q", "sec"))
    budget["document_bias"] = bool(input_files) or any(token in text for token in ("pdf", "spreadsheet", "ppt", "document"))
    budget["thread_context_available"] = bool(thread_id)
    return budget


def _format_delegation_budget(budget: dict[str, object]) -> str:
    """Render delegation policy for the system prompt."""
    return f"""

## Orchestration Budget

Mode: `{budget["mode"]}`
- Max agent dispatches: {budget["max_agent_dispatches"]}
- Max parallel tasks in a phase: {budget["max_parallel_tasks"]}
- Max validation passes: {budget["max_validation_passes"]}
- Max dynamic specialists created: {budget["max_dynamic_specialists"]}
- Planner mode: {budget["planner_mode"]}

Rules:
- Use the minimum agent set that can reliably answer the request.
- Every dispatched agent must reduce uncertainty, add required evidence, or produce a required artifact.
- Prefer parallel execution only for independent tasks with distinct evidence inputs.
- Do not create a dynamic specialist unless existing agents are demonstrably insufficient and the budget allows it.
- Reuse prior thread/topic artifacts before dispatching new extraction work.
"""


def _track_budget_event(warnings: list[str], message: str) -> None:
    if message not in warnings:
        warnings.append(message)


def _build_after_action_prompt(
    *,
    prompt: str,
    result_text: str,
    rationale: str | None,
    thread_id: str,
    topic_id: str | None,
    turn_count: int,
    cost_usd: float | None,
    tools_used: set[str],
    scripts_written: list[str],
    dynamic_agents_created: dict,
    input_files: list[str] | None,
    observations: list[str],
    delegation_budget: dict[str, object] | None = None,
    agent_dispatches: list[dict] | None = None,
    orchestration_warnings: list[str] | None = None,
) -> str:
    """Build the input payload for the after-action analyst."""
    response_excerpt = result_text[-4000:] if len(result_text) > 4000 else result_text
    sections = [
        f"Thread ID: {thread_id}",
        f"Topic ID: {topic_id or 'none'}",
        f"Turns: {turn_count}",
        f"Cost USD: {cost_usd if cost_usd is not None else 'unknown'}",
        "",
        "## User Request",
        prompt,
        "",
        "## Final Response Excerpt",
        response_excerpt or "No final response captured.",
        "",
        "## Rationale",
        rationale or "No explicit rationale captured.",
        "",
        "## Tools Used",
        ", ".join(sorted(tools_used)) if tools_used else "None recorded.",
        "",
        "## Scripts Written",
        "\n".join(f"- {fp}" for fp in scripts_written) if scripts_written else "None.",
        "",
        "## Dynamic Agents Created",
        "\n".join(f"- {name}" for name in sorted(dynamic_agents_created)) if dynamic_agents_created else "None.",
        "",
        "## Input Files",
        "\n".join(f"- {fp}" for fp in (input_files or [])) if input_files else "None.",
        "",
        "## Delegation Budget",
        json.dumps(delegation_budget or {}, indent=2, sort_keys=True),
        "",
        "## Agent Dispatches",
        "\n".join(f"- {entry}" for entry in (agent_dispatches or [])) if agent_dispatches else "None recorded.",
        "",
        "## Orchestration Warnings",
        "\n".join(f"- {item}" for item in (orchestration_warnings or [])) if orchestration_warnings else "None.",
        "",
        "## Observations",
        "\n".join(f"- {line}" for line in observations) if observations else "None recorded.",
    ]
    return "\n".join(sections).strip()


def _fallback_after_action_review(
    *,
    prompt: str,
    result_text: str,
    rationale: str | None,
    tools_used: set[str],
    dynamic_agents_created: dict,
    observations: list[str],
    delegation_budget: dict[str, object] | None = None,
    orchestration_warnings: list[str] | None = None,
    failure: Exception | None = None,
) -> str:
    """Generate a deterministic fallback after-action review."""
    tools_line = ", ".join(sorted(tools_used)) if tools_used else "No tools recorded."
    observation_preview = observations[:5]
    lines = [
        "# After Action Review",
        "",
        "## Mission",
        f"- {prompt[:300]}",
        "",
        "## Outcome",
        f"- Final response captured: {'yes' if result_text.strip() else 'no'}",
        f"- Explicit rationale captured: {'yes' if rationale else 'no'}",
        "",
        "## Sustains",
        f"- Tool coverage used: {tools_line}",
        f"- Dynamic specialists created: {len(dynamic_agents_created)}",
        f"- Delegation mode: {(delegation_budget or {}).get('mode', 'unknown')}",
        "",
        "## Improves",
        "- Add more explicit source-quality notes when uncertainty remains.",
        "- Capture clearer success/failure signals for each specialist run.",
        "",
        "## Source Assessment",
        "- Use recorded observations and verifier output to rank source reliability next run.",
        "",
        "## Agent Assessment",
        f"- Dynamic agent count this run: {len(dynamic_agents_created)}",
        "",
        "## Memory Recommendations",
    ]
    if observation_preview:
        lines.extend(f"- [topic] Review observation: {line[:180]}" for line in observation_preview)
    else:
        lines.append("- [thread] No observations were recorded during this run.")
    lines.extend([
        "",
        "## Capability Gaps",
        "- No meta-learning inference beyond recorded observations in fallback mode.",
        "",
        "## Next Run",
        "- Ensure verifier/critic outputs are captured explicitly in observations.",
        "- Promote repeated successful specialists only with evidence.",
    ])
    if orchestration_warnings:
        lines.extend([
            "",
            "## Speed Opportunities",
            *[f"- {item}" for item in orchestration_warnings[:5]],
        ])
    if failure is not None:
        lines.extend([
            "",
            "## Notes",
            f"- Fallback generated because after-action analyst failed: {failure}",
        ])
    return "\n".join(lines)


async def _default_after_action_runner(
    *,
    system_prompt: str,
    prompt_text: str,
    cwd: Path,
    model: str,
) -> str:
    """Run the after-action analyst using the Claude agent SDK."""
    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        allowed_tools=["Read"],
        permission_mode="acceptEdits",
        cwd=str(cwd),
        model=model,
        max_turns=1,
    )

    review_text = ""
    async for message in query(prompt=prompt_text, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    review_text += block.text
    return review_text.strip()


async def _generate_after_action_review(
    *,
    cwd: Path,
    thread_id: str,
    topic_id: str | None,
    prompt: str,
    result_text: str,
    rationale: str | None,
    turn_count: int,
    cost_usd: float | None,
    tools_used: set[str],
    scripts_written: list[str],
    dynamic_agents_created: dict,
    input_files: list[str] | None,
    model_overrides: dict[str, str] | None,
    delegation_budget: dict[str, object],
    agent_dispatches: list[dict],
    orchestration_warnings: list[str],
    runner: Callable[..., Awaitable[str]] | None = None,
) -> Path:
    """Generate and persist an after-action review for the completed run."""
    thread_dir = cwd / ".stratagem" / "threads" / thread_id
    obs_path = thread_dir / "observations.jsonl"
    observations = _tail_text_lines(obs_path, 20)
    agent_def = SUBAGENTS["after-action-analyst"]
    review_prompt = _build_after_action_prompt(
        prompt=prompt,
        result_text=result_text,
        rationale=rationale,
        thread_id=thread_id,
        topic_id=topic_id,
        turn_count=turn_count,
        cost_usd=cost_usd,
        tools_used=tools_used,
        scripts_written=scripts_written,
        dynamic_agents_created=dynamic_agents_created,
        input_files=input_files,
        observations=observations,
        delegation_budget=delegation_budget,
        agent_dispatches=agent_dispatches,
        orchestration_warnings=orchestration_warnings,
    )
    runner = runner or _default_after_action_runner
    model = (model_overrides or {}).get("after-action-analyst", agent_def.model) or agent_def.model

    failure: Exception | None = None
    try:
        review_text = await runner(
            system_prompt=agent_def.prompt,
            prompt_text=review_prompt,
            cwd=cwd,
            model=model,
        )
    except Exception as exc:
        failure = exc
        review_text = ""

    if not review_text.strip():
        review_text = _fallback_after_action_review(
            prompt=prompt,
            result_text=result_text,
            rationale=rationale,
            tools_used=tools_used,
            dynamic_agents_created=dynamic_agents_created,
            observations=observations,
            delegation_budget=delegation_budget,
            orchestration_warnings=orchestration_warnings,
            failure=failure,
        )

    report_path = thread_dir / "after_action.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(review_text.strip() + "\n", encoding="utf-8")
    return report_path


async def run_research(
    prompt: str,
    *,
    cwd: str | Path | None = None,
    output_dir: str | Path | None = None,
    model: str | None = None,
    model_overrides: dict[str, str] | None = None,
    max_turns: int | None = None,
    verbose: bool = False,
    thread_id: str | None = None,
    topic_id: str | None = None,
    input_files: list[str] | None = None,
    memory_budget: int | None = None,
) -> AsyncIterator:
    """Run a research query using the full Stratagem agent pipeline.

    Args:
        prompt: The research question or task
        cwd: Working directory for file operations
        output_dir: Directory for output artifacts (None = ask user)
        model: Model to use (e.g., 'opus', 'sonnet')
        model_overrides: Per-agent model overrides
        max_turns: Maximum agentic turns
        verbose: Print messages as they stream
        thread_id: Optional thread ID for context retention across queries
        topic_id: Optional topic ID for memory grouping
        input_files: Optional list of input file paths to include in context
        memory_budget: Optional memory token budget (default 8000)

    Yields:
        Messages from the agent
    """
    effective_cwd = Path(cwd) if cwd else Path.cwd()
    _run_started = datetime.now()
    delegation_budget = _derive_delegation_budget(
        prompt=prompt,
        input_files=input_files,
        thread_id=thread_id,
    )

    # Inject prior thread context into system prompt
    system = SYSTEM_PROMPT
    if thread_id:
        from stratagem.threads import load_context
        ctx = load_context(thread_id, cwd=effective_cwd)
        if ctx:
            system += (
                "\n\n## Prior Research Context\n\n"
                + ctx
                + "\n\nUse this context to inform your response. "
                "Prior artifacts are in `stratagem/artifacts/`."
            )

    # Inject memory scaffold
    from stratagem.memory import build_scaffold
    scaffold = build_scaffold(
        topic_id=topic_id,
        cwd=effective_cwd,
        memory_budget=memory_budget or 8000,
    )
    if scaffold:
        system = scaffold + "\n\n" + system  # Scaffold at context START (high-accuracy zone)
    system += _format_delegation_budget(delegation_budget)

    # Output directory configuration
    if output_dir:
        resolved_output = Path(output_dir).resolve()
        resolved_output.mkdir(parents=True, exist_ok=True)
        system += f"""

## Output Location

Default output directory: `{resolved_output}`

Before creating the first artifact, state: "Saving to {resolved_output}" — if the user specified a different path in their prompt, use that instead. Use this directory for all artifacts unless the user redirects.
"""
    else:
        system += """

## Output Location

No output directory was specified. Before creating your first artifact, ask the user where they'd like files saved. Suggest `<working_dir>/output/` as default. Once confirmed, use that directory for all artifacts in this session.
"""

    # Input files injection
    if input_files:
        file_lines = []
        for fp in input_files:
            p = Path(fp).resolve()
            if p.exists():
                size = p.stat().st_size
                suffix = p.suffix.lstrip(".")
                if size > 1_000_000:
                    size_str = f"{size / 1_000_000:.1f}MB"
                else:
                    size_str = f"{size / 1000:.0f}KB"
                file_lines.append(f"- {p} ({suffix.upper()}, {size_str})")
            else:
                file_lines.append(f"- {fp} (NOT FOUND — file may have moved)")
        system += "\n\n## Input Files\n\n" + "\n".join(file_lines)

    # Set active thread dir for record_observation tool
    if thread_id:
        import stratagem.tools.memory as _mem_mod
        _mem_mod._active_thread_dir = effective_cwd / ".stratagem" / "threads" / thread_id
        _mem_mod._active_observation_index = None

    server = create_stratagem_server()

    # Build mutable agents dict with model overrides applied
    global _active_run_agents, _dynamic_agents_created
    all_agents: dict[str, AgentDefinition] = {}
    for name, agent_def in SUBAGENTS.items():
        override_model = (model_overrides or {}).get(name)
        if override_model and override_model != agent_def.model:
            from claude_agent_sdk import AgentDefinition as _AD
            all_agents[name] = _AD(
                description=agent_def.description,
                prompt=agent_def.prompt,
                tools=agent_def.tools,
                model=override_model,
            )
        else:
            all_agents[name] = agent_def
    _active_run_agents = all_agents
    _dynamic_agents_created = {}

    # Load dynamic agents (tier 2 persistent, tier 1 topic-scoped)
    from stratagem.memory import load_dynamic_agents
    dynamic = load_dynamic_agents(topic_id=topic_id, cwd=effective_cwd)
    for name, agent_data in dynamic.items():
        if name not in all_agents:  # Don't override permanent agents (tier 3)
            from claude_agent_sdk import AgentDefinition as _AD
            all_agents[name] = _AD(
                description=agent_data.get("description", ""),
                prompt=agent_data.get("prompt", ""),
                tools=agent_data.get("tools", ["Read", "Write", "WebSearch"]),
                model=agent_data.get("model", "sonnet"),
            )

    options = ClaudeAgentOptions(
        system_prompt=system,
        mcp_servers={"stratagem": server},
        allowed_tools=get_all_allowed_tools(),
        permission_mode="acceptEdits",
        agents=all_agents,
        cwd=str(effective_cwd),
        model=model or "opus",  # Control agent uses latest frontier model
        max_turns=max_turns,
    )

    # Accumulate result data for thread persistence
    result_text = ""
    turn_count = 0
    cost_usd = None
    tools_used: set[str] = set()
    scripts_written: list[str] = []
    rationale = None
    agent_dispatches: list[dict[str, object]] = []
    agent_dispatch_count = 0
    validation_passes = 0
    orchestration_warnings: list[str] = []

    try:
        async for message in query(prompt=prompt, options=options):
            # Collect data for thread entry
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        result_text += block.text
                    elif isinstance(block, ToolUseBlock):
                        tools_used.add(block.name)
                        if block.name == "Agent":
                            agent_name = _extract_agent_name(block.input)
                            if agent_name:
                                agent_dispatch_count += 1
                                entry = {
                                    "name": agent_name,
                                    "action": _AGENT_ACTIONS.get(agent_name, "working"),
                                    "model": (model_overrides or {}).get(agent_name, _AGENT_MODELS.get(agent_name, "sonnet")),
                                    "dispatch_index": agent_dispatch_count,
                                }
                                agent_dispatches.append(entry)
                                if agent_name in ("plan-validator", "source-verifier", "report-critic"):
                                    validation_passes += 1
                                if agent_dispatch_count > int(delegation_budget["max_agent_dispatches"]):
                                    _track_budget_event(
                                        orchestration_warnings,
                                        f"Agent dispatch budget exceeded ({agent_dispatch_count}/{delegation_budget['max_agent_dispatches']}).",
                                    )
                                if validation_passes > int(delegation_budget["max_validation_passes"]):
                                    _track_budget_event(
                                        orchestration_warnings,
                                        f"Validation pass budget exceeded ({validation_passes}/{delegation_budget['max_validation_passes']}).",
                                    )
                        elif block.name == "mcp__stratagem__create_specialist":
                            projected = len(_dynamic_agents_created) + 1
                            if projected > int(delegation_budget["max_dynamic_specialists"]):
                                _track_budget_event(
                                    orchestration_warnings,
                                    f"Dynamic specialist budget exceeded ({projected}/{delegation_budget['max_dynamic_specialists']}).",
                                )
                        # Track scripts written to .stratagem/scripts/
                        if block.name == "Write" and isinstance(block.input, dict):
                            fp = block.input.get("file_path", "")
                            if ".stratagem/scripts/" in fp or "stratagem/scripts/" in fp:
                                scripts_written.append(fp)
            elif isinstance(message, ResultMessage):
                turn_count = message.num_turns
                cost_usd = message.total_cost_usd

            if verbose:
                _print_message(message)
            yield message
    finally:
        # Clear active thread dir
        import stratagem.tools.memory as _mem_mod
        _mem_mod._active_thread_dir = None
        _mem_mod._active_observation_index = None

        # Post-run: aggregate observations + persist dynamic agents
        if thread_id:
            from stratagem.memory import aggregate_observations, persist_dynamic_agents, check_promotion
            try:
                aggregate_observations(thread_id=thread_id, topic_id=topic_id, cwd=effective_cwd)

                # Persist any dynamic agents created during this run
                if _dynamic_agents_created:
                    persist_dynamic_agents(
                        definitions=_dynamic_agents_created,
                        topic_id=topic_id,
                        cwd=effective_cwd,
                    )

                # Check promotion criteria
                check_promotion(cwd=effective_cwd)
            except Exception as exc:
                _log_memory_persistence_error(cwd=effective_cwd, thread_id=thread_id, exc=exc)

        _active_run_agents = None
        # Persist thread entry even if generator abandoned early
        if thread_id and (result_text or turn_count > 0):
            from stratagem.threads import append_entry

            # Extract rationale block if present
            if "## Rationale" in result_text:
                idx = result_text.index("## Rationale")
                rationale_block = result_text[idx + len("## Rationale"):].strip()
                # Take up to next heading or 500 chars
                end = rationale_block.find("\n## ")
                if end > 0:
                    rationale = rationale_block[:end].strip()
                else:
                    rationale = rationale_block[:500].strip()

            # Use last 500 chars as summary (the agent's final output)
            summary = result_text[-500:] if len(result_text) > 500 else result_text
            append_entry(
                thread_id,
                cwd=effective_cwd,
                query=prompt,
                summary=summary,
                turns=turn_count,
                cost=cost_usd,
                rationale=rationale,
                tools_used=sorted(tools_used),
                scripts=scripts_written,
            )

            try:
                after_action_path = await _generate_after_action_review(
                    cwd=effective_cwd,
                    thread_id=thread_id,
                    topic_id=topic_id,
                    prompt=prompt,
                    result_text=result_text,
                    rationale=rationale,
                    turn_count=turn_count,
                    cost_usd=cost_usd,
                    tools_used=tools_used,
                    scripts_written=scripts_written,
                    dynamic_agents_created=_dynamic_agents_created,
                    input_files=input_files,
                    model_overrides=model_overrides,
                    delegation_budget=delegation_budget,
                    agent_dispatches=agent_dispatches,
                    orchestration_warnings=orchestration_warnings,
                )
            except Exception as exc:
                after_action_path = None
                _log_memory_persistence_error(cwd=effective_cwd, thread_id=thread_id, exc=exc)
        else:
            after_action_path = None

        # Write run_state.json
        if thread_id:
            run_state = {
                "thread_id": thread_id,
                "topic_id": topic_id,
                "started": _run_started.isoformat() if _run_started else None,
                "completed": datetime.now().isoformat(),
                "model": model or "opus",
                "model_overrides": model_overrides or {},
                "input_files": input_files or [],
                "output_dir": str(Path(output_dir).resolve()) if output_dir else None,
                "memory_budget": memory_budget or 8000,
                "delegation_budget": delegation_budget,
                "orchestration_warnings": orchestration_warnings,
                "agents_dispatched": agent_dispatches,
                "tools_used": {t: 1 for t in sorted(tools_used)},
                "total_turns": turn_count,
                "cost_usd": cost_usd,
                "dynamic_agents_created": list(_dynamic_agents_created.keys()),
                "dynamic_agent_definitions": _dynamic_agents_created,
                "after_action_report": str(after_action_path) if after_action_path else None,
                "observations_count": 0,
            }
            run_state_path = effective_cwd / ".stratagem" / "threads" / thread_id / "run_state.json"
            try:
                run_state_path.parent.mkdir(parents=True, exist_ok=True)
                run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")
            except OSError:
                pass

        _dynamic_agents_created = {}


_AGENT_MODELS = {
    "research-planner": "sonnet",
    "data-extractor": "sonnet",
    "financial-analyst": "opus",
    "research-synthesizer": "opus",
    "executive-synthesizer": "sonnet",
    "flowchart-architect": "sonnet",
    "design-agent": "sonnet",
    "prompt-optimizer": "sonnet",
    "plan-validator": "sonnet",
    "source-verifier": "sonnet",
    "report-critic": "sonnet",
    "after-action-analyst": "sonnet",
}

_AGENT_ACTIONS = {
    "research-planner": "planning",
    "data-extractor": "extracting data",
    "financial-analyst": "analyzing financials",
    "research-synthesizer": "synthesizing",
    "executive-synthesizer": "writing brief",
    "flowchart-architect": "designing visuals",
    "design-agent": "designing layout",
    "prompt-optimizer": "refining prompts",
    "plan-validator": "checking drift",
    "source-verifier": "verifying sources",
    "report-critic": "evaluating quality",
    "after-action-analyst": "conducting after-action review",
}

# ANSI colors
_C = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "blue": "\033[34m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "cyan": "\033[36m",
    "magenta": "\033[35m",
    "gray": "\033[90m",
}


def _model_color(model: str) -> str:
    if model == "opus":
        return _C["yellow"]
    if model == "sonnet":
        return _C["blue"]
    return _C["green"]


def _extract_agent_name(tool_input) -> str | None:
    """Extract the agent/subagent name from an Agent tool call input."""
    if isinstance(tool_input, dict):
        for key in ("agent", "name", "agent_name", "subagent"):
            if key in tool_input:
                return tool_input[key]
        prompt = tool_input.get("prompt", "")
        if isinstance(prompt, str):
            for name in _AGENT_ACTIONS:
                if name in prompt.lower():
                    return name
    return None


# Track active agents for CLI display
_active_agents: set[str] = set()


def _describe_tool_call(name: str, input_data: dict | None) -> str:
    """Generate a concise description of a tool call for CLI display."""
    if not isinstance(input_data, dict):
        return f"[{name}]"

    if name == "Bash":
        cmd = input_data.get("command", "")
        short = cmd.split("\n")[0][:80]
        return f"[Bash] {short}"

    if name == "Write":
        path = input_data.get("file_path", "")
        fname = Path(path).name if path else "?"
        return f"[Write] {fname}"

    if name == "Read":
        path = input_data.get("file_path", "")
        fname = Path(path).name if path else "?"
        return f"[Read] {fname}"

    if name == "Glob":
        pattern = input_data.get("pattern", "")
        return f"[Glob] {pattern}"

    if name == "Grep":
        pattern = input_data.get("pattern", "")
        return f"[Grep] {pattern[:60]}"

    if name in ("WebSearch", "WebFetch"):
        query = input_data.get("query", input_data.get("url", ""))
        return f"[{name}] {str(query)[:60]}"

    if name.startswith("mcp__stratagem__"):
        tool_name = name.replace("mcp__stratagem__", "")
        path = input_data.get("output_path", input_data.get("file_path", ""))
        if path:
            return f"[{tool_name}] → {Path(path).name}"
        return f"[{tool_name}]"

    return f"[{name}]"


def _print_message(message):
    """Print a message to stdout for CLI usage with agent activity tracking."""
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                print(block.text, end="", flush=True)
            elif isinstance(block, ToolUseBlock):
                if block.name == "Agent":
                    agent_name = _extract_agent_name(block.input)
                    if agent_name:
                        model = _AGENT_MODELS.get(agent_name, "sonnet")
                        action = _AGENT_ACTIONS.get(agent_name, "working")
                        mc = _model_color(model)
                        print(
                            f"\n{_C['cyan']}▸{_C['reset']} "
                            f"{_C['bold']}{agent_name}{_C['reset']} "
                            f"{mc}[{model}]{_C['reset']} "
                            f"{_C['dim']}{action}{_C['reset']}",
                            flush=True,
                        )
                        _active_agents.add(agent_name)
                else:
                    desc = _describe_tool_call(block.name, block.input)
                    print(f"{_C['gray']}  {desc}{_C['reset']}", flush=True)
    elif isinstance(message, ResultMessage):
        # Clear active agents
        for name in _active_agents:
            print(
                f"{_C['green']}✓{_C['reset']} {name} {_C['dim']}done{_C['reset']}",
                flush=True,
            )
        _active_agents.clear()
        duration = message.duration_ms
        if duration > 60000:
            time_str = f"{duration / 60000:.1f}m"
        else:
            time_str = f"{duration / 1000:.1f}s"
        print(f"\n{_C['green']}━━━ Done{_C['reset']} ({message.num_turns} turns, {time_str})", flush=True)
        if message.total_cost_usd:
            print(f"{_C['dim']}Cost: ${message.total_cost_usd:.4f}{_C['reset']}", flush=True)
