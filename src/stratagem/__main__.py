"""CLI entry point: python -m stratagem"""

import asyncio
import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        prog="stratagem",
        description="Market research agent — document processing, web scraping, and financial analysis",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
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
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    args = parser.parse_args()

    if not args.prompt:
        # Interactive mode: read from stdin
        if sys.stdin.isatty():
            parser.print_help()
            print("\nExamples:")
            print('  stratagem "What are the earnings trends for top networking companies?"')
            print('  stratagem "Analyze Cisco\'s latest 10-K filing"')
            print('  stratagem "Extract key metrics from report.pdf"')
            sys.exit(0)
        else:
            args.prompt = sys.stdin.read().strip()
            if not args.prompt:
                print("Error: No prompt provided", file=sys.stderr)
                sys.exit(1)

    try:
        asyncio.run(_run(args))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


async def _run(args):
    from stratagem.agent import run_research

    cwd = Path(args.cwd) if args.cwd else Path.cwd()
    verbose = not args.quiet

    # Ensure working directories exist
    stratagem_dir = cwd / ".stratagem"
    for subdir in ["cache", "filings", "extractions", "reports"]:
        (stratagem_dir / subdir).mkdir(parents=True, exist_ok=True)
    (cwd / "output").mkdir(parents=True, exist_ok=True)

    async for message in run_research(
        prompt=args.prompt,
        cwd=cwd,
        model=args.model,
        max_turns=args.max_turns,
        verbose=verbose,
    ):
        pass  # Messages are printed in verbose mode by run_research


if __name__ == "__main__":
    main()
