import asyncio
from livekit import agents

from src.ana.agent import entrypoint

if __name__ == "__main__":
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
