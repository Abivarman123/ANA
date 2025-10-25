"""Main agent implementation for ANA."""

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
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            llm=google.beta.realtime.RealtimeModel(
                model=config.model["model_name"],
                _gemini_tools=[types.GoogleSearch()],
                voice=config.model["voice"],
                temperature=config.model["temperature"],
            ),
            tools=get_tools(),
            chat_ctx=chat_ctx,
        )


async def entrypoint(ctx: agents.JobContext):
    """Main entrypoint for the agent."""

    session = AgentSession()
    user_name = config.get("user_name")

    # Initialize Mem0 client with custom instructions
    try:
        mem0 = initialize_mem0_client()
        # Load initial memories at startup (optimized for performance)
        results, memory_str = load_initial_memories(mem0, user_name, count=10)
        # Create initial chat context with loaded memories
        initial_ctx = create_memory_context(
            results, user_name, has_mem0=mem0 is not None
        )
    except Exception as e:
        # Log the error and fall back to no memory context
        agents.logger.warning(f"Failed to initialize memory: {e}")
        mem0 = None
        results, memory_str = [], ""
        initial_ctx = create_memory_context([], user_name, has_mem0=False)

    # Define shutdown hook for saving conversation to Mem0
    async def save_conversation():
        """Wrapper for save_conversation_to_mem0."""
        await save_conversation_to_mem0(session, mem0, user_name, memory_str)

    # Register shutdown callbacks
    ctx.add_shutdown_callback(save_conversation)
    ctx.add_shutdown_callback(close_terminal_window)

    await session.start(
        room=ctx.room,
        agent=Assistant(chat_ctx=initial_ctx),
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
