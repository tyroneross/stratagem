"""Minimal test harness for Stratagem.

Replaces pytest with ~120 lines. Supports:
- Test discovery: test_*.py files, Test* classes, test_* methods/functions
- Async tests: auto-detected, run with asyncio.run()
- Fixtures: tmp_path and tmp_dir (tempdir, passed as arg, cleaned up after)
- Markers: @mark("network") with --skip-network flag
- Color output: green pass, red fail, yellow skip
- CLI: uv run python -m stratagem.testing [--skip-network] [-k pattern]
"""

import asyncio
import importlib
import importlib.util
import inspect
import shutil
import sys
import tempfile
import traceback
from pathlib import Path


# ── Markers ──────────────────────────────────────────────────

_MARKER_ATTR = "_test_markers"


def mark(name: str):
    """Decorator to tag a test with a marker name."""
    def decorator(fn):
        markers = getattr(fn, _MARKER_ATTR, set())
        markers.add(name)
        setattr(fn, _MARKER_ATTR, markers)
        return fn
    return decorator


def get_markers(fn) -> set[str]:
    return getattr(fn, _MARKER_ATTR, set())


# ── Colors ───────────────────────────────────────────────────

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

_use_color = sys.stdout.isatty()


def _c(color: str, text: str) -> str:
    return f"{color}{text}{RESET}" if _use_color else text


# ── Fixture injection ────────────────────────────────────────

def _make_tmp_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="stratagem_test_"))


def _inject_fixtures(fn) -> tuple[list, list[Path]]:
    """Inspect function signature and build args. Returns (args, tmp_dirs_to_cleanup)."""
    sig = inspect.signature(fn)
    args = []
    tmp_dirs = []
    for name in sig.parameters:
        if name == "self":
            continue
        if name in ("tmp_path", "tmp_dir"):
            d = _make_tmp_dir()
            tmp_dirs.append(d)
            args.append(d)
    return args, tmp_dirs


# ── Test discovery ───────────────────────────────────────────

def _discover_tests(test_dir: Path, pattern: str | None = None) -> list[tuple[str, callable]]:
    """Find all test functions. Returns [(qualified_name, fn)]."""
    tests = []
    for filepath in sorted(test_dir.glob("test_*.py")):
        module_name = filepath.stem
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            print(_c(RED, f"  IMPORT ERROR {filepath.name}: {e}"))
            continue

        # Collect from Test* classes
        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if isinstance(obj, type) and attr_name.startswith("Test"):
                instance = None
                for method_name in sorted(dir(obj)):
                    if not method_name.startswith("test_"):
                        continue
                    method = getattr(obj, method_name)
                    if not callable(method):
                        continue
                    qname = f"{module_name}::{attr_name}::{method_name}"
                    if pattern and pattern.lower() not in qname.lower():
                        continue
                    if instance is None:
                        instance = obj()
                    bound = getattr(instance, method_name)
                    tests.append((qname, bound))

            # Top-level test_ functions
            elif callable(obj) and attr_name.startswith("test_"):
                qname = f"{module_name}::{attr_name}"
                if pattern and pattern.lower() not in qname.lower():
                    continue
                tests.append((qname, obj))

    return tests


# ── Test runner ──────────────────────────────────────────────

async def _run_test(name: str, fn: callable) -> str:
    """Run a single test. Returns 'pass', 'fail', or 'skip'."""
    args, tmp_dirs = _inject_fixtures(fn)
    try:
        if asyncio.iscoroutinefunction(fn):
            await fn(*args)
        else:
            fn(*args)
        return "pass"
    except Exception:
        traceback.print_exc()
        return "fail"
    finally:
        for d in tmp_dirs:
            shutil.rmtree(d, ignore_errors=True)


def run_tests(
    test_dir: Path,
    skip_markers: set[str] | None = None,
    pattern: str | None = None,
) -> tuple[int, int, int]:
    """Run all tests. Returns (passed, failed, skipped)."""
    skip_markers = skip_markers or set()
    tests = _discover_tests(test_dir, pattern)

    if not tests:
        print(_c(YELLOW, "No tests found."))
        return 0, 0, 0

    print(f"\n{_c(BOLD, f'Collected {len(tests)} tests')}\n")

    passed = failed = skipped = 0

    for name, fn in tests:
        markers = get_markers(fn)
        if markers & skip_markers:
            print(f"  {_c(YELLOW, 'SKIP')} {_c(DIM, name)}")
            skipped += 1
            continue

        print(f"  {_c(DIM, 'RUN')}  {name}", end="", flush=True)
        result = asyncio.run(_run_test(name, fn))

        # Overwrite the line
        if result == "pass":
            print(f"\r  {_c(GREEN, 'PASS')} {name}")
            passed += 1
        else:
            print(f"\r  {_c(RED, 'FAIL')} {name}")
            failed += 1

    # Summary
    print()
    parts = []
    if passed:
        parts.append(_c(GREEN, f"{passed} passed"))
    if failed:
        parts.append(_c(RED, f"{failed} failed"))
    if skipped:
        parts.append(_c(YELLOW, f"{skipped} skipped"))
    print(f"  {', '.join(parts)} in {len(tests)} tests\n")

    return passed, failed, skipped


# ── CLI entry point ──────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Stratagem test runner")
    parser.add_argument("--skip-network", action="store_true", help="Skip tests marked @mark('network')")
    parser.add_argument("-k", "--filter", dest="pattern", help="Only run tests matching pattern")
    parser.add_argument("path", nargs="?", default="tests", help="Test directory (default: tests)")
    args = parser.parse_args()

    skip = set()
    if args.skip_network:
        skip.add("network")

    test_dir = Path(args.path)
    if not test_dir.is_dir():
        print(_c(RED, f"Test directory not found: {test_dir}"))
        sys.exit(1)

    # Ensure project is importable
    src = Path("src")
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))

    _, failed, _ = run_tests(test_dir, skip_markers=skip, pattern=args.pattern)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
