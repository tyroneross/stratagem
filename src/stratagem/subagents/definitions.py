"""Subagent definitions — AgentDefinition configs for all specialist agents."""

from pathlib import Path

from claude_agent_sdk import AgentDefinition

PROMPTS_DIR = Path(__file__).parent / "prompts"
REFERENCES_DIR = Path(__file__).parent / "references"


def _load_prompt(name: str, references: list[str] | None = None) -> str:
    """Load a system prompt, optionally appending reference guides."""
    prompt = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    if references:
        for ref_name in references:
            ref_path = REFERENCES_DIR / f"{ref_name}.md"
            if ref_path.exists():
                prompt += f"\n\n---\n\n{ref_path.read_text(encoding='utf-8')}"
    return prompt


# MCP tool names (namespaced under stratagem server)
_S = "mcp__stratagem__"

SUBAGENTS: dict[str, AgentDefinition] = {
    "data-extractor": AgentDefinition(
        description="Extract and verify data from PDFs, websites, spreadsheets, and presentations. Use for structured data extraction tasks.",
        prompt=_load_prompt("data_extractor", ["pdf_processing", "xlsx_processing", "pptx_processing"]),
        tools=[
            f"{_S}parse_pdf",
            f"{_S}scrape_url",
            f"{_S}read_spreadsheet",
            f"{_S}read_pptx",
            f"{_S}read_docx",
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
        model="sonnet",  # Synthesizes from pre-extracted data; strong prompt compensates
    ),
    "executive-synthesizer": AgentDefinition(
        description="Create executive-ready research briefs with strategic framing, actionable conclusions, and confidence assessments.",
        prompt=_load_prompt("executive_synthesizer", ["docx_processing"]),
        tools=[
            "Read",
            "Write",
        ],
        model="sonnet",  # I3/O1: reformats synthesis output; strong prompt compensates
    ),
    "financial-analyst": AgentDefinition(
        description="Analyze SEC filings, earnings reports, and financial statements. Extracts metrics, identifies trends, and produces financial analysis.",
        prompt=_load_prompt("financial_analyst", ["pdf_processing", "xlsx_processing"]),
        tools=[
            f"{_S}search_sec_filings",
            f"{_S}download_sec_filing",
            f"{_S}read_spreadsheet",
            f"{_S}parse_pdf",
            f"{_S}read_docx",
            f"{_S}create_spreadsheet",
            "Read",
            "Write",
            "Bash",  # C2: needed for Python script execution (Calculation Policy)
        ],
        model="sonnet",  # Analysis + Bash calculations; strong prompt compensates
    ),
    "flowchart-architect": AgentDefinition(
        description="Design process architectures and create flowchart visualizations as PowerPoint presentations.",
        prompt=_load_prompt("flowchart_architect", ["pptx_creation"]),
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
        prompt=_load_prompt("design_agent", ["pptx_processing", "docx_processing"]),
        tools=[
            f"{_S}create_pptx",
            f"{_S}create_report",
            "Read",
            "Write",
        ],
        model="sonnet",
    ),
}
