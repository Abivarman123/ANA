"""Main agent implementation for ANA with extended session support."""

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
    """ANA Assistant agent with extended session support."""

    def __init__(self, chat_ctx=None) -> None:
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            llm=google.beta.realtime.RealtimeModel(
                model=config.model["model_name"],
                _gemini_tools=[types.GoogleSearch()],
                voice=config.model["voice"],
                temperature=config.model["temperature"],
                context_window_compression=types.ContextWindowCompressionConfig(
                    sliding_window=types.SlidingWindow(),
                    trigger_tokens=16000,
                ),
                session_resumption=types.SessionResumptionConfig(handle=None),
            ),
            tools=get_tools(),
            chat_ctx=chat_ctx,
        )


async def entrypoint(ctx: agents.JobContext):
    """Main entrypoint for the agent."""
    await ctx.connect()

    session = AgentSession()
    user_name = config.get("user_name")

    # Initialize Mem0 client
    try:
        mem0 = initialize_mem0_client()
        results, memory_str = load_initial_memories(mem0, user_name, count=10)
        initial_ctx = create_memory_context(results, user_name, has_mem0=True)
    except Exception:
        mem0 = None
        results, memory_str = [], ""
        initial_ctx = create_memory_context([], user_name, has_mem0=False)

    # Register shutdown callbacks
    ctx.add_shutdown_callback(
        lambda: save_conversation_to_mem0(session, mem0, user_name, memory_str)
    )
    ctx.add_shutdown_callback(close_terminal_window)

    # Create and start assistant
    assistant = Assistant(chat_ctx=initial_ctx)

    await session.start(
        room=ctx.room,
        agent=assistant,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await session.generate_reply(instructions=SESSION_INSTRUCTION)


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
