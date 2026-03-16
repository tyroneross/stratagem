"""Runtime specialist agent creation tool."""

from typing import Any

from claude_agent_sdk import tool


@tool(
    "create_specialist",
    "Create a temporary specialist agent to handle a capability gap identified during research planning. "
    "The new agent becomes available immediately for dispatch via the Agent tool.",
    {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Agent identifier (lowercase-hyphenated, e.g. 'patent-analyst')",
            },
            "description": {
                "type": "string",
                "description": "One-line description of what this agent does",
            },
            "instructions": {
                "type": "string",
                "description": "Full system prompt / instructions for the agent",
            },
            "model": {
                "type": "string",
                "description": "Model to use — 'sonnet' (default), 'opus', or 'haiku'",
                "enum": ["sonnet", "opus", "haiku"],
                "default": "sonnet",
            },
            "tools": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tool names the agent can use. Defaults to [Read, Write, WebSearch, Bash]",
            },
        },
        "required": ["name", "description", "instructions"],
    },
)
async def create_specialist(args: dict[str, Any]) -> dict[str, Any]:
    from claude_agent_sdk import AgentDefinition
    import stratagem.agent as _agent_mod

    name = args["name"]
    description = args["description"]
    instructions = args["instructions"]
    model = args.get("model", "sonnet")
    tools = args.get("tools", ["Read", "Write", "WebSearch", "Bash"])

    if _agent_mod._active_run_agents is None:
        return {"error": "No active research run."}

    if name in _agent_mod._active_run_agents:
        return {"error": f"Agent '{name}' already exists."}

    if model not in ("sonnet", "opus", "haiku"):
        return {"error": f"Invalid model '{model}'. Use sonnet, opus, or haiku."}

    agent_def = AgentDefinition(
        description=description,
        prompt=instructions,
        tools=tools,
        model=model,
    )
    _agent_mod._active_run_agents[name] = agent_def

    # Record for post-run persistence
    if not hasattr(_agent_mod, '_dynamic_agents_created'):
        _agent_mod._dynamic_agents_created = {}
    _agent_mod._dynamic_agents_created[name] = {
        "description": description,
        "prompt": instructions,
        "model": model,
        "tools": tools,
    }

    return {"ok": True, "message": f"Created specialist '{name}' ({model}). Dispatch it using the Agent tool."}
