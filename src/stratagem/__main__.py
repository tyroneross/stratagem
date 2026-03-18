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
        description="Strategic research agent — document processing, web scraping, and financial analysis",
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
        "--output-dir", "-o",
        type=str,
        default=None,
        help="Directory for output artifacts (default: ask user or <cwd>/output/)",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Use Sonnet for orchestrator (faster responses, lower cost)",
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
        "--thread",
        type=str,
        default=None,
        help="Thread ID for context retention (resume or name a thread)",
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="Topic ID to associate this run with (e.g., 'ai-chip-landscape')",
    )
    parser.add_argument(
        "--input",
        nargs="+",
        default=None,
        metavar="FILE",
        help="Input files for agents to use (e.g., report.pdf financials.xlsx)",
    )
    parser.add_argument(
        "--memory-budget",
        type=int,
        default=None,
        help="Token budget for memory injection (default: 8000)",
    )
    parser.add_argument(
        "--model-override",
        action="append",
        default=None,
        metavar="NAME:MODEL",
        help="Per-agent model override (e.g., --model-override data-extractor:haiku). Repeatable.",
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
    from datetime import datetime as _dt

    mode = "fast" if getattr(args, "fast", False) else (args.model or "opus")

    # Generate or resume thread
    thread_id = getattr(args, "thread", None) or f"cli_{_dt.now():%Y%m%d_%H%M%S}"
    args.thread = thread_id

    print(f"Stratagem v0.1.0 — Strategic research agent [{mode}]")
    print(f"Thread: {thread_id}")
    if getattr(args, "output_dir", None):
        print(f"Output: {Path(args.output_dir).resolve()}")
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
    output_dir = Path(args.output_dir).resolve() if getattr(args, "output_dir", None) else None
    verbose = not args.quiet
    thread_id = getattr(args, "thread", None)

    # --fast overrides model to sonnet for orchestrator
    model = args.model
    if getattr(args, "fast", False) and not model:
        model = "sonnet"

    # Ensure working directories exist
    stratagem_dir = cwd / ".stratagem"
    for subdir in ["cache", "filings", "extractions", "reports", "threads", "artifacts", "topics", "agents"]:
        (stratagem_dir / subdir).mkdir(parents=True, exist_ok=True)
    (cwd / "output").mkdir(parents=True, exist_ok=True)

    # Create thread if specified
    if thread_id:
        from stratagem.threads import create_thread
        create_thread(thread_id, cwd)

    # Create topic if specified
    if getattr(args, "topic", None):
        from stratagem.topics import create_topic
        create_topic(args.topic, cwd=cwd)

    # Parse --model-override flags into dict
    model_overrides = None
    if getattr(args, "model_override", None):
        model_overrides = {}
        for override in args.model_override:
            if ":" in override:
                name, mdl = override.split(":", 1)
                model_overrides[name] = mdl

    topic_id = getattr(args, "topic", None)
    input_files = getattr(args, "input", None)
    memory_budget = getattr(args, "memory_budget", None)

    if verbose:
        print("\033[2m▸ Running...\033[0m", flush=True)

    async for message in run_research(
        prompt=prompt,
        cwd=cwd,
        output_dir=output_dir,
        model=model,
        model_overrides=model_overrides,
        max_turns=args.max_turns,
        verbose=verbose,
        thread_id=thread_id,
        topic_id=topic_id,
        input_files=input_files,
        memory_budget=memory_budget,
    ):
        pass  # Messages are printed in verbose mode by run_research


if __name__ == "__main__":
    main()
