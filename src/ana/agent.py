"""Main agent implementation for ANA using AgentServer pattern."""

import datetime
import platform

from google.genai import types
from livekit import agents, rtc
from livekit.agents import Agent, AgentServer, AgentSession, room_io
from livekit.plugins import google, noise_cancellation

from .config import config
from .prompts import CONTEXT_TEMPLATE, NUEROSAMA_MODE, SESSION_INSTRUCTION
from .tools import get_tools
from .tools.memory import (
    create_memory_context,
    initialize_mem0_client,
    load_initial_memories,
    save_conversation_to_mem0,
)
from .tools.system import close_terminal_window

# Initialize Server
server = AgentServer()


class Assistant(Agent):
    """ANA Assistant agent."""

    def __init__(self, instructions: str, chat_ctx=None) -> None:
        realtime_input_cfg = types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(),
        )
        super().__init__(
            instructions=instructions,
            llm=google.beta.realtime.RealtimeModel(
                model=config.model["model_name"],
                voice=config.model["voice"],
                temperature=config.model["temperature"],
                context_window_compression=types.ContextWindowCompressionConfig(
                    sliding_window=types.SlidingWindow(),
                    trigger_tokens=16000,
                ),
                session_resumption=types.SessionResumptionConfig(handle=None),
                realtime_input_config=realtime_input_cfg,
            ),
            tools=get_tools(),
            chat_ctx=chat_ctx,
        )

    async def on_user_message(self, message: str):
        """Handle incoming text messages."""
        pass


@server.rtc_session()
async def entrypoint(ctx: agents.JobContext):
    """Main entrypoint for the agent."""
    await ctx.connect()

    session = AgentSession()
    user_name = config.get("user_name")

    # Initialize Mem0 client
    try:
        mem0 = await initialize_mem0_client()
        results, memory_str = await load_initial_memories(mem0, user_name, count=10)
        initial_ctx = create_memory_context(results, user_name, has_mem0=True)
    except Exception:
        mem0 = None
        results, memory_str = [], ""
        initial_ctx = create_memory_context([], user_name, has_mem0=False)

    # Register shutdown callbacks
    async def save_memory_callback():
        await save_conversation_to_mem0(session, mem0, user_name, memory_str)

    ctx.add_shutdown_callback(save_memory_callback)
    ctx.add_shutdown_callback(close_terminal_window)

    # Prepare dynamic system instructions
    dynamic_context = CONTEXT_TEMPLATE.format(
        date=datetime.date.today().isoformat(),
        user_name=user_name,
        os_name=platform.system(),
    )
    full_instructions = f"{dynamic_context}\n{NUEROSAMA_MODE}"

    assistant = Assistant(instructions=full_instructions, chat_ctx=initial_ctx)

    await session.start(
        room=ctx.room,
        agent=assistant,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony()
                if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                else noise_cancellation.BVC(),
            ),
        ),
    )

    await session.generate_reply(instructions=SESSION_INSTRUCTION)


if __name__ == "__main__":
    agents.cli.run_app(server)
