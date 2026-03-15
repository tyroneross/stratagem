"""Artifact manifest management — centralize all output with tracking.

All reports, spreadsheets, presentations, and other outputs are registered
in stratagem/artifacts/manifest.json for discovery and thread association.

Storage: stratagem/artifacts/
  manifest.json    # [{id, path, format, title, thread_id, created, size_bytes}]
"""

import fcntl
import hashlib
import json
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


def _artifacts_dir(cwd: Path) -> Path:
    return cwd / ".stratagem" / "artifacts"


def get_manifest_path(cwd: Path) -> Path:
    """Return the path to manifest.json."""
    return _artifacts_dir(cwd) / "manifest.json"


@contextmanager
def _lock_manifest(cwd: Path):
    """Acquire an exclusive file lock for atomic read-modify-write."""
    lock_path = _artifacts_dir(cwd) / ".manifest.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    f = open(lock_path, "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()


def _read_manifest(cwd: Path) -> list[dict]:
    path = get_manifest_path(cwd)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _write_manifest(cwd: Path, entries: list[dict]) -> None:
    path = get_manifest_path(cwd)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def _make_artifact_id() -> str:
    """Generate artifact ID: art_{timestamp}_{4char_hash}."""
    ts = str(time.time())
    h = hashlib.sha256(ts.encode()).hexdigest()[:4]
    return f"art_{int(time.time())}_{h}"


# ── Public API ──


def register(
    path: str | Path,
    format: str,
    title: str,
    cwd: Path,
    thread_id: str | None = None,
) -> dict:
    """Register an artifact in the manifest.

    Args:
        path: File path of the artifact
        format: File format (markdown, pptx, html, docx, xlsx)
        title: Human-readable title
        cwd: Working directory
        thread_id: Optional thread association

    Returns:
        The created manifest entry.
    """
    artifact_path = Path(path)
    try:
        size_bytes = artifact_path.stat().st_size if artifact_path.exists() else 0
    except OSError:
        size_bytes = 0

    entry = {
        "id": _make_artifact_id(),
        "path": str(path),
        "format": format,
        "title": title,
        "thread_id": thread_id,
        "created": datetime.now().isoformat(),
        "size_bytes": size_bytes,
    }

    with _lock_manifest(cwd):
        manifest = _read_manifest(cwd)
        manifest.append(entry)
        _write_manifest(cwd, manifest)

    return entry


def list_artifacts(cwd: Path, thread_id: str | None = None) -> list[dict]:
    """List artifacts from manifest, optionally filtered by thread.

    Args:
        cwd: Working directory
        thread_id: If provided, only return artifacts for this thread

    Returns:
        List of manifest entries.
    """
    manifest = _read_manifest(cwd)
    if thread_id is not None:
        return [e for e in manifest if e.get("thread_id") == thread_id]
    return manifest
