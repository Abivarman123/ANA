"use client";

import { useState } from "react";

interface GameState {
  id: string;
  status: string;
  difficulty: string;
}

interface GameControlsProps {
  isConnected: boolean;
  gameState: GameState | null;
  onStartGame: (
    opponentType: "ana" | "human",
    color: "white" | "black" | "random",
    difficulty: string
  ) => void;
  onResign: () => void;
  playerColor: "white" | "black";
  isAutoPlayEnabled: boolean;
  onToggleAutoPlay: (enabled: boolean) => void;
  gameId: string | null;
  isHost: boolean;
  onJoinGame: (gameId: string) => void;
}

export function GameControls({
  isConnected,
  gameState,
  onStartGame,
  onResign,
  playerColor,
  isAutoPlayEnabled,
  onToggleAutoPlay,
  gameId,
  isHost,
  onJoinGame,
}: GameControlsProps) {
  const [showNewGameModal, setShowNewGameModal] = useState(false);
  const [showJoinGameModal, setShowJoinGameModal] = useState(false);
  const [joinGameIdInput, setJoinGameIdInput] = useState("");
  const [selectedOpponent, setSelectedOpponent] = useState<"ana" | "human">("ana");
  const [selectedColor, setSelectedColor] = useState<"white" | "black" | "random">("white");
  const [selectedDifficulty, setSelectedDifficulty] = useState("medium");

  const handleStartGame = () => {
    onStartGame(selectedOpponent, selectedColor, selectedDifficulty);
    setShowNewGameModal(false);
  };

  return (
    <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-4 space-y-4">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-xl font-bold text-white flex items-center justify-center gap-2">
          <span className="text-2xl">♟️</span>
          Chess
        </h2>
        <p className="text-sm text-slate-400 mt-1">
          Play a classic game of Chess
        </p>
      </div>

      {/* Connection Status */}
      <div className="flex items-center gap-2 text-sm">
        <div
          className={`w-2 h-2 rounded-full ${
            isConnected ? "bg-green-500" : "bg-red-500"
          }`}
        />
        <span className={isConnected ? "text-green-400" : "text-red-400"}>
          {isConnected ? "Connected" : "Disconnected"}
        </span>
      </div>

      {/* Game Info */}
      {gameState && (
        <div className="p-3 bg-slate-700/30 rounded-lg space-y-2">
          <div className="text-sm text-slate-300">
            <span className="text-slate-500">Playing as:</span>{" "}
            <span className="font-medium capitalize">{playerColor}</span>
          </div>
          <div className="text-sm text-slate-300">
            <span className="text-slate-500">Status:</span>{" "}
            <span className="font-medium capitalize">{gameState.status}</span>
          </div>
          <div className="text-sm text-slate-300">
            <span className="text-slate-500">Difficulty:</span>{" "}
            <span className="font-medium capitalize">{gameState.difficulty}</span>
          </div>
        </div>
      )}

      {/* Game Code Display (For Host) */}
      {gameId && isHost && gameState?.status === "waiting" && (
        <div className="p-4 bg-gradient-to-r from-indigo-900/50 to-purple-900/50 rounded-lg border border-indigo-500/30 text-center animate-pulse">
          <div className="text-xs text-indigo-300 uppercase tracking-wider font-bold mb-1">
            Share Game Code
          </div>
          <div className="text-xl font-mono font-bold text-white tracking-widest select-all cursor-pointer bg-black/20 rounded py-1"
               onClick={() => navigator.clipboard.writeText(gameId)}>
            {gameId.slice(0, 8)}...
          </div>
          <div className="text-[10px] text-indigo-400 mt-1">
            Click to copy full ID
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="space-y-2">
        <button
          onClick={() => setShowNewGameModal(true)}
          disabled={!isConnected || (!!gameState && gameState.status === "active")}
          className="w-full py-2.5 px-4 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 disabled:from-slate-600 disabled:to-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-all font-medium shadow-lg shadow-cyan-500/20"
        >
          🎮 New Game
        </button>

        {!gameState && (
          <button
            onClick={() => setShowJoinGameModal(true)}
            disabled={!isConnected}
            className="w-full py-2.5 px-4 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg transition-colors font-medium border border-slate-600"
          >
            ↪️ Join Game
          </button>
        )}

        {gameState && gameState.status === "active" && (
          <button
            onClick={onResign}
            className="w-full py-2 px-4 bg-red-600/20 hover:bg-red-600/30 border border-red-500/30 text-red-400 rounded-lg transition-colors font-medium"
          >
            🏳️ Resign
          </button>
        )}

        {/* Secret/Private Auto-Assist Toggle - HOST ONLY */}
        {gameState && gameState.status === "active" && isHost && (
          <button
            onClick={() => onToggleAutoPlay(!isAutoPlayEnabled)}
            className={`w-full py-2 px-4 rounded-lg transition-colors font-medium border ${
              isAutoPlayEnabled
                ? "bg-purple-600/20 border-purple-500 text-purple-300"
                : "bg-slate-700/30 border-slate-600 text-slate-400"
            }`}
          >
            {isAutoPlayEnabled ? "🔮 Auto-Pilot ON" : "⚪ Auto-Pilot OFF"}
          </button>
        )}
      </div>

      {/* How to Play */}
      <div className="pt-4 border-t border-slate-700/50">
        <h4 className="text-sm font-semibold text-slate-300 mb-2">How to Play</h4>
        <ul className="text-xs text-slate-400 space-y-1">
          <li>• Drag pieces to make moves</li>
          <li>• Assistant can explain moves</li>
          <li>• Use Auto-Pilot for assistance</li>
        </ul>
      </div>

      {/* New Game Modal */}
      {showNewGameModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 rounded-2xl border border-slate-700 p-6 w-full max-w-md shadow-2xl">
            <h3 className="text-xl font-bold text-white mb-6">New Game</h3>

            {/* Opponent Selection */}
            <div className="mb-5">
              <label className="text-sm font-medium text-slate-400 mb-3 block">Opponent</label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => setSelectedOpponent("ana")}
                  className={`py-3 px-4 rounded-xl border-2 transition-all flex flex-col items-center gap-1 ${
                    selectedOpponent === "ana"
                      ? "bg-cyan-500/20 border-cyan-500 text-cyan-300 shadow-lg shadow-cyan-500/20"
                      : "bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600 hover:text-slate-300"
                  }`}
                >
                  <span className="text-2xl">🤖</span>
                  <span className="font-medium">Practice</span>
                </button>
                <button
                  onClick={() => setSelectedOpponent("human")}
                  className={`py-3 px-4 rounded-xl border-2 transition-all flex flex-col items-center gap-1 ${
                    selectedOpponent === "human"
                      ? "bg-cyan-500/20 border-cyan-500 text-cyan-300 shadow-lg shadow-cyan-500/20"
                      : "bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600 hover:text-slate-300"
                  }`}
                >
                  <span className="text-2xl">👤</span>
                  <span className="font-medium">vs Human</span>
                </button>
              </div>
            </div>

            {/* Color Selection */}
            <div className="mb-5">
              <label className="text-sm font-medium text-slate-400 mb-3 block">Your Color</label>
              <div className="grid grid-cols-3 gap-3">
                {([["white", "⬜", "White"], ["black", "⬛", "Black"], ["random", "🎲", "Random"]] as const).map(([value, icon, label]) => (
                  <button
                    key={value}
                    onClick={() => setSelectedColor(value as "white" | "black" | "random")}
                    className={`py-3 px-2 rounded-xl border-2 transition-all flex flex-col items-center gap-1 ${
                      selectedColor === value
                        ? "bg-cyan-500/20 border-cyan-500 text-cyan-300 shadow-lg shadow-cyan-500/20"
                        : "bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600 hover:text-slate-300"
                    }`}
                  >
                    <span className="text-xl">{icon}</span>
                    <span className="text-sm font-medium">{label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Difficulty (only for ANA) */}
            {selectedOpponent === "ana" && (
              <div className="mb-6">
                <label className="text-sm font-medium text-slate-400 mb-3 block">Difficulty</label>
                <div className="grid grid-cols-3 gap-3">
                  {([["easy", "😊", "Easy"], ["medium", "🧠", "Medium"], ["hard", "🔥", "Hard"]] as const).map(([value, icon, label]) => (
                    <button
                      key={value}
                      onClick={() => setSelectedDifficulty(value)}
                      className={`py-3 px-2 rounded-xl border-2 transition-all flex flex-col items-center gap-1 ${
                        selectedDifficulty === value
                          ? "bg-cyan-500/20 border-cyan-500 text-cyan-300 shadow-lg shadow-cyan-500/20"
                          : "bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600 hover:text-slate-300"
                      }`}
                    >
                      <span className="text-xl">{icon}</span>
                      <span className="text-sm font-medium">{label}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Modal Actions */}
            <div className="flex gap-3 pt-2">
              <button
                onClick={() => setShowNewGameModal(false)}
                className="flex-1 py-3 px-4 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 rounded-xl transition-colors font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleStartGame}
                className="flex-1 py-3 px-4 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-xl transition-all font-semibold shadow-lg shadow-cyan-500/30"
              >
                Start Game
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Join Game Modal */}
      {showJoinGameModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 rounded-2xl border border-slate-700 p-6 w-full max-w-md shadow-2xl">
            <h3 className="text-xl font-bold text-white mb-6">Join Game</h3>
            
            <div className="mb-6">
              <label className="text-sm font-medium text-slate-400 mb-2 block">Game Code</label>
              <input
                type="text"
                value={joinGameIdInput}
                onChange={(e) => setJoinGameIdInput(e.target.value)}
                placeholder="Paste code here..."
                className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500"
              />
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setShowJoinGameModal(false)}
                className="flex-1 py-3 px-4 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 rounded-xl transition-colors font-medium"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  onJoinGame(joinGameIdInput);
                  setShowJoinGameModal(false);
                }}
                disabled={!joinGameIdInput.trim()}
                className="flex-1 py-3 px-4 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl transition-all font-semibold shadow-lg shadow-cyan-500/30"
              >
                Join Game
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
