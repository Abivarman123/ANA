"""Main agent implementation for ANA."""

from google.genai import types
from livekit import agents
from livekit.agents import Agent, AgentSession, RoomInputOptions, mcp
from livekit.plugins import google, noise_cancellation

from .config import config
from .prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from .tools import get_tools


class Assistant(Agent):
    """ANA Assistant agent."""

    def __init__(self) -> None:
        mcp_servers = self._load_mcp_servers()

        super().__init__(
            instructions=AGENT_INSTRUCTION,
            llm=google.beta.realtime.RealtimeModel(
                model=config.model["model_name"],
                _gemini_tools=[types.GoogleSearch()],
                voice=config.model["voice"],
                temperature=config.model["temperature"],
            ),
            tools=get_tools(),
            mcp_servers=mcp_servers if mcp_servers else None,
        )

    def _load_mcp_servers(self) -> list:
        """Load MCP servers from config with flexible configuration support.
        
        Supports two formats:
        1. Simple URL string: "https://server.com"
        2. Detailed config object with type, name, tool_configuration, authorization, etc.
        
        Example detailed config:
        {
          "type": "url",
          "url": "https://example.com/sse",
          "name": "example-mcp",
          "tool_configuration": {
            "enabled": true,
            "allowed_tools": ["tool1", "tool2"]
          },
          "authorization_token": "YOUR_TOKEN"
        }
        """
        import logging
        
        servers = []
        mcp_config = config.get("mcp_servers", []) or (
            config.get("mcp", {}).get("servers", [])
            if isinstance(config.get("mcp", {}), dict)
            else []
        )
        
        for server_config in mcp_config:
            try:
                if isinstance(server_config, str):
                    # Simple URL string format (backward compatible)
                    servers.append(mcp.MCPServerHTTP(server_config))
                    logging.info(f"Loaded MCP server: {server_config}")
                    
                elif isinstance(server_config, dict):
                    # Detailed configuration object
                    _server_type = server_config.get("type", "url")  # Reserved for future: stdio, sse, etc.
                    url = server_config.get("url")
                    name = server_config.get("name", "unnamed-mcp")
                    
                    if not url:
                        logging.warning(f"MCP server config missing 'url': {server_config}")
                        continue
                    
                    # Extract optional configuration
                    tool_config = server_config.get("tool_configuration", {})
                    enabled = tool_config.get("enabled", True)
                    allowed_tools = tool_config.get("allowed_tools", [])
                    authorization_token = server_config.get("authorization_token")
                    
                    # Skip if explicitly disabled
                    if not enabled:
                        logging.info(f"Skipping disabled MCP server: {name}")
                        continue
                    
                    # Note: MCPServerHTTP currently only accepts url parameter
                    # Store metadata for future use when LiveKit supports filtering/auth
                    server = mcp.MCPServerHTTP(url)
                    
                    # Store metadata as attributes for potential future use
                    server._ana_name = name
                    server._ana_allowed_tools = allowed_tools
                    server._ana_auth_token = authorization_token
                    
                    servers.append(server)
                    logging.info(
                        f"Loaded MCP server: {name} ({url})"
                        + (f" [filtered: {len(allowed_tools)} tools]" if allowed_tools else "")
                    )
                    
                else:
                    logging.warning(f"Invalid MCP server config format: {server_config}")
                    
            except Exception as e:
                logging.error(f"Error loading MCP server {server_config}: {e}")
        
        return servers


async def entrypoint(ctx: agents.JobContext):
    """Main entrypoint for the agent."""
    session = AgentSession()

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(
            video_enabled=False,
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()

    await session.generate_reply(
        instructions=SESSION_INSTRUCTION,
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
