'use client';

import { useSessionInfo } from '@/hooks/useSessionInfo';
import { cn } from '@/lib/utils';

interface SessionInfoProps {
  className?: string;
}

function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

export function SessionInfo({ className }: SessionInfoProps) {
  const {
    sessionDuration,
    isGenerating,
    isAgentSpeaking,
    isAgentThinking,
    isListening,
    isTurnComplete,
  } = useSessionInfo();

  if (sessionDuration === 0) return null;

  return (
    <div
      className={cn('text-muted-foreground flex items-center gap-3 font-mono text-xs', className)}
    >
      {/* Session Timer */}
      <div className="flex items-center gap-1.5">
        <div className="h-1.5 w-1.5 rounded-full bg-green-500" />
        <span>{formatDuration(sessionDuration)}</span>
      </div>

      {/* Agent Status */}
      {isAgentThinking && (
        <div className="flex items-center gap-1.5">
          <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-yellow-500" />
          <span>Thinking</span>
        </div>
      )}

      {isAgentSpeaking && (
        <div className="flex items-center gap-1.5">
          <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-blue-500" />
          <span>Speaking</span>
        </div>
      )}

      {isListening && !isGenerating && (
        <div className="flex items-center gap-1.5">
          <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          <span>Listening</span>
        </div>
      )}

      {isTurnComplete && !isGenerating && !isListening && (
        <div className="flex items-center gap-1.5">
          <div className="h-1.5 w-1.5 rounded-full bg-gray-500" />
          <span>Ready</span>
        </div>
      )}
    </div>
  );
}
