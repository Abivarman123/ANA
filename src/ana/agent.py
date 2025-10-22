"""Main agent implementation for ANA."""

from google.genai import types
from livekit import agents
from livekit.agents import Agent, AgentSession, RoomInputOptions
from livekit.plugins import google, noise_cancellation

from .config import config
from .prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from .tools import get_tools


class Assistant(Agent):
    """ANA Assistant agent."""

    def __init__(self) -> None:
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            llm=google.beta.realtime.RealtimeModel(
                model=config.model["model_name"],
                _gemini_tools=[types.GoogleSearch()],
                voice=config.model["voice"],
                temperature=config.model["temperature"],
            ),
            tools=get_tools(),
        )


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
