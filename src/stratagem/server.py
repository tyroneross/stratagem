"""MCP server creation and tool registry for Stratagem."""

from claude_agent_sdk import create_sdk_mcp_server

from stratagem.tools.pdf import parse_pdf
from stratagem.tools.web import scrape_url
from stratagem.tools.spreadsheet import read_spreadsheet
from stratagem.tools.presentation import read_pptx, create_pptx
from stratagem.tools.docx import read_docx
from stratagem.tools.images import extract_images
from stratagem.tools.sec_edgar import search_sec_filings, download_sec_filing
from stratagem.tools.reports import create_report
from stratagem.tools.spreadsheet_create import create_spreadsheet
from stratagem.tools.specialist import create_specialist
from stratagem.tools.memory import record_observation

# All custom tools
ALL_TOOLS = [
    parse_pdf,
    scrape_url,
    read_spreadsheet,
    read_pptx,
    create_pptx,
    read_docx,
    extract_images,
    search_sec_filings,
    download_sec_filing,
    create_report,
    create_spreadsheet,
    create_specialist,
    record_observation,
]

# Tool names for allowed_tools configuration
TOOL_NAMES = [f"mcp__stratagem__{t.name}" for t in ALL_TOOLS]

# Built-in tools the agent needs
BUILTIN_TOOLS = ["Read", "Write", "Glob", "Grep", "Bash", "WebSearch", "WebFetch", "Agent"]


def create_stratagem_server():
    """Create the Stratagem MCP server with all custom tools."""
    return create_sdk_mcp_server(
        name="stratagem",
        version="0.1.0",
        tools=ALL_TOOLS,
    )


def get_all_allowed_tools() -> list[str]:
    """Get full list of tool names to pre-approve."""
    return TOOL_NAMES + BUILTIN_TOOLS


if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server

    server_config = create_stratagem_server()
    mcp_server = server_config["instance"]

    async def _main():
        async with stdio_server() as (read_stream, write_stream):
            await mcp_server.run(
                read_stream, write_stream,
                mcp_server.create_initialization_options(),
            )

    asyncio.run(_main())
