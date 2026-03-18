"""Integration tests for Stratagem agent."""

from pathlib import Path

from stratagem.server import create_stratagem_server, get_all_allowed_tools, ALL_TOOLS, TOOL_NAMES
from stratagem.subagents.definitions import SUBAGENTS


class TestServer:
    def test_all_tools_registered(self):
        assert len(ALL_TOOLS) == 12

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
            "after-action-analyst",
            "plan-validator",
            "design-agent",
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
        for skill in ["research", "analyze-earnings", "extract-data", "flowchart"]:
            skill_file = skills_dir / skill / "SKILL.md"
            assert skill_file.exists(), f"Missing skill: {skill_file}"

    def test_agent_file_exists(self):
        agent_file = Path(__file__).parent.parent / "plugin" / "agents" / "research-orchestrator" / "AGENT.md"
        assert agent_file.exists()


class TestNavGator:
    def test_generate_architecture(self, tmp_path):
        from stratagem.navgator import generate_architecture
        arch_dir = generate_architecture(tmp_path)
        assert arch_dir.exists()
        assert (arch_dir / "index.json").exists()
        assert (arch_dir / "graph.json").exists()
        assert (arch_dir / "SUMMARY.md").exists()

    def test_component_count(self, tmp_path):
        import json
        from stratagem.navgator import generate_architecture
        arch_dir = generate_architecture(tmp_path)
        index = json.loads((arch_dir / "index.json").read_text())
        # 13 agents + 12 tools = 25 components
        assert index["stats"]["total_components"] == 25
        assert index["stats"]["components_by_type"]["agent"] == 13
        assert index["stats"]["components_by_type"]["service"] == 12

    def test_connection_count(self, tmp_path):
        import json
        from stratagem.navgator import generate_architecture
        arch_dir = generate_architecture(tmp_path)
        index = json.loads((arch_dir / "index.json").read_text())
        # 12 delegations + 3 feedback + 16 tool uses + 1 control→create_report = 32
        assert index["stats"]["total_connections"] == 32

    def test_graph_nodes_match_components(self, tmp_path):
        import json
        from stratagem.navgator import generate_architecture
        arch_dir = generate_architecture(tmp_path)
        index = json.loads((arch_dir / "index.json").read_text())
        graph = json.loads((arch_dir / "graph.json").read_text())
        assert len(graph["nodes"]) == index["stats"]["total_components"]
        assert len(graph["edges"]) == index["stats"]["total_connections"]

    def test_individual_files_written(self, tmp_path):
        from stratagem.navgator import generate_architecture
        arch_dir = generate_architecture(tmp_path)
        comp_files = list((arch_dir / "components").glob("COMP_*.json"))
        conn_files = list((arch_dir / "connections").glob("CONN_*.json"))
        assert len(comp_files) == 25
        assert len(conn_files) == 32


class TestAgentLogging:
    def test_memory_persistence_errors_are_logged(self, tmp_path):
        import json

        from stratagem.agent import _log_memory_persistence_error

        try:
            raise RuntimeError("memory aggregation failed")
        except RuntimeError as exc:
            _log_memory_persistence_error(cwd=tmp_path, thread_id="thread_123", exc=exc)

        log_path = tmp_path / ".stratagem" / "logs" / "memory_errors.log"
        assert log_path.exists()
        entry = json.loads(log_path.read_text(encoding="utf-8").strip().splitlines()[-1])
        assert entry["thread_id"] == "thread_123"
        assert "memory aggregation failed" in entry["error"]
        assert "RuntimeError" in entry["traceback"]


class TestAfterActionReview:
    async def test_after_action_review_written(self, tmp_path):
        from stratagem.agent import _generate_after_action_review

        thread_dir = tmp_path / ".stratagem" / "threads" / "thread_aar"
        thread_dir.mkdir(parents=True, exist_ok=True)
        (thread_dir / "observations.jsonl").write_text(
            '{"id":"OBS_1","category":"process","content":"Verifier caught weak sourcing"}\n',
            encoding="utf-8",
        )

        async def fake_runner(**kwargs):
            assert "Verifier caught weak sourcing" in kwargs["prompt_text"]
            return "# After Action Review\n\n## Mission\n- Test mission\n"

        path = await _generate_after_action_review(
            cwd=tmp_path,
            thread_id="thread_aar",
            topic_id="ai-chips",
            prompt="Assess GPU competition",
            result_text="Final answer",
            rationale="Used planner then synthesizer.",
            turn_count=4,
            cost_usd=1.23,
            tools_used={"Read", "WebSearch"},
            scripts_written=[],
            dynamic_agents_created={},
            input_files=None,
            model_overrides=None,
            delegation_budget={"mode": "standard"},
            agent_dispatches=[],
            orchestration_warnings=[],
            anti_patterns=[],
            handoff_artifacts={},
            runner=fake_runner,
        )

        report_path, text = path
        assert report_path.exists()
        text = report_path.read_text(encoding="utf-8")
        assert "# After Action Review" in text
        assert "Test mission" in text


class TestOrchestrationPolicy:
    def test_delegation_budget_stays_lean_for_simple_tasks(self):
        from stratagem.agent import _derive_delegation_budget

        budget = _derive_delegation_budget(
            prompt="Summarize this PDF into a short brief.",
            input_files=["/tmp/report.pdf"],
            thread_id=None,
        )

        assert budget["mode"] == "lean"
        assert budget["max_agent_dispatches"] == 3
        assert budget["max_dynamic_specialists"] == 0

    def test_delegation_budget_expands_for_complex_tasks(self):
        from stratagem.agent import _derive_delegation_budget

        budget = _derive_delegation_budget(
            prompt="Compare NVIDIA, AMD, and Intel across AI accelerators, market landscape, and financial strategy using SEC filings and multiple documents.",
            input_files=["/tmp/a.pdf", "/tmp/b.xlsx"],
            thread_id="thread_123",
        )

        assert budget["mode"] == "deep"
        assert budget["max_agent_dispatches"] == 7
        assert budget["max_validation_passes"] == 2
        assert budget["finance_bias"] is True


class TestMemoryCompression:
    async def test_memory_compression_writes_detail_file(self, tmp_path):
        import json

        from stratagem.agent import _compress_memory_store

        async def fake_runner(**kwargs):
            assert "Memory store: Topic ai-chips" in kwargs["prompt_text"]
            return "### Topic Summary\n- Compressed memory summary."

        mem_path = tmp_path / ".stratagem" / "topics" / "ai-chips" / "memory.json"
        detail_path = await _compress_memory_store(
            cwd=tmp_path,
            label="Topic ai-chips",
            path=mem_path,
            data={
                "sources": [{"content": "SEC EDGAR is reliable", "confidence": 0.9}],
                "findings": [{"content": "NVIDIA leads training GPUs", "confidence": 0.9}],
                "process": [{"content": "Use verifier before critic", "confidence": 0.8}],
                "run_count": 4,
                "last_run": "2026-03-14T10:00:00",
            },
            model="sonnet",
            runner=fake_runner,
        )

        assert detail_path is not None
        assert detail_path.exists()
        compact = json.loads(mem_path.read_text(encoding="utf-8"))
        assert compact["compressed"] is True
        assert "Compressed memory summary" in compact["compressed_summary"]
