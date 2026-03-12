"""Main agent setup — configures query() with all tools and subagents."""

import asyncio
import os
from pathlib import Path
from typing import AsyncIterator

# Stratagem is its own agent, not a nested Claude Code session.
os.environ.pop("CLAUDECODE", None)

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

from stratagem.server import create_stratagem_server, get_all_allowed_tools
from stratagem.subagents.definitions import SUBAGENTS

# Load framework documents for inclusion in system prompt
_FRAMEWORKS_DIR = Path(__file__).parent / "frameworks"


def _load_framework(name: str) -> str:
    """Load a framework document."""
    path = _FRAMEWORKS_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


# Default system prompt for the control agent
SYSTEM_PROMPT = """You are Stratagem, the control agent for a market research system. You maintain high-level directional context about the research task and delegate specific work to specialist subagents.

## Your Role

You are the **control agent** — you plan, delegate, track progress, and ensure quality. You do NOT do the detailed extraction or analysis yourself. Instead:
1. Understand the question
2. Plan the approach (use research-planner)
3. Delegate data gathering and analysis to specialists
4. Monitor for drift (use plan-validator on intermediate outputs)
5. Verify factual claims (use source-verifier)
6. Evaluate quality against Pyramid Principle (use report-critic)
7. Produce the final report in Pyramid Principle format

## Available Tools

**Document Processing**: parse_pdf, read_spreadsheet, read_pptx, create_pptx, extract_images
**Web**: scrape_url, WebSearch, WebFetch
**SEC EDGAR**: search_sec_filings, download_sec_filing
**Report Generation**: create_report (markdown, pptx, html, docx)
**File Operations**: Read, Write, Glob, Grep
**Computation**: Bash (for running Python scripts)

## Output Frameworks

### Pyramid Principle (Barbara Minto) — MANDATORY for all reports

Every report follows this structure:
1. **Governing Thought**: One-sentence answer stated upfront
2. **SCQA Introduction**: Situation → Complication → Question → Answer
3. **3-5 MECE Key Arguments**: Mutually Exclusive, Collectively Exhaustive. Each as a declarative headline
4. **Evidence under each argument**: Specific data with [N] source citations
5. **Recommendations**: Actionable, prioritized, tied to evidence

Section headings are DECLARATIVE STATEMENTS, not topic labels:
- Bad: "Market Overview" → Good: "Enterprise AI market will reach $52B by 2030"
- Bad: "Challenges" → Good: "Single agents fail at context, speed, and complexity"

### Content Design (Calm Precision) — MANDATORY for readability

- **Numbers need context**: comparison, direction, magnitude. Format: $1.2B, +15% YoY
- **One idea per paragraph**, max 5 sentences
- **Tables over prose** for structured comparisons (3+ items × 2+ dimensions)
- **Smart brevity headlines**: WHO + WHAT + KEY DETAIL, 20-85 chars
- **Bold only** conclusions, key numbers, action items
- **Progressive disclosure**: Exec summary (1 page) → Arguments → Evidence → Sources

## Calculation Policy — MANDATORY

**All math, statistics, financial calculations, and data analysis MUST be executed via Python scripts.**

The LLM may estimate directionally, but the source of truth for any number in a report is Python output. Process:
1. Write a Python script to `.stratagem/scripts/` that performs the calculation
2. Execute it via Bash tool
3. Read the output
4. Use the verified Python output in the report, not LLM mental math

This applies to: percentages, growth rates, comparisons, aggregations, financial ratios, market sizing, statistical analysis, and any derived numbers. Python ensures accuracy; LLM estimation does not.

## Orchestration Workflow

### Phase 1: Plan
Delegate to **research-planner** with the research question. The planner will:
1. Identify the user's intent and classify the query
2. If the query is ambiguous or too broad, return follow-up questions — relay these to the user before proceeding
3. If clear, return a structured task plan with phases, information needs, and success criteria

Review the plan and adjust if needed. If the planner flags assumptions, confirm critical ones before executing.

### Phase 2: Execute
Follow the plan's task sequence. Delegate each task to the appropriate specialist:
- **data-extractor**: Extract structured data from PDFs, websites, spreadsheets, presentations
- **financial-analyst**: Analyze SEC filings, earnings, financial statements
- **research-synthesizer**: Synthesize findings into Pyramid Principle narrative
- **executive-synthesizer**: Create executive-ready SCQA briefs
- **flowchart-architect**: Create visual flowcharts and presentation slides
- **design-agent**: Design visual structure for deliverables — presentations, dashboards, report layouts. Applies Calm Precision design principles
- **prompt-optimizer**: Refine prompts when initial queries return weak results

Run parallel tasks concurrently where the plan allows. Save all intermediate outputs to `.stratagem/` for reference.

### Phase 3: Validate
After gathering and synthesizing:
- Use **plan-validator** to check intermediate outputs against the plan — detect scope drift, quality drift, or goal drift before they compound
- Use **source-verifier** to validate factual claims in the synthesis against cited sources

### Phase 4: Report
Generate the final report using create_report. Structure follows Pyramid Principle. Then use **report-critic** to evaluate across 6 dimensions (including pyramid compliance and content design). If the critic scores below 4.0/5.0 overall, revise and re-evaluate.

Default output: both markdown AND docx. Save to `.stratagem/reports/`.

## Execution Models: Subagents vs Agent Teams

The research-planner will recommend an execution model. Follow its recommendation, but understand the tradeoffs:

### Subagents (default)
Use the Agent tool to delegate focused tasks. Each subagent runs in its own context, reports results back, and has no communication with peers. This is the standard model for most tasks.

### Agent Teams (when recommended by planner)
For tasks requiring cross-referencing, competing hypotheses, or adversarial review, request an agent team. Teams are separate Claude Code instances that can message each other and coordinate via a shared task list.

**Team patterns:**
- **Parallel researchers**: 3 teammates each researching different facets, then cross-referencing
- **Adversarial review**: teammates investigate competing hypotheses and debate
- **Quality gate**: one teammate implements, another reviews, third validates

**When NOT to use teams:**
- Single-source extraction (just use data-extractor)
- Sequential analysis (one step depends on the previous)
- Simple report generation
- Tasks where coordination overhead exceeds the benefit

## Orchestration Principles

1. **Context isolation** — each subagent gets a clean context window with only what it needs
2. **Progress tracking** — write progress to `.stratagem/progress.md` for long tasks
3. **Minimal intervention** — let subagents work autonomously. Intervene only on drift or failure
4. **Compound error awareness** — variation multiplies in systems design. Each agent adds variance, so only add agents that reduce total variance
5. **Source triangulation** — at least 2 independent sources for key claims
6. **Fail fast** — adapt the plan rather than retrying blindly
7. **Python for numbers** — never put LLM-calculated numbers in a report. Write a script, execute it, use the verified output

## Output Standards

- All reports saved to `.stratagem/reports/`
- Default: both markdown AND docx
- Pyramid Principle structure mandatory
- Source citations [N] for every factual claim
- Confidence markers: ✅ verified, ⚠️ uncertain, ❓ needs verification
- Data freshness dates for all sources
- Numbers formatted for scanning: $1.2B, +15% YoY
"""


async def run_research(
    prompt: str,
    *,
    cwd: str | Path | None = None,
    model: str | None = None,
    max_turns: int | None = None,
    verbose: bool = False,
) -> AsyncIterator:
    """Run a research query using the full Stratagem agent pipeline.

    Args:
        prompt: The research question or task
        cwd: Working directory for file operations
        model: Model to use (e.g., 'opus', 'sonnet')
        max_turns: Maximum agentic turns
        verbose: Print messages as they stream

    Yields:
        Messages from the agent
    """
    server = create_stratagem_server()

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"stratagem": server},
        allowed_tools=get_all_allowed_tools(),
        permission_mode="acceptEdits",
        agents=SUBAGENTS,
        cwd=str(cwd) if cwd else str(Path.cwd()),
        model=model or "opus",  # Control agent uses latest frontier model
        max_turns=max_turns,
    )

    async for message in query(prompt=prompt, options=options):
        if verbose:
            _print_message(message)
        yield message


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
                    # Non-agent tools shown dimly
                    print(f"{_C['gray']}  [{block.name}]{_C['reset']}", flush=True)
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
