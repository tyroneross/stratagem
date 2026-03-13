"""Tests for artifact manifest system."""

import json

from stratagem.artifacts import register, list_artifacts, get_manifest_path


class TestArtifacts:
    def test_register_artifact(self, tmp_path):
        # Create a dummy file
        f = tmp_path / "report.md"
        f.write_text("# Test Report")

        entry = register(
            path=str(f),
            format="markdown",
            title="Test Report",
            cwd=tmp_path,
        )

        assert entry["id"].startswith("art_")
        assert entry["format"] == "markdown"
        assert entry["title"] == "Test Report"
        assert entry["size_bytes"] > 0

    def test_list_artifacts(self, tmp_path):
        f1 = tmp_path / "a.md"
        f1.write_text("A")
        f2 = tmp_path / "b.xlsx"
        f2.write_text("B")

        register(path=str(f1), format="markdown", title="A", cwd=tmp_path)
        register(path=str(f2), format="xlsx", title="B", cwd=tmp_path)

        arts = list_artifacts(tmp_path)
        assert len(arts) == 2

    def test_list_by_thread(self, tmp_path):
        f1 = tmp_path / "a.md"
        f1.write_text("A")
        f2 = tmp_path / "b.md"
        f2.write_text("B")

        register(path=str(f1), format="markdown", title="A", cwd=tmp_path, thread_id="t1")
        register(path=str(f2), format="markdown", title="B", cwd=tmp_path, thread_id="t2")

        t1_arts = list_artifacts(tmp_path, thread_id="t1")
        assert len(t1_arts) == 1
        assert t1_arts[0]["title"] == "A"

    def test_manifest_file_created(self, tmp_path):
        f = tmp_path / "test.html"
        f.write_text("<html></html>")

        register(path=str(f), format="html", title="Test", cwd=tmp_path)

        manifest_path = get_manifest_path(tmp_path)
        assert manifest_path.exists()

        data = json.loads(manifest_path.read_text())
        assert len(data) == 1

    def test_register_with_thread(self, tmp_path):
        f = tmp_path / "out.docx"
        f.write_text("doc")

        entry = register(
            path=str(f),
            format="docx",
            title="My Doc",
            cwd=tmp_path,
            thread_id="thread_123",
        )
        assert entry["thread_id"] == "thread_123"
