"""Remote Stockfish adapter using chess-api.com REST API.

This adapter connects to the free chess-api.com service which provides
Stockfish 17 NNUE analysis with up to 80 MNPS calculation power.
"""

import logging
from typing import Any

import aiohttp

from ..engine_interface import ChessEngineInterface, MoveResult

logger = logging.getLogger(__name__)


class RemoteStockfishAdapter(ChessEngineInterface):
    """Chess engine adapter using chess-api.com REST API."""

    API_URL = "https://chess-api.com/v1"

    def __init__(self):
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_best_move(
        self,
        fen: str,
        depth: int = 12,
        max_thinking_time: int = 50,
    ) -> MoveResult:
        """
        Get the best move for a given position using chess-api.com.

        Args:
            fen: FEN string of the current position
            depth: Search depth (max 12 for free tier, max 18 for supporters)
            max_thinking_time: Max thinking time in ms (max 100)

        Returns:
            MoveResult with the best move and analysis
        """
        session = await self._get_session()

        payload = {
            "fen": fen,
            "depth": min(depth, 12),  # Free tier limit
            "maxThinkingTime": min(max_thinking_time, 100),
            "variants": 1,
        }

        try:
            async with session.post(
                self.API_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status != 200:
                    logger.error(f"Chess API error: {response.status}")
                    raise Exception(f"Chess API returned status {response.status}")

                data = await response.json()
                return self._parse_response(data)

        except aiohttp.ClientError as e:
            logger.error(f"Network error calling chess API: {e}")
            raise

    def _parse_response(self, data: dict[str, Any]) -> MoveResult:
        """Parse the chess-api.com response into a MoveResult."""
        # Handle case where response is a list (multiple variants)
        if isinstance(data, list):
            data = data[0] if data else {}

        move = data.get("move", data.get("lan", ""))
        san = data.get("san", move)

        # Ensure numeric types
        try:
            evaluation = float(data.get("eval", 0.0))
        except (ValueError, TypeError):
            evaluation = 0.0

        try:
            depth = int(data.get("depth", 0))
        except (ValueError, TypeError):
            depth = 0

        mate_in = data.get("mate")
        if mate_in is not None:
            try:
                mate_in = int(mate_in)
            except (ValueError, TypeError):
                mate_in = None

        continuation = data.get("continuationArr", [])

        try:
            win_chance = float(data.get("winChance", 50.0))
        except (ValueError, TypeError):
            win_chance = 50.0

        text = data.get("text", "")

        # Generate natural language explanation
        explanation = self._generate_explanation(
            san=san,
            evaluation=evaluation,
            mate_in=mate_in,
            win_chance=win_chance,
            text=text,
        )

        return MoveResult(
            move=move,
            san=san,
            evaluation=evaluation,
            depth=depth,
            mate_in=mate_in,
            continuation=continuation,
            win_chance=win_chance,
            explanation=explanation,
        )

    def _generate_explanation(
        self,
        san: str,
        evaluation: float,
        mate_in: int | None,
        win_chance: float,
        text: str,
    ) -> str:
        """Generate a natural language explanation of the move."""
        if text:
            return text

        parts = []

        if mate_in is not None:
            if mate_in > 0:
                parts.append(f"This leads to checkmate in {mate_in} moves!")
            else:
                parts.append(f"Unfortunately, we're facing mate in {abs(mate_in)}.")
        else:
            if abs(evaluation) < 0.5:
                parts.append("The position is roughly equal.")
            elif evaluation > 2:
                parts.append("White has a significant advantage.")
            elif evaluation > 0.5:
                parts.append("White is slightly better.")
            elif evaluation < -2:
                parts.append("Black has a significant advantage.")
            elif evaluation < -0.5:
                parts.append("Black is slightly better.")

        return " ".join(parts) if parts else f"Playing {san}."

    async def is_available(self) -> bool:
        """Check if the chess API is available."""
        try:
            session = await self._get_session()
            # Test with starting position
            test_payload = {
                "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                "depth": 1,
                "maxThinkingTime": 10,
            }
            async with session.post(
                self.API_URL,
                json=test_payload,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.warning(f"Chess API availability check failed: {e}")
            return False
