"""Main agent implementation for ANA using AgentServer pattern."""

import datetime
import logging
import platform

from google.genai import types
from livekit import agents
from livekit.agents import Agent, AgentServer, AgentSession, room_io
from livekit.plugins import google, noise_cancellation

from .config import config
from .prompts import CONTEXT_TEMPLATE, NEUROSAMA_MODE, SESSION_INSTRUCTION
from .tools import get_tools
from .tools.memory import (
    save_conversation_to_mem0,
    setup_memory_system,
)
from .tools.system import close_terminal_window

# Configure logging
logger = logging.getLogger(__name__)


class Assistant(Agent):
    """ANA Assistant agent."""

    def __init__(self, instructions: str, chat_ctx=None) -> None:
        super().__init__(
            instructions=instructions,
            chat_ctx=chat_ctx,
        )


# Initialize Server
server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: agents.JobContext):
    """Main entrypoint for the agent."""
    user_name = config.get("user_name")

    # Initialize Memory System
    mem0, initial_ctx, memory_str = await setup_memory_system(user_name)

    # Prepare dynamic system instructions
    dynamic_context = CONTEXT_TEMPLATE.format(
        date=datetime.date.today().isoformat(),
        user_name=user_name,
        os_name=platform.system(),
    )
    full_instructions = f"{dynamic_context}\n{NEUROSAMA_MODE}"

    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model=config.model["model_name"],
            voice=config.model["voice"],
            temperature=config.model["temperature"],
            thinking_config=types.ThinkingConfig(
                include_thoughts=False,
            ),
            context_window_compression=types.ContextWindowCompressionConfig(
                sliding_window=types.SlidingWindow(),
                trigger_tokens=16000,
            ),
            session_resumption=types.SessionResumptionConfig(handle=None),
        ),
        tools=get_tools(),
    )

    # Register shutdown callbacks
    async def save_memory_callback():
        try:
            await save_conversation_to_mem0(session, mem0, user_name, memory_str)
        except Exception as e:
            logger.error(f"Error in save_memory_callback: {e}")

    ctx.add_shutdown_callback(save_memory_callback)
    ctx.add_shutdown_callback(close_terminal_window)

    assistant = Assistant(instructions=full_instructions, chat_ctx=initial_ctx)

    await session.start(
        room=ctx.room,
        agent=assistant,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=noise_cancellation.BVC(),
            ),
        ),
    )

    await session.generate_reply(instructions=SESSION_INSTRUCTION)


if __name__ == "__main__":
    agents.cli.run_app(server)
