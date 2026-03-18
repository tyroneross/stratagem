"""Subagent definitions — AgentDefinition configs for all specialist agents."""

from pathlib import Path

from claude_agent_sdk import AgentDefinition

PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    """Load a system prompt from the prompts directory."""
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


# MCP tool names (namespaced under stratagem server)
_S = "mcp__stratagem__"

SUBAGENTS: dict[str, AgentDefinition] = {
    "data-extractor": AgentDefinition(
        description="Extract and verify data from PDFs, websites, spreadsheets, and presentations. Use for structured data extraction tasks.",
        prompt=_load_prompt("data_extractor"),
        tools=[
            f"{_S}parse_pdf",
            f"{_S}scrape_url",
            f"{_S}read_spreadsheet",
            f"{_S}read_pptx",
            f"{_S}extract_images",
            f"{_S}create_spreadsheet",
            "Read",
            "Glob",
            "WebSearch",  # C4: needs to discover URLs, not just scrape known ones
        ],
        model="sonnet",
    ),
    "research-synthesizer": AgentDefinition(
        description="Synthesize research from multiple extracted data sources into comprehensive, authoritative narratives with citations.",
        prompt=_load_prompt("research_synthesizer"),
        tools=[
            "Read",
            "Write",
            "WebSearch",  # C3: needs source access for citation verification
            f"{_S}scrape_url",
        ],
        model="opus",
    ),
    "executive-synthesizer": AgentDefinition(
        description="Create executive-ready research briefs with strategic framing, actionable conclusions, and confidence assessments.",
        prompt=_load_prompt("executive_synthesizer"),
        tools=[
            "Read",
            "Write",
        ],
        model="sonnet",  # I3/O1: reformats synthesis output; strong prompt compensates
    ),
    "financial-analyst": AgentDefinition(
        description="Analyze SEC filings, earnings reports, and financial statements. Extracts metrics, identifies trends, and produces financial analysis.",
        prompt=_load_prompt("financial_analyst"),
        tools=[
            f"{_S}search_sec_filings",
            f"{_S}download_sec_filing",
            f"{_S}read_spreadsheet",
            f"{_S}parse_pdf",
            f"{_S}create_spreadsheet",
            "Read",
            "Write",
            "Bash",  # C2: needed for Python script execution (Calculation Policy)
        ],
        model="opus",
    ),
    "flowchart-architect": AgentDefinition(
        description="Design process architectures and create flowchart visualizations as PowerPoint presentations.",
        prompt=_load_prompt("flowchart_architect"),
        tools=[
            f"{_S}create_pptx",
            "Read",
            "Write",
        ],
        model="sonnet",  # I3/O1: generating PPTX structures doesn't need opus
    ),
    "prompt-optimizer": AgentDefinition(
        description="Analyze, refine, and optimize research prompts for accuracy, specificity, and reliability.",
        prompt=_load_prompt("prompt_optimizer"),
        tools=["Read", "Write"],
        model="sonnet",  # I3/O1: structured refinement, not creative task
    ),
    # ── Architecture-driven agents ──
    "research-planner": AgentDefinition(
        description="Decompose research questions into structured task plans. Use BEFORE data gathering to plan the approach, identify information needs, sequence tasks, and define success criteria.",
        prompt=_load_prompt("research_planner"),
        tools=["Read", "WebSearch"],
        model="sonnet",
    ),
    "source-verifier": AgentDefinition(
        description="Verify claims against cited sources. Cross-references assertions, flags unsupported claims, detects hallucination and stale data. Use AFTER synthesis to validate factual grounding.",
        prompt=_load_prompt("source_verifier"),
        tools=[
            f"{_S}scrape_url",
            "Read",
            "WebSearch",
        ],
        model="sonnet",
    ),
    "report-critic": AgentDefinition(
        description="Evaluate report quality across completeness, accuracy, structure, analytical depth, and actionability. Returns scored assessment with specific improvement recommendations.",
        prompt=_load_prompt("report_critic"),
        tools=["Read"],
        model="sonnet",
    ),
    "after-action-analyst": AgentDefinition(
        description="Conduct a structured after-action review after each research run. Diagnoses execution quality, speed bottlenecks, capability gaps, and recommends memory updates, new agent specs, or operating guidance for follow-on agents.",
        prompt=_load_prompt("after_action_analyst"),
        tools=["Read"],
        model="sonnet",
    ),
    "plan-validator": AgentDefinition(
        description="Monitor research execution for drift. Spot-checks subagent outputs against the plan using process control methods, detects scope/quality/source/goal drift, and recommends corrective actions.",
        prompt=_load_prompt("plan_validator"),
        tools=["Read"],
        model="sonnet",
    ),
    "design-agent": AgentDefinition(
        description="Design visual structure and layout for deliverables — presentations, dashboards, reports, infographics. Applies Calm Precision principles as flexible guidance. Recommends chart types, information hierarchy, and slide layouts.",
        prompt=_load_prompt("design_agent"),
        tools=[
            f"{_S}create_pptx",
            f"{_S}create_report",
            "Read",
            "Write",
        ],
        model="sonnet",
    ),
}
