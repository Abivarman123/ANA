"""Main entry point for ANA."""

from livekit import agents

from src.ana.agent import entrypoint

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
