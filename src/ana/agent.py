"""Main agent implementation for ANA."""

import asyncio

from google.genai import types
from livekit import agents
from livekit.agents import Agent, AgentSession, RoomInputOptions
from livekit.plugins import google, noise_cancellation

from .config import config
from .prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from .tools import get_tools
from .tools.memory import (
    create_memory_context,
    initialize_mem0_client,
    load_initial_memories,
    save_conversation_to_mem0,
)
from .tools.system import close_terminal_window


class Assistant(Agent):
    """ANA Assistant agent."""

    def __init__(self, chat_ctx=None) -> None:
        """Initialize the agent."""
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            llm=google.beta.realtime.RealtimeModel(
                model=config.model["model_name"],
                _gemini_tools=[types.GoogleSearch()],
                voice=config.model["voice"],
                temperature=config.model["temperature"],
            ),
            tools=[],  # Tools will be set after async initialization
            chat_ctx=chat_ctx,
        )


async def entrypoint(ctx: agents.JobContext):
    """Main entrypoint for the agent."""
    session = AgentSession()
    user_name = config.get("user_name")

    # Parallel initialization for faster startup
    async def init_memory():
        """Initialize mem0 in parallel."""
        try:
            # Initialize mem0 client (already async)
            mem0 = await initialize_mem0_client()
            # Load initial memories (now async)
            results, memory_str = await load_initial_memories(mem0, user_name, 5)
            return mem0, results, memory_str
        except Exception as e:
            agents.logger.warning(f"Failed to initialize memory: {e}")
            return None, [], ""

    async def init_tools():
        """Get tools (runs in parallel)."""
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, get_tools)

    # Run mem0 and tool initialization in parallel
    (mem0, results, memory_str), tools = await asyncio.gather(
        init_memory(),
        init_tools(),
    )

    initial_ctx = create_memory_context(results, user_name, has_mem0=mem0 is not None)

    # Define shutdown hook for saving conversation to Mem0
    async def save_conversation():
        """Wrapper for save_conversation_to_mem0."""
        await save_conversation_to_mem0(session, mem0, user_name, memory_str)

    # Register shutdown callbacks
    ctx.add_shutdown_callback(save_conversation)
    ctx.add_shutdown_callback(close_terminal_window)

    # Create assistant with pre-loaded tools
    assistant = Assistant(chat_ctx=initial_ctx)
    assistant._tools = tools  # Use pre-loaded tools

    await session.start(
        room=ctx.room,
        agent=assistant,
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
