'use client';

import dynamic from 'next/dynamic';
import { AnimatePresence, motion } from 'motion/react';
import { useVoiceAssistant } from '@livekit/components-react';
import { cn } from '@/lib/utils';

const MotionDiv = motion.create('div');

// Dynamically import the heavy 3D scene — disables SSR for it
const VRMAvatarScene = dynamic(() => import('./vrm-avatar-scene'), {
  ssr: false,
});

interface VRMAvatarProps {
  visible: boolean;
  modelPath?: string;
}

export function VRMAvatar({ visible, modelPath = '/models/avatar.vrm' }: VRMAvatarProps) {
  const { audioTrack: agentAudioTrack } = useVoiceAssistant();

  return (
    <AnimatePresence>
      {visible && (
        <MotionDiv
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.8 }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
          className="pointer-events-auto fixed inset-0 z-[60] flex items-center justify-center"
        >
          <div className="relative h-[80vh] w-[80vw] max-w-4xl">
            <div className={cn('h-full w-full rounded-xl bg-black/20 shadow-2xl backdrop-blur-sm')}>
              <VRMAvatarScene modelPath={modelPath} audioTrack={agentAudioTrack} />
            </div>
          </div>
        </MotionDiv>
      )}
    </AnimatePresence>
  );
}
