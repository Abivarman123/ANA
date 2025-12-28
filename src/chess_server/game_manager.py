"""Authoritative game state manager using python-chess.

This module handles all game logic, move validation, and state management.
The server is the single source of truth for game state.
"""

import logging
import uuid
from typing import Callable

import chess

from .models import Game, GameStatus, Player

logger = logging.getLogger(__name__)


class GameManager:
    """
    Manages chess game state and move validation.

    Uses python-chess for authoritative move validation and game state.
    """

    def __init__(self):
        self.games: dict[str, Game] = {}
        self.boards: dict[str, chess.Board] = {}
        self._on_game_end_callbacks: list[Callable] = []

    def create_game(
        self,
        white: Player,
        black: Player,
        difficulty: str = "medium",
    ) -> Game:
        """
        Create a new chess game.

        Args:
            white: The white player
            black: The black player
            difficulty: Difficulty level for ANA ('easy', 'medium', 'hard')

        Returns:
            The newly created Game
        """
        game_id = str(uuid.uuid4())
        game = Game(
            id=game_id,
            white=white,
            black=black,
            status=GameStatus.ACTIVE,
            difficulty=difficulty,
        )
        self.games[game_id] = game
        self.boards[game_id] = chess.Board()

        logger.info(f"Created game {game_id}: {white.name} vs {black.name}")
        return game

    def get_game(self, game_id: str) -> Game | None:
        """Get a game by ID."""
        return self.games.get(game_id)

    def make_move(self, game_id: str, move_uci: str) -> dict:
        """
        Attempt to make a move in a game.

        Args:
            game_id: The game ID
            move_uci: Move in UCI format (e.g., 'e2e4', 'e7e8q' for promotion)

        Returns:
            dict with:
                - success: bool
                - error: str (if failed)
                - fen: new FEN (if success)
                - san: move in SAN notation (if success)
                - game_over: bool
                - result: game result if over
        """
        game = self.games.get(game_id)
        board = self.boards.get(game_id)

        if not game or not board:
            return {"success": False, "error": "Game not found"}

        if game.status != GameStatus.ACTIVE:
            return {"success": False, "error": "Game is not active"}

        try:
            move = chess.Move.from_uci(move_uci)
        except ValueError:
            return {"success": False, "error": f"Invalid move format: {move_uci}"}

        if move not in board.legal_moves:
            return {"success": False, "error": f"Illegal move: {move_uci}"}

        # Make the move
        san = board.san(move)
        board.push(move)

        # Update game state
        game.fen = board.fen()
        game.moves.append(move_uci)

        result = {
            "success": True,
            "fen": game.fen,
            "san": san,
            "move": move_uci,
            "game_over": False,
        }

        # Check for game end conditions
        if board.is_checkmate():
            game.status = GameStatus.FINISHED
            game.winner = "black" if board.turn else "white"
            result["game_over"] = True
            result["result"] = f"Checkmate! {game.winner.capitalize()} wins!"
            logger.info(f"Game {game_id} ended: {result['result']}")

        elif board.is_stalemate():
            game.status = GameStatus.FINISHED
            game.winner = "draw"
            result["game_over"] = True
            result["result"] = "Stalemate - Draw!"
            logger.info(f"Game {game_id} ended: Stalemate")

        elif board.is_insufficient_material():
            game.status = GameStatus.FINISHED
            game.winner = "draw"
            result["game_over"] = True
            result["result"] = "Draw by insufficient material"
            logger.info(f"Game {game_id} ended: Insufficient material")

        elif board.can_claim_draw():
            # Could implement draw offers here
            pass

        if board.is_check() and not result.get("game_over"):
            result["check"] = True

        return result

    def get_legal_moves(self, game_id: str) -> list[str]:
        """Get all legal moves in UCI format for the current position."""
        board = self.boards.get(game_id)
        if not board:
            return []
        return [move.uci() for move in board.legal_moves]

    def get_current_turn(self, game_id: str) -> str:
        """Get whose turn it is ('white' or 'black')."""
        board = self.boards.get(game_id)
        if not board:
            return "white"
        return "white" if board.turn else "black"

    def is_game_over(self, game_id: str) -> bool:
        """Check if the game is over."""
        board = self.boards.get(game_id)
        if not board:
            return False
        return board.is_game_over()

    def resign(self, game_id: str, player_id: str) -> dict:
        """Handle a player resignation."""
        game = self.games.get(game_id)
        if not game:
            return {"success": False, "error": "Game not found"}

        if game.white.id == player_id:
            game.winner = "black"
        elif game.black.id == player_id:
            game.winner = "white"
        else:
            return {"success": False, "error": "Player not in this game"}

        game.status = GameStatus.FINISHED
        return {
            "success": True,
            "result": f"{game.winner.capitalize()} wins by resignation!",
        }

    def abandon_game(self, game_id: str) -> None:
        """Mark a game as abandoned (e.g., player disconnected)."""
        game = self.games.get(game_id)
        if game:
            game.status = GameStatus.ABANDONED
            logger.info(f"Game {game_id} abandoned")

    def add_chat_message(
        self,
        game_id: str,
        sender_id: str,
        sender_name: str,
        message: str,
    ) -> dict | None:
        """Add a chat message to a game."""
        import time

        game = self.games.get(game_id)
        if not game:
            return None

        chat_msg = {
            "sender": sender_id,
            "senderName": sender_name,
            "message": message,
            "timestamp": time.time(),
        }
        game.chat_messages.append(chat_msg)
        return chat_msg

    def cleanup_finished_games(self, max_age_seconds: int = 3600) -> int:
        """Remove finished games older than max_age_seconds."""
        removed = 0

        for game_id in list(self.games.keys()):
            game = self.games[game_id]
            if game.status in (GameStatus.FINISHED, GameStatus.ABANDONED):
                # For simplicity, remove all finished games
                # In production, track game end time
                del self.games[game_id]
                del self.boards[game_id]
                removed += 1

        if removed:
            logger.info(f"Cleaned up {removed} finished games")
        return removed
