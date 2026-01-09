"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Chess } from "chess.js";
import type { Square } from "chess.js";
import { Chessboard } from "react-chessboard";
import { ChatPanel } from "./ChatPanel";
import { GameControls } from "./GameControls";

interface GameState {
  id: string;
  white: { id: string; name: string; type: string };
  black: { id: string; name: string; type: string };
  fen: string;
  moves: string[];
  status: string;
  winner: string | null;
  difficulty: string;
}

interface ChatMessage {
  sender: string;
  senderName: string;
  message: string;
  timestamp: number;
}

interface WebSocketMessage {
  type: string;
  game?: GameState;
  yourColor?: string;
  playerId?: string;
  lastMove?: { move: string; san: string; check: boolean };
  gameOver?: boolean;
  result?: string;
  message?: string;
  sender?: string;
  senderName?: string;
  error?: string;
}

export function ChessGame() {
  const [game, setGame] = useState<Chess>(new Chess());
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [playerColor, setPlayerColor] = useState<"white" | "black">("white");
  const [playerId, setPlayerId] = useState<string>("");
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isHost, setIsHost] = useState(false);
  const [isAnaThinking, setIsAnaThinking] = useState(false);
  const [isAutoPlayEnabled, setIsAutoPlayEnabled] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [gameResult, setGameResult] = useState<string | null>(null);
  const [boardOrientation, setBoardOrientation] =
    useState<"white" | "black">("white");

  const wsRef = useRef<WebSocket | null>(null);

  // Connect to WebSocket server
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    // Get WebSocket URL from environment variable, query param, or default to localhost
    const urlParams = new URLSearchParams(window.location.search);
    const overrideWsUrl = urlParams.get("wsUrl");
    
    let wsUrl = overrideWsUrl || process.env.NEXT_PUBLIC_CHESS_WS_URL || "ws://localhost:8765/ws";
    
    // If we're on a secure connection (like ngrok/production), use wss://
    if (window.location.protocol === "https:" && wsUrl.startsWith("ws://")) {
      wsUrl = wsUrl.replace("ws://", "wss://");
    }

    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      setIsConnected(true);
      console.log("Connected to chess server");
    };

    socket.onclose = () => {
      setIsConnected(false);
      console.log("Disconnected from chess server");
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    socket.onmessage = (event) => {
      const data: WebSocketMessage = JSON.parse(event.data);
      handleMessage(data);
    };

    wsRef.current = socket;
    setWs(socket);
  }, []);

  // Handle incoming messages
  const handleMessage = useCallback((data: WebSocketMessage) => {
    switch (data.type) {
      case "connected":
        if (data.playerId) {
          setPlayerId(data.playerId);
        }
        break;

      case "game_created":
      case "game_joined":
      case "game_state":
        if (data.game) {
          setGameState(data.game);
          const newGame = new Chess(data.game.fen);
          setGame(newGame);

          if (data.yourColor) {
            setPlayerColor(data.yourColor as "white" | "black");
            setBoardOrientation(data.yourColor as "white" | "black");
          }

          if (data.gameOver && data.result) {
            setGameResult(data.result);
          }
        }
        break;

      case "ana_thinking":
        // Only show if we are in practice mode or it's relevant
        // But user asked to remove ANA indicators for opponent.
        // We will keep state but maybe not show text or show distinct text
        setIsAnaThinking(true);
        break;

      case "ana_thinking_local":
        setIsAnaThinking(true);
        break;

      case "chat":
        if (data.sender && data.senderName && data.message) {
          setIsAnaThinking(false);
          // If sender is ANA Ghost, we can show it as "Assistant" or similar
          // The server already sends "Assistant" as senderName for ghost
          setMessages((prev) => [
            ...prev,
            {
              sender: data.sender!,
              senderName: data.senderName!,
              message: data.message!,
              timestamp: Date.now(),
            },
          ]);
        }
        break;

      case "move_error":
        console.error("Move error:", data.error);
        break;

      case "error":
        console.error("Server error:", data.message);
        break;
    }
  }, []);

  // Connect on mount
  useEffect(() => {
    connect();

    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  // Handle piece drop
  const onDrop = useCallback(
    (sourceSquare: Square, targetSquare: Square): boolean => {
      if (!gameState || gameState.status !== "active") return false;

      // Check if it's our turn
      const isWhiteTurn = game.turn() === "w";
      if (
        (isWhiteTurn && playerColor !== "white") ||
        (!isWhiteTurn && playerColor !== "black")
      ) {
        return false;
      }

      // Try to make the move locally first for validation
      const gameCopy = new Chess(game.fen());
      try {
        const move = gameCopy.move({
          from: sourceSquare,
          to: targetSquare,
          promotion: "q", // Always promote to queen for simplicity
        });

        if (!move) return false;

        // Send move to server
        wsRef.current?.send(
          JSON.stringify({
            type: "move",
            move: sourceSquare + targetSquare + (move.promotion || ""),
          })
        );

        return true;
      } catch {
        return false;
      }
    },
    [game, gameState, playerColor]
  );

  // Start a new game
  const startGame = useCallback(
    (
      opponentType: "ana" | "human",
      color: "white" | "black" | "random",
      difficulty: string
    ) => {
      setGameResult(null);
      setMessages([]);

      wsRef.current?.send(
        JSON.stringify({
          type: "create_game",
          playerName: "Player",
          color,
          opponentType,
          difficulty,
        })
      );
      
      // If we create the game, we are the host.
      setIsHost(true);
      setIsAutoPlayEnabled(false);
    },
    []
  );

  // Join an existing game
  const joinGame = useCallback((gameId: string) => {
    setGameResult(null);
    setMessages([]);

    wsRef.current?.send(
      JSON.stringify({
        type: "join_game",
        gameId,
        playerName: "Player 2",
      })
    );

    // If we join a game, we are NOT the host.
    setIsHost(false);
    setIsAutoPlayEnabled(false);
  }, []);

  // Send chat message
  const sendMessage = useCallback((message: string) => {
    wsRef.current?.send(
      JSON.stringify({
        type: "chat",
        message,
      })
    );
  }, []);

  // Resign the game
  const resign = useCallback(() => {
    wsRef.current?.send(
      JSON.stringify({
        type: "resign",
      })
    );
  }, []);

  // Get current turn info
  const getCurrentTurn = (): string => {
    if (!gameState) return "";
    const isWhiteTurn = game.turn() === "w";
    if (isWhiteTurn) {
      return `${gameState.white.name}'s turn`;
    }
    return `${gameState.black.name}'s turn`;
  };

  // Check if it's player's turn
  const isMyTurn = (): boolean => {
    if (!gameState || gameState.status !== "active") return false;
    const isWhiteTurn = game.turn() === "w";
    return (
      (isWhiteTurn && playerColor === "white") ||
      (!isWhiteTurn && playerColor === "black")
    );
  };

  // Auto-Play Logic
  useEffect(() => {
    if (isAutoPlayEnabled && isMyTurn() && !isAnaThinking && !gameResult) {
      // Small delay for natural feel
      const timer = setTimeout(() => {
        wsRef.current?.send(
          JSON.stringify({
            type: "request_ana_move",
          })
        );
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [isAutoPlayEnabled, gameState, game, playerColor, isAnaThinking, gameResult]); // Dependencies that define "My Turn" and "State"

  return (
    <div className="flex flex-col lg:flex-row min-h-screen p-4 lg:p-8 gap-6">
      {/* Left side - Game Controls */}
      <div className="lg:w-64 flex-shrink-0">
        <GameControls
          isConnected={isConnected}
          gameState={gameState}
          onStartGame={startGame}
          onResign={resign}
          playerColor={playerColor}
          isAutoPlayEnabled={isAutoPlayEnabled}
          onToggleAutoPlay={setIsAutoPlayEnabled}
          gameId={gameState?.id || null}
          isHost={isHost}
          onJoinGame={joinGame}
        />
      </div>

      {/* Center - Chessboard */}
      <div className="flex-1 flex flex-col items-center justify-center">
        {/* Game status */}
        <div className="mb-4 text-center">
          {!isConnected && (
            <div className="text-red-400 mb-2">
              ⚠️ Not connected to server. Make sure the chess server is running.
            </div>
          )}

          {gameState && (
            <div className="space-y-2">
              <div className="text-white text-lg font-semibold">
                {gameState.white.name} vs {gameState.black.name}
              </div>
              <div className="text-slate-300">
                {gameResult || getCurrentTurn()}
                {isAnaThinking && (
                  <span className="ml-2 text-cyan-400 animate-pulse">
                    Thinking...
                  </span>
                )}
              </div>
              {isMyTurn() && !gameResult && (
                <div className="text-green-400 text-sm">Your turn!</div>
              )}
            </div>
          )}

          {!gameState && isConnected && (
            <div className="text-slate-400">
              Click &quot;New Game&quot; to start playing
            </div>
          )}
        </div>

        {/* Chessboard */}
        <div
          className="w-full max-w-[600px] aspect-square rounded-lg overflow-hidden shadow-2xl"
          style={{
            boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
          }}
        >
          <Chessboard
            options={{
              position: game.fen(),
              onPieceDrop: ({ sourceSquare, targetSquare }) =>
                onDrop(sourceSquare as Square, targetSquare as Square),
              boardOrientation: boardOrientation,
              boardStyle: {
                borderRadius: "8px",
              },
              darkSquareStyle: {
                backgroundColor: "#4a5568",
              },
              lightSquareStyle: {
                backgroundColor: "#a0aec0",
              },
              allowDragging: isMyTurn() && !gameResult,
            }}
          />
        </div>

        {/* Move history */}
        {gameState && gameState.moves.length > 0 && (
          <div className="mt-4 p-3 bg-slate-800/50 rounded-lg max-w-[600px] w-full">
            <div className="text-slate-400 text-sm mb-1">Move History</div>
            <div className="text-slate-200 text-sm flex flex-wrap gap-1">
              {gameState.moves.map((move, index) => (
                <span
                  key={index}
                  className="px-2 py-0.5 bg-slate-700/50 rounded"
                >
                  {index % 2 === 0 && (
                    <span className="text-slate-500 mr-1">
                      {Math.floor(index / 2) + 1}.
                    </span>
                  )}
                  {move}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Right side - Chat */}
      <div className="lg:w-80 flex-shrink-0">
        <ChatPanel
          messages={messages}
          onSendMessage={sendMessage}
          isAnaThinking={isAnaThinking}
          disabled={!gameState}
        />
      </div>
    </div>
  );
}
