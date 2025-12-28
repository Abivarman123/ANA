"""WebSocket-based chess game server.

This server handles:
- Game creation and management
- Real-time move broadcasting
- ANA integration for AI opponents
- Chat message relay
"""

import asyncio
import json
import logging
import uuid
from typing import Any

from aiohttp import WSMsgType, web

from .ana_player import ANAPlayer
from .game_manager import GameManager
from .models import Game, GameStatus, Player, PlayerType

logger = logging.getLogger(__name__)


class ChessServer:
    """
    WebSocket server for chess games.

    Handles multiplayer games with humans and ANA as potential players.
    """

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.game_manager = GameManager()
        self.ana_player = ANAPlayer()
        self.connections: dict[str, web.WebSocketResponse] = {}  # player_id -> ws
        self.player_games: dict[str, str] = {}  # player_id -> game_id
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None

    async def start(self):
        """Start the WebSocket server."""
        self._app = web.Application()
        self._app.router.add_get("/ws", self.handle_websocket)
        self._app.router.add_get("/health", self.handle_health)
        self._app.router.add_post("/api/move", self.handle_external_move)
        self._app.router.add_get("/api/game/{game_id}", self.handle_get_game_api)

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        site = web.TCPSite(self._runner, self.host, self.port)
        await site.start()

        logger.info(f"Chess server started at ws://{self.host}:{self.port}/ws")

    async def stop(self):
        """Stop the server."""
        if self._runner:
            await self._runner.cleanup()
        logger.info("Chess server stopped")

    async def handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint with game list."""
        games_list = [g.to_dict() for g in self.game_manager.games.values()]
        return web.json_response(
            {
                "status": "ok",
                "games_count": len(games_list),
                "games": games_list,
            }
        )

    async def handle_get_game_api(self, request: web.Request) -> web.Response:
        """API endpoint to get game state."""
        game_id = request.match_info.get("game_id")
        game = self.game_manager.get_game(game_id)
        if not game:
            return web.json_response({"error": "Game not found"}, status=404)
        return web.json_response(game.to_dict())

    async def handle_external_move(self, request: web.Request) -> web.Response:
        """API endpoint for external systems (like ANA agent) to apply moves."""
        try:
            data = await request.json()
            game_id = data.get("game_id")
            move_uci = data.get("move")
            explanation = data.get("explanation", "")

            game = self.game_manager.get_game(game_id)
            if not game:
                return web.json_response({"error": "Game not found"}, status=404)

            # Apply move
            result = self.game_manager.make_move(game_id, move_uci)
            if not result["success"]:
                return web.json_response({"error": result["error"]}, status=400)

            # Add chat message if explanation provided
            if explanation:
                self.game_manager.add_chat_message(game_id, "ana", "ANA", explanation)
                # Broadcast chat
                await self._broadcast(
                    game,
                    {
                        "type": "chat",
                        "gameId": game.id,
                        "sender": "ana",
                        "senderName": "ANA",
                        "message": explanation,
                    },
                )

            # Broadcast update to UI
            await self._broadcast_game_state(game, move_result=result)

            return web.json_response({"status": "ok", "result": result})

        except Exception as e:
            logger.error(f"Error in external move: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Handle a new WebSocket connection."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        player_id = str(uuid.uuid4())
        self.connections[player_id] = ws

        logger.info(f"New connection: {player_id}")

        # Send welcome message with player ID
        await self._send(
            ws,
            {
                "type": "connected",
                "playerId": player_id,
            },
        )

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_message(player_id, ws, data)
                    except json.JSONDecodeError:
                        await self._send(
                            ws,
                            {
                                "type": "error",
                                "message": "Invalid JSON",
                            },
                        )
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")

        except Exception as e:
            logger.error(f"Connection error: {e}")

        finally:
            # Cleanup on disconnect
            await self._handle_disconnect(player_id)
            del self.connections[player_id]
            logger.info(f"Connection closed: {player_id}")

        return ws

    async def _handle_message(
        self,
        player_id: str,
        ws: web.WebSocketResponse,
        data: dict[str, Any],
    ):
        """Route incoming messages to handlers."""
        msg_type = data.get("type")

        handlers = {
            "create_game": self._handle_create_game,
            "join_game": self._handle_join_game,
            "move": self._handle_move,
            "resign": self._handle_resign,
            "chat": self._handle_chat,
            "get_game_state": self._handle_get_game_state,
            "request_ana_move": self._handle_request_ana_move,
        }

        handler = handlers.get(msg_type)
        if handler:
            await handler(player_id, ws, data)
        else:
            await self._send(
                ws,
                {
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                },
            )

    async def _handle_create_game(
        self,
        player_id: str,
        ws: web.WebSocketResponse,
        data: dict[str, Any],
    ):
        """Create a new game."""
        player_name = data.get("playerName", "Player")
        player_color = data.get("color", "white")  # white, black, or random
        opponent_type = data.get("opponentType", "ana")  # ana or human
        difficulty = data.get("difficulty", "medium")

        # Create human player
        human_player = Player(
            id=player_id,
            name=player_name,
            type=PlayerType.HUMAN,
            websocket=ws,
        )

        # Determine colors
        if player_color == "random":
            import random

            player_color = random.choice(["white", "black"])

        # Create opponent
        if opponent_type == "ana":
            ana = Player(
                id="ana",
                name="ANA",
                type=PlayerType.ANA,
            )
            if player_color == "white":
                white, black = human_player, ana
            else:
                white, black = ana, human_player
        else:
            # Human vs Human - waiting for opponent
            if player_color == "white":
                white = human_player
                black = Player(id="", name="Waiting...", type=PlayerType.HUMAN)
            else:
                white = Player(id="", name="Waiting...", type=PlayerType.HUMAN)
                black = human_player

        game = self.game_manager.create_game(white, black, difficulty)
        self.player_games[player_id] = game.id

        # If waiting for human opponent, set status
        if opponent_type == "human" and (not white.id or not black.id):
            game.status = GameStatus.WAITING

        await self._send(
            ws,
            {
                "type": "game_created",
                "game": game.to_dict(),
                "yourColor": player_color,
            },
        )

        # If it's ANA's turn (playing white), trigger ANA's move
        if game.is_ana_turn and game.status == GameStatus.ACTIVE:
            asyncio.create_task(self._trigger_ana_move(game))

    async def _handle_join_game(
        self,
        player_id: str,
        ws: web.WebSocketResponse,
        data: dict[str, Any],
    ):
        """Join an existing game."""
        game_id = data.get("gameId")
        player_name = data.get("playerName", "Player 2")

        game = self.game_manager.get_game(game_id)
        if not game:
            await self._send(
                ws,
                {
                    "type": "error",
                    "message": "Game not found",
                },
            )
            return

        if game.status != GameStatus.WAITING:
            await self._send(
                ws,
                {
                    "type": "error",
                    "message": "Game is not accepting players",
                },
            )
            return

        # Fill in empty slot
        joining_player = Player(
            id=player_id,
            name=player_name,
            type=PlayerType.HUMAN,
            websocket=ws,
        )

        if not game.white.id:
            game.white = joining_player
            your_color = "white"
        else:
            game.black = joining_player
            your_color = "black"

        game.status = GameStatus.ACTIVE
        self.player_games[player_id] = game.id

        # Notify joiner
        await self._send(
            ws,
            {
                "type": "game_joined",
                "game": game.to_dict(),
                "yourColor": your_color,
            },
        )

        # Notify other player
        await self._broadcast_game_state(game)

    async def _handle_move(
        self,
        player_id: str,
        ws: web.WebSocketResponse,
        data: dict[str, Any],
    ):
        """Handle a player's move."""
        game_id = self.player_games.get(player_id)
        if not game_id:
            await self._send(ws, {"type": "error", "message": "Not in a game"})
            return

        game = self.game_manager.get_game(game_id)
        if not game:
            await self._send(ws, {"type": "error", "message": "Game not found"})
            return

        # Verify it's this player's turn
        current_turn = self.game_manager.get_current_turn(game_id)
        player_color = "white" if game.white.id == player_id else "black"

        if current_turn != player_color:
            await self._send(ws, {"type": "error", "message": "Not your turn"})
            return

        # Make the move
        move_uci = data.get("move")
        result = self.game_manager.make_move(game_id, move_uci)

        if not result["success"]:
            await self._send(
                ws,
                {
                    "type": "move_error",
                    "error": result["error"],
                },
            )
            return

        # Broadcast updated state
        await self._broadcast_game_state(game, move_result=result)

        # If game continues and it's now ANA's turn, trigger ANA
        if not result.get("game_over") and game.is_ana_turn:
            asyncio.create_task(self._trigger_ana_move(game))

    async def _trigger_ana_move(self, game: Game):
        """Trigger ANA to make a move."""
        # Small delay before ANA starts thinking (more natural)
        await asyncio.sleep(0.5)

        # Notify players ANA is thinking
        await self._broadcast(
            game,
            {
                "type": "ana_thinking",
                "gameId": game.id,
            },
        )

        # Get ANA's move
        result = await self.ana_player.get_move(game)

        if result["success"]:
            # Make the move on the board
            move_result = self.game_manager.make_move(game.id, result["move"])

            if move_result["success"]:
                # Add ANA's explanation as a chat message
                self.game_manager.add_chat_message(
                    game.id,
                    "ana",
                    "ANA",
                    result["explanation"],
                )

                # Broadcast updated state
                await self._broadcast_game_state(game, move_result=move_result)

                # Also broadcast the chat message
                await self._broadcast(
                    game,
                    {
                        "type": "chat",
                        "gameId": game.id,
                        "sender": "ana",
                        "senderName": "ANA",
                        "message": result["explanation"],
                    },
                )
            else:
                logger.error(f"ANA's move failed validation: {move_result['error']}")
        else:
            logger.error(f"ANA failed to generate move: {result.get('error')}")

    async def _handle_resign(
        self,
        player_id: str,
        ws: web.WebSocketResponse,
        data: dict[str, Any],
    ):
        """Handle player resignation."""
        game_id = self.player_games.get(player_id)
        if not game_id:
            return

        result = self.game_manager.resign(game_id, player_id)
        if result["success"]:
            game = self.game_manager.get_game(game_id)
            if game:
                await self._broadcast_game_state(game)

    async def _handle_chat(
        self,
        player_id: str,
        ws: web.WebSocketResponse,
        data: dict[str, Any],
    ):
        """Handle chat message."""
        game_id = self.player_games.get(player_id)
        if not game_id:
            return

        game = self.game_manager.get_game(game_id)
        if not game:
            return

        message = data.get("message", "").strip()
        if not message:
            return

        # Get player name
        if game.white.id == player_id:
            sender_name = game.white.name
        elif game.black.id == player_id:
            sender_name = game.black.name
        else:
            sender_name = "Unknown"

        self.game_manager.add_chat_message(game_id, player_id, sender_name, message)

        await self._broadcast(
            game,
            {
                "type": "chat",
                "gameId": game_id,
                "sender": player_id,
                "senderName": sender_name,
                "message": message,
            },
        )

    async def _handle_get_game_state(
        self,
        player_id: str,
        ws: web.WebSocketResponse,
        data: dict[str, Any],
    ):
        """Get current game state."""
        game_id = self.player_games.get(player_id) or data.get("gameId")
        if not game_id:
            await self._send(ws, {"type": "error", "message": "No game specified"})
            return

        game = self.game_manager.get_game(game_id)
        if not game:
            await self._send(ws, {"type": "error", "message": "Game not found"})
            return

        await self._send(
            ws,
            {
                "type": "game_state",
                "game": game.to_dict(),
            },
        )

    async def _handle_request_ana_move(
        self,
        player_id: str,
        ws: web.WebSocketResponse,
        data: dict[str, Any],
    ):
        """Request ANA to make a move for the human player (Ghost Mode)."""
        game_id = self.player_games.get(player_id)
        if not game_id:
            return

        game = self.game_manager.get_game(game_id)
        if not game:
            return

        # Verify turn
        current_turn = self.game_manager.get_current_turn(game_id)
        player_color = "white" if game.white.id == player_id else "black"

        if current_turn != player_color:
            return  # Not your turn

        # Notify requester ONLY that ANA is thinking
        await self._send(ws, {"type": "ana_thinking_local"})

        # Get ANA's move
        result = await self.ana_player.get_move(game, player_color=player_color)

        if result["success"]:
            # Make the move on the board
            move_result = self.game_manager.make_move(game.id, result["move"])

            if move_result["success"]:
                # Broadcast updated state (Look like a normal move)
                await self._broadcast_game_state(game, move_result=move_result)

                # Send explanation ONLY to requester
                await self._send(
                    ws,
                    {
                        "type": "chat",
                        "sender": "ana_ghost",
                        "senderName": "Assistant",
                        "message": result["explanation"],
                    },
                )
            else:
                await self._send(
                    ws,
                    {
                        "type": "error",
                        "message": f"ANA invalid move: {move_result['error']}",
                    },
                )
        else:
            await self._send(
                ws, {"type": "error", "message": "ANA failed to find move"}
            )

    async def _handle_disconnect(self, player_id: str):
        """Handle player disconnect."""
        game_id = self.player_games.get(player_id)
        if game_id:
            game = self.game_manager.get_game(game_id)
            if game and game.status == GameStatus.ACTIVE:
                # For now, abandon the game
                self.game_manager.abandon_game(game_id)
                await self._broadcast(
                    game,
                    {
                        "type": "player_disconnected",
                        "gameId": game_id,
                        "playerId": player_id,
                    },
                )
            del self.player_games[player_id]

    async def _broadcast_game_state(
        self,
        game: Game,
        move_result: dict | None = None,
    ):
        """Broadcast game state to all players in a game."""
        message = {
            "type": "game_state",
            "game": game.to_dict(),
        }

        if move_result:
            message["lastMove"] = {
                "move": move_result.get("move"),
                "san": move_result.get("san"),
                "check": move_result.get("check", False),
            }
            if move_result.get("game_over"):
                message["gameOver"] = True
                message["result"] = move_result.get("result")

        await self._broadcast(game, message)

    async def _broadcast(self, game: Game, message: dict):
        """Send message to all players in a game."""
        for player in [game.white, game.black]:
            if player.type == PlayerType.HUMAN and player.id:
                ws = self.connections.get(player.id)
                if ws and not ws.closed:
                    await self._send(ws, message)

    async def _send(self, ws: web.WebSocketResponse, message: dict):
        """Send a JSON message to a WebSocket."""
        try:
            await ws.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")


async def run_server(host: str = "localhost", port: int = 8765):
    """Run the chess server."""
    server = ChessServer(host, port)
    await server.start()

    # Keep running until interrupted
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await server.stop()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(run_server())
