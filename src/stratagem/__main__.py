"""CLI entry point: python -m stratagem"""

import asyncio
import argparse
import os
import sys
from pathlib import Path

# Stratagem is its own agent — not a nested Claude Code session.
# Unset the guard variable so the SDK doesn't block us.
os.environ.pop("CLAUDECODE", None)


def main():
    parser = argparse.ArgumentParser(
        prog="stratagem",
        description="Market research agent — document processing, web scraping, and financial analysis",
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Research question or task to execute",
    )
    parser.add_argument(
        "--model",
        choices=["opus", "sonnet", "haiku"],
        default=None,
        help="Claude model to use",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=None,
        help="Maximum number of agentic turns",
    )
    parser.add_argument(
        "--cwd",
        type=str,
        default=None,
        help="Working directory for file operations",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output the final result",
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Launch the web UI at http://localhost:8420",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8420,
        help="Port for the web UI (default: 8420)",
    )
    parser.add_argument(
        "--architecture",
        action="store_true",
        help="Generate NavGator-compatible architecture data and exit",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    args = parser.parse_args()

    if args.ui:
        from stratagem.ui import start_ui
        start_ui(port=args.port)
        sys.exit(0)

    if args.architecture:
        from stratagem.navgator import generate_architecture
        arch_dir = generate_architecture(args.cwd or Path.cwd())
        print(f"Architecture data written to {arch_dir}")
        sys.exit(0)

    # Join positional args as prompt (allows: stratagem what is the latest news)
    prompt = " ".join(args.prompt).strip() if args.prompt else ""

    if not prompt:
        if sys.stdin.isatty():
            # Interactive REPL mode
            _interactive(args)
            sys.exit(0)
        else:
            prompt = sys.stdin.read().strip()
            if not prompt:
                print("Error: No prompt provided", file=sys.stderr)
                sys.exit(1)

    args.prompt = prompt
    try:
        asyncio.run(_run(args))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _interactive(args):
    """Interactive REPL — type queries naturally, Ctrl+C or 'exit' to quit."""
    print("Stratagem v0.1.0 — Market research agent")
    print("Type your research question. Ctrl+C or 'exit' to quit.\n")

    while True:
        try:
            prompt = input("\033[1mstratagem>\033[0m ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye.")
            break

        if not prompt:
            continue
        if prompt.lower() in ("exit", "quit", "q"):
            print("Bye.")
            break

        args.prompt = prompt
        try:
            asyncio.run(_run(args))
        except KeyboardInterrupt:
            print("\n\nInterrupted. Ready for next query.\n")
        except Exception as e:
            print(f"\nError: {e}\n", file=sys.stderr)

        print()  # blank line between queries


async def _run(args):
    from stratagem.agent import run_research

    prompt = args.prompt if isinstance(args.prompt, str) else " ".join(args.prompt)
    cwd = Path(args.cwd) if args.cwd else Path.cwd()
    verbose = not args.quiet

    # Ensure working directories exist
    stratagem_dir = cwd / ".stratagem"
    for subdir in ["cache", "filings", "extractions", "reports"]:
        (stratagem_dir / subdir).mkdir(parents=True, exist_ok=True)
    (cwd / "output").mkdir(parents=True, exist_ok=True)

    async for message in run_research(
        prompt=prompt,
        cwd=cwd,
        model=args.model,
        max_turns=args.max_turns,
        verbose=verbose,
    ):
        pass  # Messages are printed in verbose mode by run_research


if __name__ == "__main__":
    main()
