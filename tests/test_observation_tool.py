"""Tests for record_observation MCP tool."""

import asyncio
import json
from pathlib import Path


class TestRecordObservation:
    def test_basic_observation(self, tmp_path):
        from stratagem.tools.memory import _write_observation

        obs_path = tmp_path / "observations.jsonl"
        result = _write_observation(
            obs_path=obs_path,
            agent="data-extractor",
            category="source",
            content="reuters.com requires subscription",
            confidence=0.8,
            tags=["reuters", "paywall"],
            scope="thread",
            related_to=None,
        )
        assert result["ok"] is True
        assert result["id"].startswith("OBS_")

        # Verify file written
        lines = obs_path.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["agent"] == "data-extractor"
        assert entry["category"] == "source"
        assert entry["content"] == "reuters.com requires subscription"
        assert entry["confidence"] == 0.8

    def test_empty_content_rejected(self, tmp_path):
        from stratagem.tools.memory import _write_observation

        obs_path = tmp_path / "observations.jsonl"
        result = _write_observation(
            obs_path=obs_path,
            agent="test",
            category="source",
            content="",
            confidence=0.5,
            tags=[],
            scope="thread",
            related_to=None,
        )
        assert "error" in result

    def test_confidence_clamped(self, tmp_path):
        from stratagem.tools.memory import _write_observation

        obs_path = tmp_path / "observations.jsonl"
        result = _write_observation(
            obs_path=obs_path,
            agent="test",
            category="finding",
            content="Some finding",
            confidence=1.5,
            tags=[],
            scope="thread",
            related_to=None,
        )
        assert result["ok"] is True
        entry = json.loads(obs_path.read_text().strip())
        assert entry["confidence"] == 1.0

    def test_duplicate_skipped(self, tmp_path):
        from stratagem.tools.memory import _write_observation

        obs_path = tmp_path / "observations.jsonl"
        r1 = _write_observation(
            obs_path=obs_path,
            agent="test",
            category="source",
            content="reuters.com paywall",
            confidence=0.8,
            tags=[],
            scope="thread",
            related_to=None,
        )
        r2 = _write_observation(
            obs_path=obs_path,
            agent="test",
            category="source",
            content="reuters.com paywall",
            confidence=0.9,
            tags=[],
            scope="thread",
            related_to=None,
        )
        assert r2["ok"] is True
        assert r2["id"] == r1["id"]  # Returns existing ID
        lines = obs_path.read_text().strip().splitlines()
        assert len(lines) == 1  # No duplicate
