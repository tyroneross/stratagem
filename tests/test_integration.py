"""Integration tests for Stratagem agent."""

import pytest
from pathlib import Path

from stratagem.server import create_stratagem_server, get_all_allowed_tools, ALL_TOOLS, TOOL_NAMES
from stratagem.subagents.definitions import SUBAGENTS


class TestServer:
    def test_all_tools_registered(self):
        assert len(ALL_TOOLS) == 9

    def test_tool_names(self):
        for name in TOOL_NAMES:
            assert name.startswith("mcp__stratagem__")

    def test_create_server(self):
        server = create_stratagem_server()
        assert server is not None

    def test_allowed_tools_includes_builtins(self):
        tools = get_all_allowed_tools()
        assert "Read" in tools
        assert "Write" in tools
        assert "Agent" in tools


class TestSubagents:
    def test_all_subagents_defined(self):
        expected = [
            "data-extractor",
            "research-synthesizer",
            "executive-synthesizer",
            "financial-analyst",
            "flowchart-architect",
            "prompt-optimizer",
            "research-planner",
            "source-verifier",
            "report-critic",
            "plan-validator",
        ]
        for name in expected:
            assert name in SUBAGENTS, f"Missing subagent: {name}"

    def test_subagent_prompts_loaded(self):
        for name, agent in SUBAGENTS.items():
            assert agent.prompt, f"Empty prompt for {name}"
            assert len(agent.prompt) > 50, f"Prompt too short for {name}"

    def test_subagent_descriptions(self):
        for name, agent in SUBAGENTS.items():
            assert agent.description, f"Empty description for {name}"

    def test_data_extractor_has_tools(self):
        agent = SUBAGENTS["data-extractor"]
        assert agent.tools is not None
        assert len(agent.tools) > 0
        assert any("parse_pdf" in t for t in agent.tools)

    def test_financial_analyst_has_sec_tools(self):
        agent = SUBAGENTS["financial-analyst"]
        assert agent.tools is not None
        assert any("search_sec_filings" in t for t in agent.tools)
        assert any("download_sec_filing" in t for t in agent.tools)


class TestPluginStructure:
    def test_plugin_json_exists(self):
        plugin_json = Path(__file__).parent.parent / "plugin" / "plugin.json"
        assert plugin_json.exists()

    def test_skill_files_exist(self):
        skills_dir = Path(__file__).parent.parent / "plugin" / "skills"
        for skill in ["research", "analyze-earnings", "extract-data", "financial-model"]:
            skill_file = skills_dir / skill / "SKILL.md"
            assert skill_file.exists(), f"Missing skill: {skill_file}"

    def test_agent_file_exists(self):
        agent_file = Path(__file__).parent.parent / "plugin" / "agents" / "research-orchestrator" / "AGENT.md"
        assert agent_file.exists()
