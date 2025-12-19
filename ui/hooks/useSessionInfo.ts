import { useEffect, useState } from 'react';
import { type AgentState, useVoiceAssistant } from '@livekit/components-react';
import { useSession } from '@/components/app/session-provider';

export interface SessionInfo {
  sessionDuration: number;
  isGenerating: boolean;
  isAgentSpeaking: boolean;
  isAgentThinking: boolean;
  isListening: boolean;
  isTurnComplete: boolean;
  agentState: AgentState;
}

export function useSessionInfo(): SessionInfo {
  const { isSessionActive } = useSession();
  const { state } = useVoiceAssistant();
  const [sessionDuration, setSessionDuration] = useState(0);
  const [startTime, setStartTime] = useState<number | null>(null);

  // Track session start time
  useEffect(() => {
    if (isSessionActive && startTime === null) {
      setStartTime(Date.now());
    } else if (!isSessionActive) {
      setStartTime(null);
      setSessionDuration(0);
    }
  }, [isSessionActive, startTime]);

  // Update session duration every second
  useEffect(() => {
    if (!isSessionActive || startTime === null) return;

    const interval = setInterval(() => {
      setSessionDuration(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    return () => clearInterval(interval);
  }, [isSessionActive, startTime]);

  // Map voice assistant states to detailed info
  // AgentState: 'disconnected' | 'connecting' | 'initializing' | 'listening' | 'thinking' | 'speaking'
  const isAgentThinking = state === 'thinking';
  const isAgentSpeaking = state === 'speaking';
  const isListening = state === 'listening';
  const isGenerating = isAgentThinking || isAgentSpeaking;
  // Turn is complete when agent is listening (ready for input) or not generating
  const isTurnComplete =
    isListening || (!isGenerating && state !== 'disconnected' && state !== 'connecting');

  return {
    sessionDuration,
    isGenerating,
    isAgentSpeaking,
    isAgentThinking,
    isListening,
    isTurnComplete,
    agentState: state,
  };
}
