"use client";

import { useState, useRef, useEffect } from "react";

interface ChatMessage {
  sender: string;
  senderName: string;
  message: string;
  timestamp: number;
}

interface ChatPanelProps {
  messages: ChatMessage[];
  onSendMessage: (message: string) => void;
  isAnaThinking: boolean;
  disabled: boolean;
}

export function ChatPanel({
  messages,
  onSendMessage,
  isAnaThinking,
  disabled,
}: ChatPanelProps) {
  const [inputValue, setInputValue] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() && !disabled) {
      onSendMessage(inputValue.trim());
      setInputValue("");
    }
  };

  return (
    <div className="h-full flex flex-col bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-700/50">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <span className="text-2xl">💬</span>
          Game Chat
        </h3>
        <p className="text-sm text-slate-400 mt-1">
          Chat and commentary
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[300px] max-h-[500px]">
        {messages.length === 0 && !isAnaThinking && (
          <div className="text-slate-500 text-center text-sm py-8">
            No messages yet. Start a game to chat!
          </div>
        )}

        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex flex-col ${
              msg.sender === "ana" || msg.sender === "ana_ghost"
                ? "items-start"
                : "items-end"
            }`}
          >
            <div className="text-xs text-slate-500 mb-1">
              {msg.senderName}
            </div>
            <div
              className={`max-w-[90%] p-3 rounded-lg ${
                msg.sender === "ana" || msg.sender === "ana_ghost"
                  ? "bg-gradient-to-br from-cyan-600/30 to-blue-600/30 border border-cyan-500/30 text-cyan-100"
                  : "bg-slate-700 text-slate-200"
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.message}</p>
            </div>
          </div>
        ))}

        {isAnaThinking && (
          <div className="flex flex-col items-start">
            <div className="text-xs text-slate-500 mb-1">...</div>
            <div className="bg-gradient-to-br from-cyan-600/30 to-blue-600/30 border border-cyan-500/30 p-3 rounded-lg">
              <div className="flex items-center gap-2 text-cyan-300">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></span>
                  <span className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></span>
                  <span className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></span>
                </div>
                <span className="text-sm">Thinking...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-slate-700/50">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={disabled ? "Start a game to chat..." : "Type a message..."}
            disabled={disabled}
            className="flex-1 px-4 py-2 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={disabled || !inputValue.trim()}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
