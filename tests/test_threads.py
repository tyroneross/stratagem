"""Tests for thread context system."""

import json

from stratagem.threads import (
    create_thread,
    load_context,
    append_entry,
    rebuild_context,
    list_threads,
    get_thread,
)


class TestThreads:
    def test_create_thread(self, tmp_path):
        tdir = create_thread("t1", tmp_path)
        assert tdir.exists()

        # Index should have entry
        index = json.loads((tmp_path / ".stratagem" / "threads" / "index.json").read_text())
        assert len(index) == 1
        assert index[0]["id"] == "t1"

    def test_create_thread_idempotent(self, tmp_path):
        create_thread("t1", tmp_path)
        create_thread("t1", tmp_path)

        index = json.loads((tmp_path / ".stratagem" / "threads" / "index.json").read_text())
        assert len(index) == 1

    def test_load_context_empty(self, tmp_path):
        create_thread("t1", tmp_path)
        assert load_context("t1", tmp_path) is None

    def test_append_and_load_context(self, tmp_path):
        create_thread("t1", tmp_path)
        append_entry("t1", tmp_path, query="What is AAPL?", summary="Apple Inc trades at $150.")
        ctx = load_context("t1", tmp_path)
        assert ctx is not None
        assert "AAPL" in ctx
        assert "Apple" in ctx

    def test_append_updates_index(self, tmp_path):
        create_thread("t1", tmp_path)
        append_entry("t1", tmp_path, query="Q1", summary="S1")
        append_entry("t1", tmp_path, query="Q2", summary="S2")

        index = json.loads((tmp_path / ".stratagem" / "threads" / "index.json").read_text())
        assert index[0]["query_count"] == 2

    def test_rebuild_context_caps_lines(self, tmp_path):
        create_thread("t1", tmp_path)
        # Add many entries to test capping
        for i in range(10):
            append_entry("t1", tmp_path, query=f"Question {i}", summary=f"Answer {i} with details.")

        ctx = load_context("t1", tmp_path)
        assert ctx is not None
        lines = ctx.strip().split("\n")
        assert len(lines) <= 30

    def test_list_threads(self, tmp_path):
        create_thread("t1", tmp_path, title="First thread")
        create_thread("t2", tmp_path, title="Second thread")

        threads = list_threads(tmp_path)
        assert len(threads) == 2
        ids = {t["id"] for t in threads}
        assert ids == {"t1", "t2"}

    def test_get_thread(self, tmp_path):
        create_thread("t1", tmp_path)
        append_entry("t1", tmp_path, query="Q", summary="S")

        t = get_thread("t1", tmp_path)
        assert t is not None
        assert t["id"] == "t1"
        assert t["message_count"] == 1
        assert t["has_context"] is True

    def test_get_thread_missing(self, tmp_path):
        assert get_thread("nonexistent", tmp_path) is None

    def test_append_creates_thread_in_index(self, tmp_path):
        # Append without creating first — should auto-add to index
        (tmp_path / ".stratagem" / "threads").mkdir(parents=True)
        append_entry("auto", tmp_path, query="Q", summary="S")
        threads = list_threads(tmp_path)
        assert any(t["id"] == "auto" for t in threads)
