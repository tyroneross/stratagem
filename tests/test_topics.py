"""Tests for topic registry."""

from pathlib import Path
from stratagem.topics import create_topic, get_topic, list_topics


class TestTopicRegistry:
    def test_create_topic(self, tmp_path):
        topic = create_topic("ai-chips", title="AI Chip Landscape", cwd=tmp_path)
        assert topic["id"] == "ai-chips"
        assert topic["title"] == "AI Chip Landscape"
        assert topic["thread_ids"] == []
        assert topic["tags"] == []

    def test_get_topic(self, tmp_path):
        create_topic("ai-chips", title="AI Chip Landscape", cwd=tmp_path)
        topic = get_topic("ai-chips", cwd=tmp_path)
        assert topic is not None
        assert topic["id"] == "ai-chips"

    def test_get_nonexistent_topic(self, tmp_path):
        topic = get_topic("nope", cwd=tmp_path)
        assert topic is None

    def test_list_topics(self, tmp_path):
        create_topic("ai-chips", title="AI Chips", cwd=tmp_path)
        create_topic("gpu-market", title="GPU Market", cwd=tmp_path)
        topics = list_topics(cwd=tmp_path)
        assert len(topics) == 2
        ids = [t["id"] for t in topics]
        assert "ai-chips" in ids
        assert "gpu-market" in ids

    def test_link_thread(self, tmp_path):
        from stratagem.topics import link_thread
        create_topic("ai-chips", title="AI Chips", cwd=tmp_path)
        link_thread("ai-chips", "web_123", cwd=tmp_path)
        topic = get_topic("ai-chips", cwd=tmp_path)
        assert "web_123" in topic["thread_ids"]

    def test_link_thread_dedup(self, tmp_path):
        from stratagem.topics import link_thread
        create_topic("ai-chips", title="AI Chips", cwd=tmp_path)
        link_thread("ai-chips", "web_123", cwd=tmp_path)
        link_thread("ai-chips", "web_123", cwd=tmp_path)  # duplicate
        topic = get_topic("ai-chips", cwd=tmp_path)
        assert topic["thread_ids"].count("web_123") == 1

    def test_invalid_topic_id(self, tmp_path):
        import traceback
        try:
            create_topic("../escape", title="Bad", cwd=tmp_path)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
