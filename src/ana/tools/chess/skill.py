"""Chess skill tool for ANA.

This module exposes chess analysis as a tool that ANA can use to play chess.
It includes human-like thinking delays to simulate natural gameplay.
"""

import asyncio
import logging
import random

import aiohttp
from livekit.agents import function_tool

from .adapters.remote_stockfish import RemoteStockfishAdapter
from .engine_interface import MoveResult

logger = logging.getLogger(__name__)

# Singleton engine instance
_engine: RemoteStockfishAdapter | None = None


def _get_engine() -> RemoteStockfishAdapter:
    """Get or create the chess engine adapter."""
    global _engine
    if _engine is None:
        _engine = RemoteStockfishAdapter()
    return _engine


# Difficulty settings map to search depth
DIFFICULTY_DEPTHS = {
    "easy": 4,
    "medium": 8,
    "hard": 12,
}

# Thinking delay ranges (min, max) in seconds per difficulty
THINKING_DELAYS = {
    "easy": (3.0, 5.0),
    "medium": (5.0, 10.0),
    "hard": (10.0, 15.0),
}


async def _get_move_with_delay(
    fen: str,
    difficulty: str = "medium",
) -> MoveResult:
    """
    Get best move with human-like thinking delay.

    Args:
        fen: FEN string of the current position
        difficulty: 'easy', 'medium', or 'hard'

    Returns:
        MoveResult with the best move and analysis
    """
    engine = _get_engine()
    depth = DIFFICULTY_DEPTHS.get(difficulty, 8)
    delay_range = THINKING_DELAYS.get(difficulty, (5.0, 10.0))

    # Human-like thinking delay
    thinking_time = random.uniform(*delay_range)
    logger.info(f"Chess: Thinking for {thinking_time:.1f}s at depth {depth}...")

    # Start both the delay and the analysis
    result, _ = await asyncio.gather(
        engine.get_best_move(fen, depth=depth),
        asyncio.sleep(thinking_time),
    )

    return result


@function_tool()
async def analyze_chess_position(
    fen: str,
    player_color: str = "white",
    difficulty: str = "medium",
    game_id: str | None = None,
) -> str:
    """
    Analyze a chess position and suggest the best move.

    Use this when playing chess to determine your next move.
    If a game_id is provided, the move will be automatically applied to the board.

    Args:
        fen: FEN string representing the current board position.
        player_color: Which color you are playing - 'white' or 'black'
        difficulty: How hard to play - 'easy', 'medium', or 'hard'
        game_id: Optional ID of the active game to apply the move to.
    """
    try:
        result = await _get_move_with_delay(fen, difficulty)

        # Build response
        response_parts = [f"I'll play **{result.san}**"]

        if result.explanation:
            response_parts.append(result.explanation)

        # Apply move to game server if game_id provided
        if game_id:
            async with aiohttp.ClientSession() as session:
                url = "http://localhost:8765/api/move"
                payload = {
                    "game_id": game_id,
                    "move": result.move,
                    "explanation": result.explanation or f"Playing {result.san}",
                }
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        logger.error(
                            f"Failed to apply move to server: {await resp.text()}"
                        )

        if result.mate_in is not None:
            if (result.mate_in > 0 and player_color == "white") or (
                result.mate_in < 0 and player_color == "black"
            ):
                response_parts.append(f"Checkmate in {abs(result.mate_in)}! 🎯")
            else:
                response_parts.append(
                    f"I see mate in {abs(result.mate_in)} against me... "
                    "but I'll fight on!"
                )

        return " ".join(response_parts)

    except Exception as e:
        logger.error(f"Chess analysis failed: {e}")
        return f"I'm having trouble analyzing this position right now. Error: {str(e)}"


@function_tool()
async def get_active_chess_games() -> str:
    """
    Check the chess server for any active games.

    Use this to find out if there's a game in progress that you should participate in.
    Returns a current summary of active games, including their IDs, players, and positions.
    """
    try:
        async with aiohttp.ClientSession() as session:
            url = "http://localhost:8765/health"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    games = data.get("games", [])
                    if not games:
                        return (
                            "There are no active chess games on the server right now."
                        )

                    results = []
                    for g in games:
                        white = g.get("white", {}).get("name", "Unknown")
                        black = g.get("black", {}).get("name", "Unknown")
                        results.append(
                            f"Game ID: {g.get('id')}\n"
                            f"Players: {white} (White) vs {black} (Black)\n"
                            f"Status: {g.get('status')}\n"
                            f"Position (FEN): {g.get('fen')}"
                        )

                    return "Active Chess Games:\n\n" + "\n---\n".join(results)
                else:
                    return "I couldn't reach the chess server right now."
    except Exception as e:
        return f"Error connecting to chess server: {str(e)}"


@function_tool()
async def get_chess_move(
    fen: str,
    difficulty: str = "medium",
) -> str:
    """
    Get the best chess move for the current position.

    This is a simpler version that just returns the move in UCI format.

    Args:
        fen: FEN string of the current board position
        difficulty: 'easy', 'medium', or 'hard'

    Returns:
        The best move in UCI format (e.g., 'e2e4')
    """
    try:
        result = await _get_move_with_delay(fen, difficulty)
        return result.move
    except Exception as e:
        logger.error(f"Chess move calculation failed: {e}")
        return f"error: {str(e)}"
