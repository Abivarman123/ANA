"""ANA player wrapper for the chess server.

This module provides the integration between the chess server and
ANA's chess skill, allowing ANA to play as a participant in games.
"""

import logging
import re

from src.ana.tools.chess.skill import analyze_chess_position

from .models import Game, PlayerType

logger = logging.getLogger(__name__)


class ANAPlayer:
    """
    Wrapper to invoke ANA's chess skill during games.

    This class acts as a bridge between the game server and ANA's
    chess analysis capabilities.
    """

    def __init__(self):
        self._thinking = False

    async def get_move(self, game: Game, player_color: str | None = None) -> dict:
        """
        Get ANA's move for the current game position.

        Args:
            game: The current game state
            player_color: Optional override for which color to play/analyze as.
                         If None, infers from game settings where ANA is a player.

        Returns:
            dict with:
                - move: UCI format move string
                - explanation: Natural language explanation
                - success: bool
        """
        if self._thinking:
            return {
                "success": False,
                "error": "Already thinking about a move",
            }

        self._thinking = True

        try:
            # Determine which color ANA is playing if not specified
            if player_color is None:
                if game.white.type == PlayerType.ANA:
                    player_color = "white"
                elif game.black.type == PlayerType.ANA:
                    player_color = "black"
                else:
                    return {
                        "success": False,
                        "error": "ANA is not a player in this game",
                    }

            logger.info(
                f"ANA thinking... (game={game.id}, color={player_color}, "
                f"difficulty={game.difficulty})"
            )

            # Call the chess skill (includes thinking delay)
            explanation = await analyze_chess_position(
                fen=game.fen,
                player_color=player_color,
                difficulty=game.difficulty,
            )

            # Extract the move from the explanation
            # The skill returns something like "I'll play **e4**. The position is..."
            move = self._extract_move_from_explanation(explanation, game.fen)

            if not move:
                # Fallback: get just the move
                from src.ana.tools.chess.skill import get_chess_move

                move = await get_chess_move(fen=game.fen, difficulty=game.difficulty)

            logger.info(f"ANA plays: {move}")

            return {
                "success": True,
                "move": move,
                "explanation": explanation,
            }

        except Exception as e:
            logger.error(f"ANA move calculation failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

        finally:
            self._thinking = False

    def _extract_move_from_explanation(self, explanation: str, fen: str) -> str | None:
        """
        Extract UCI move from the explanation text.

        The explanation format is typically:
        "I'll play **Nf3**. Some explanation..."

        We need to convert SAN to UCI using the current position.
        """
        import chess

        # Look for move in bold (**move**)
        match = re.search(r"\*\*([A-Za-z0-9+#=]+)\*\*", explanation)
        if not match:
            return None

        san_move = match.group(1)

        try:
            board = chess.Board(fen)
            move = board.parse_san(san_move)
            return move.uci()
        except (ValueError, chess.InvalidMoveError, chess.AmbiguousMoveError) as e:
            logger.warning(f"Could not parse SAN move '{san_move}': {e}")
            return None

    @property
    def is_thinking(self) -> bool:
        """Check if ANA is currently thinking."""
        return self._thinking
