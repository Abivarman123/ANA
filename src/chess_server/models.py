"""Data models for the chess game server."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PlayerType(str, Enum):
    """Type of player in a chess game."""

    HUMAN = "human"
    ANA = "ana"


class GameStatus(str, Enum):
    """Status of a chess game."""

    WAITING = "waiting"  # Waiting for second player
    ACTIVE = "active"  # Game in progress
    FINISHED = "finished"  # Game ended
    ABANDONED = "abandoned"  # Player disconnected


@dataclass
class Player:
    """Represents a player in a chess game."""

    id: str
    name: str
    type: PlayerType
    websocket: Any = None  # WebSocket connection (None for ANA)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
        }


@dataclass
class Game:
    """Represents a chess game with all its state."""

    id: str
    white: Player
    black: Player
    fen: str = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    moves: list[str] = field(default_factory=list)
    status: GameStatus = GameStatus.WAITING
    winner: str | None = None  # "white", "black", or "draw"
    chat_messages: list[dict] = field(default_factory=list)
    difficulty: str = "medium"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "white": self.white.to_dict(),
            "black": self.black.to_dict(),
            "fen": self.fen,
            "moves": self.moves,
            "status": self.status.value,
            "winner": self.winner,
            "difficulty": self.difficulty,
        }

    @property
    def current_turn(self) -> str:
        """Get whose turn it is based on FEN."""
        # FEN format: position activeColor castling enPassant halfmove fullmove
        parts = self.fen.split()
        if len(parts) >= 2:
            return "white" if parts[1] == "w" else "black"
        return "white"

    @property
    def is_ana_turn(self) -> bool:
        """Check if it's ANA's turn to move."""
        if self.current_turn == "white":
            return self.white.type == PlayerType.ANA
        return self.black.type == PlayerType.ANA


@dataclass
class ChatMessage:
    """A chat message in the game."""

    sender: str  # player id or "system"
    sender_name: str
    message: str
    timestamp: float

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "sender": self.sender,
            "senderName": self.sender_name,
            "message": self.message,
            "timestamp": self.timestamp,
        }
