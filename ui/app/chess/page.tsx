"use client";

import { ChessGame } from "@/components/chess/ChessGame";

export default function ChessPage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <ChessGame />
    </main>
  );
}
