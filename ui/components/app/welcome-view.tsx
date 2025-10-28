import Image from 'next/image';
import { Button } from '@/components/livekit/button';

function WelcomeImage() {
  return (
    <Image
      src="/ana.png"
      alt="ANA Logo"
      width="256"
      height="256"
      className="text-fg0 mb-4 size-16"
    />
  );
}

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  return (
    <div ref={ref}>
      <section className="bg-background flex flex-col items-center justify-center text-center">
        <WelcomeImage />

        <p className="text-foreground max-w-prose pt-1 leading-6 font-medium">
          Chat with ANA, your advanced neural assistant powered by cutting-edge AI technology.
        </p>

        <Button variant="primary" size="lg" onClick={onStartCall} className="mt-6 w-64 font-mono">
          {startButtonText}
        </Button>
      </section>
    </div>
  );
};
