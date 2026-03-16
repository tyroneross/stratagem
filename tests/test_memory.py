"""Tests for memory loading, scaffold generation, and post-run aggregation."""

import json
from pathlib import Path

from stratagem.topics import create_topic


class TestScaffoldGeneration:
    def test_empty_scaffold(self, tmp_path):
        from stratagem.memory import build_scaffold
        scaffold = build_scaffold(topic_id=None, cwd=tmp_path)
        assert scaffold == ""  # No topic, no memory

    def test_scaffold_with_topic_memory(self, tmp_path):
        from stratagem.memory import build_scaffold

        # Set up topic with memory
        create_topic("ai-chips", title="AI Chip Landscape", cwd=tmp_path)
        mem_path = tmp_path / ".stratagem" / "topics" / "ai-chips" / "memory.json"
        mem_path.parent.mkdir(parents=True, exist_ok=True)
        mem_path.write_text(json.dumps({
            "sources": [
                {"content": "reuters.com requires subscription", "confidence": 0.8, "tags": ["reuters"]},
                {"content": "SEC EDGAR is reliable", "confidence": 0.95, "tags": ["sec"]},
            ],
            "findings": [
                {"content": "NVIDIA leads GPU market at 80%", "confidence": 0.9, "tags": ["nvidia"]},
            ],
            "process": [
                {"content": "WebSearch fallback works for paywalled sites", "confidence": 0.7, "tags": []},
            ],
            "run_count": 3,
            "last_run": "2026-03-14T10:00:00",
        }))

        scaffold = build_scaffold(topic_id="ai-chips", cwd=tmp_path)
        assert "AI Chip Landscape" in scaffold
        assert "Sources: 2" in scaffold
        assert "Findings: 1" in scaffold
        assert ".stratagem/topics/ai-chips/memory.json" in scaffold

    def test_scaffold_includes_common_memory(self, tmp_path):
        from stratagem.memory import build_scaffold

        common_path = tmp_path / ".stratagem" / "memory.json"
        common_path.parent.mkdir(parents=True, exist_ok=True)
        common_path.write_text(json.dumps({
            "process": [
                {"content": "Always verify SEC data against 10-K", "confidence": 0.9},
            ],
        }))

        scaffold = build_scaffold(topic_id=None, cwd=tmp_path)
        assert "Common Memory" in scaffold
        assert "Process learnings: 1" in scaffold


class TestAggregation:
    def test_aggregate_observations_to_topic(self, tmp_path):
        from stratagem.memory import aggregate_observations

        # Set up topic
        create_topic("ai-chips", title="AI Chips", cwd=tmp_path)

        # Write thread observations
        thread_dir = tmp_path / ".stratagem" / "threads" / "web_123"
        thread_dir.mkdir(parents=True, exist_ok=True)
        obs_path = thread_dir / "observations.jsonl"
        obs_path.write_text(
            json.dumps({"id": "OBS_1", "agent": "data-extractor", "category": "source",
                         "content": "reuters.com paywall", "confidence": 0.8,
                         "tags": ["reuters"], "scope": "thread", "related_to": None}) + "\n"
            + json.dumps({"id": "OBS_2", "agent": "synthesizer", "category": "finding",
                          "content": "NVIDIA 80% GPU share", "confidence": 0.9,
                          "tags": ["nvidia"], "scope": "thread", "related_to": None}) + "\n"
        )

        aggregate_observations(
            thread_id="web_123",
            topic_id="ai-chips",
            cwd=tmp_path,
        )

        # Check topic memory updated
        mem_path = tmp_path / ".stratagem" / "topics" / "ai-chips" / "memory.json"
        assert mem_path.exists()
        mem = json.loads(mem_path.read_text())
        assert len(mem["sources"]) == 1
        assert len(mem["findings"]) == 1
        assert mem["run_count"] == 1

    def test_aggregate_dedup(self, tmp_path):
        from stratagem.memory import aggregate_observations

        create_topic("ai-chips", title="AI Chips", cwd=tmp_path)

        # Pre-populate topic memory with existing observation
        mem_path = tmp_path / ".stratagem" / "topics" / "ai-chips" / "memory.json"
        mem_path.parent.mkdir(parents=True, exist_ok=True)
        mem_path.write_text(json.dumps({
            "sources": [{"content": "reuters.com paywall", "confidence": 0.7, "tags": ["reuters"]}],
            "findings": [],
            "process": [],
            "run_count": 1,
            "last_run": "2026-03-14T10:00:00",
        }))

        # New observation with same content but higher confidence
        thread_dir = tmp_path / ".stratagem" / "threads" / "web_456"
        thread_dir.mkdir(parents=True, exist_ok=True)
        obs_path = thread_dir / "observations.jsonl"
        obs_path.write_text(json.dumps({
            "id": "OBS_3", "agent": "verifier", "category": "source",
            "content": "reuters.com paywall", "confidence": 0.9,
            "tags": ["reuters"], "scope": "thread", "related_to": "OBS_1",
        }) + "\n")

        aggregate_observations(thread_id="web_456", topic_id="ai-chips", cwd=tmp_path)

        mem = json.loads(mem_path.read_text())
        # Should still be 1 source, but confidence updated to higher value
        assert len(mem["sources"]) == 1
        assert mem["sources"][0]["confidence"] == 0.9

    def test_aggregate_common_scope(self, tmp_path):
        from stratagem.memory import aggregate_observations

        create_topic("ai-chips", title="AI Chips", cwd=tmp_path)

        thread_dir = tmp_path / ".stratagem" / "threads" / "web_789"
        thread_dir.mkdir(parents=True, exist_ok=True)
        obs_path = thread_dir / "observations.jsonl"
        obs_path.write_text(json.dumps({
            "id": "OBS_4", "agent": "planner", "category": "process",
            "content": "Always verify SEC filings against 10-K",
            "confidence": 0.9, "tags": [], "scope": "common", "related_to": None,
        }) + "\n")

        aggregate_observations(thread_id="web_789", topic_id="ai-chips", cwd=tmp_path)

        common = json.loads((tmp_path / ".stratagem" / "memory.json").read_text())
        assert len(common["process"]) == 1
