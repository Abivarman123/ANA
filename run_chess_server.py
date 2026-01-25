"""Entry point to run the chess server standalone."""

import asyncio
import logging
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(__file__).rsplit("src", 1)[0])

from src.chess_server.server import run_server


def main():
    """Run the chess server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 50)
    print("  ANA Chess Server")
    print("=" * 50)
    print()
    print("Starting WebSocket server...")
    print("Connect at: ws://localhost:8765/ws")
    print()
    print("Press Ctrl+C to stop")
    print()

    try:
        asyncio.run(run_server(host="0.0.0.0", port=8765))
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
