'use client';

import { useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { useRoomContext } from '@livekit/components-react';
import { Gear } from '@phosphor-icons/react/dist/ssr';
import { useSession } from '@/components/app/session-provider';
import { SessionView } from '@/components/app/session-view';
import { SettingsModal } from '@/components/app/settings-modal';
import { WelcomeView } from '@/components/app/welcome-view';
import { Button } from '@/components/livekit/button';

const MotionWelcomeView = motion.create(WelcomeView);
const MotionSessionView = motion.create(SessionView);

const VIEW_MOTION_PROPS = {
  variants: {
    visible: {
      opacity: 1,
    },
    hidden: {
      opacity: 0,
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.5,
    ease: 'linear',
  },
} as const;

export function ViewController() {
  const room = useRoomContext();
  const isSessionActiveRef = useRef(false);
  const { appConfig, isSessionActive, startSession } = useSession();
  const [showSettings, setShowSettings] = useState(false);

  // animation handler holds a reference to stale isSessionActive value
  isSessionActiveRef.current = isSessionActive;

  // disconnect room after animation completes
  const handleAnimationComplete = () => {
    if (!isSessionActiveRef.current && room.state !== 'disconnected') {
      room.disconnect();
    }
  };

  return (
    <>
      <div className="absolute top-4 right-4 z-50">
        <Button variant="ghost" size="icon" onClick={() => setShowSettings(true)}>
          <Gear className="size-6" />
        </Button>
      </div>

      <SettingsModal isOpen={showSettings} onClose={() => setShowSettings(false)} />

      <AnimatePresence mode="wait">
        {/* Welcome screen */}
        {!isSessionActive && (
          <MotionWelcomeView
            key="welcome"
            {...VIEW_MOTION_PROPS}
            startButtonText={appConfig.startButtonText}
            onStartCall={startSession}
          />
        )}
        {/* Session view */}
        {isSessionActive && (
          <MotionSessionView
            key="session-view"
            {...VIEW_MOTION_PROPS}
            appConfig={appConfig}
            onAnimationComplete={handleAnimationComplete}
          />
        )}
      </AnimatePresence>
    </>
  );
}
