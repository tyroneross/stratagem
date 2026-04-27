"""DoE-style checks for Stratagem query routing policy."""

import pytest

from stratagem.agent import _derive_delegation_budget, _format_delegation_budget


ROUTING_CASES = [
    (
        "simple_finance_lookup",
        "What was Arista's Q1 2025 revenue?",
        None,
        None,
        {"mode": "lean", "finance_bias": True, "produces_artifact": False},
    ),
    (
        "finance_calculation",
        "Calculate NVIDIA revenue CAGR and margin trend from the last three fiscal years.",
        None,
        None,
        {"finance_bias": True, "calculation_bias": True, "planner_mode": {"recommended", "required"}},
    ),
    (
        "current_market_news",
        "What changed in OpenAI model pricing this week?",
        None,
        None,
        {"web_bias": True, "mode": {"standard", "deep"}},
    ),
    (
        "market_sizing",
        "Size the US GLP-1 market and identify key competitors, sources, and uncertainties.",
        None,
        None,
        {"mode": {"standard", "deep"}, "web_bias": True, "calculation_bias": True},
    ),
    (
        "single_document_extraction",
        "Extract the key risks from this PDF and summarize them in a table.",
        ["/tmp/example.pdf"],
        None,
        {"document_bias": True, "mode": {"standard", "deep"}},
    ),
    (
        "artifact_deck",
        "Draft a short powerpoint on a competitive analysis of Arista and Juniper.",
        None,
        None,
        {"produces_artifact": True, "force_report_critic": True, "planner_mode": "required"},
    ),
    (
        "dashboard_artifact",
        "Create a dashboard with charts showing onboarding funnel conversion and recommendations.",
        None,
        None,
        {"produces_artifact": True, "force_report_critic": True, "calculation_bias": True},
    ),
    (
        "vague_clarification",
        "Help me think through this idea.",
        None,
        None,
        {"mode": "lean", "needs_clarification": True, "produces_artifact": False},
    ),
    (
        "briefly_false_artifact",
        "Briefly explain why switching costs matter in B2B SaaS.",
        None,
        None,
        {"produces_artifact": False, "force_report_critic": False},
    ),
    (
        "complex_multi_company",
        "Compare NVIDIA, AMD, and Intel across AI accelerators, market landscape, and financial strategy using SEC filings and multiple documents.",
        ["/tmp/a.pdf", "/tmp/b.xlsx"],
        "thread_123",
        {"mode": "deep", "finance_bias": True, "document_bias": True, "web_bias": True},
    ),
]


def _matches(actual, expected):
    if isinstance(expected, set):
        return actual in expected
    return actual == expected


@pytest.mark.parametrize("name,prompt,input_files,thread_id,expected", ROUTING_CASES)
def test_query_routing_doe_cases(name, prompt, input_files, thread_id, expected):
    budget = _derive_delegation_budget(prompt=prompt, input_files=input_files, thread_id=thread_id)

    for key, expected_value in expected.items():
        assert _matches(budget.get(key), expected_value), f"{name}:{key}"

    if any(
        budget.get(key)
        for key in ("finance_bias", "document_bias", "web_bias", "calculation_bias", "needs_clarification")
    ):
        assert "Routing hints:" in _format_delegation_budget(budget)


def test_routing_hints_preserve_operating_keywords():
    budget = _derive_delegation_budget(
        prompt="Create a dashboard with charts showing current revenue CAGR from SEC filings.",
        input_files=["/tmp/revenue.xlsx"],
        thread_id=None,
    )

    formatted = _format_delegation_budget(budget).lower()
    for keyword in (
        "financial-analyst",
        "data-extractor",
        "websearch",
        "freshness",
        "python",
        "report-critic",
        "verify",
    ):
        assert keyword in formatted
