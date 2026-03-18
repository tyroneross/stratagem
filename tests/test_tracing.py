"""Tests for optional LangSmith tracing helpers."""


class TestTracingHelpers:
    def test_tracing_disabled_by_default(self, monkeypatch):
        from stratagem.tracing import tracing_enabled

        monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
        assert tracing_enabled() is False

    def test_tracing_enabled_from_env(self, monkeypatch):
        from stratagem.tracing import tracing_enabled, project_name

        monkeypatch.setenv("LANGSMITH_TRACING", "true")
        monkeypatch.setenv("LANGSMITH_PROJECT", "stratagem-dev")

        assert tracing_enabled() is True
        assert project_name() == "stratagem-dev"
