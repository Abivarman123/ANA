"""Abstract interface for chess engine adapters.

This module defines the contract that all chess engine implementations must follow,
allowing for easy swapping between remote (chess-api.com) and local (Stockfish binary) adapters.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class MoveResult:
    """Result from a chess engine analysis."""

    move: str  # UCI format, e.g., "e2e4"
    san: str  # Standard Algebraic Notation, e.g., "e4"
    evaluation: float  # Centipawn evaluation (positive = white advantage)
    depth: int  # Search depth reached
    mate_in: int | None = None  # Forced mate in N moves (None if no mate found)
    continuation: list[str] = field(default_factory=list)  # Suggested continuation
    win_chance: float = 50.0  # Win probability percentage
    explanation: str = ""  # Natural language explanation


class ChessEngineInterface(ABC):
    """Abstract base class for chess engine adapters."""

    @abstractmethod
    async def get_best_move(
        self,
        fen: str,
        depth: int = 12,
        max_thinking_time: int = 50,
    ) -> MoveResult:
        """
        Analyze a chess position and return the best move.

        Args:
            fen: FEN string representing the current board position
            depth: Search depth (higher = stronger but slower, max 18)
            max_thinking_time: Maximum thinking time in milliseconds

        Returns:
            MoveResult containing the best move and analysis data
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the engine is available and responding."""
        pass
