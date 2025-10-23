"""Wake word detection module for ANA using Porcupine."""

import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import psutil
import pvporcupine
import sounddevice as sd

logger = logging.getLogger(__name__)


class WakeWordDetector:
    """Detects wake word using Porcupine and triggers ANA."""

    def __init__(
        self,
        access_key: str,
        keyword_path: Optional[str] = None,
        sensitivity: Optional[float] = None,
        on_wake_callback: Optional[Callable] = None,
    ):
        """
        Initialize wake word detector.

        Args:
            access_key: Picovoice access key for Porcupine
            keyword_path: Path to .ppn wake word file (defaults to config.json setting)
            sensitivity: Detection sensitivity 0.0-1.0 (defaults to config.json setting)
            on_wake_callback: Callback function when wake word is detected
        """
        from .config import config

        self.access_key = access_key
        self.on_wake_callback = on_wake_callback
        self.is_running = False

        # Get wake word config
        wake_config = config.wake_word

        # Use provided sensitivity or fall back to config
        self.sensitivity = sensitivity if sensitivity is not None else wake_config.get("sensitivity", 0.5)

        # Find keyword path
        if keyword_path is None:
            project_root = Path(__file__).parent.parent.parent
            keyword_filename = wake_config.get("keyword_path", "Hey-ANA.ppn")
            keyword_path = project_root / keyword_filename
        else:
            keyword_path = Path(keyword_path)

        if not keyword_path.exists():
            raise FileNotFoundError(f"Wake word file not found: {keyword_path}")

        self.keyword_path = str(keyword_path)
        self.porcupine = None
        self.audio_stream = None

    def start(self):
        """Start listening for wake word."""
        try:
            # Initialize Porcupine
            self.porcupine = pvporcupine.create(
                access_key=self.access_key,
                keyword_paths=[self.keyword_path],
                sensitivities=[self.sensitivity],
            )

            # Initialize sounddevice stream
            self.audio_stream = sd.InputStream(
                samplerate=self.porcupine.sample_rate,
                channels=1,
                dtype=np.int16,
                blocksize=self.porcupine.frame_length,
            )
            self.audio_stream.start()

            self.is_running = True
            print("🎤 Wake word detector started. Say 'Hey ANA' to activate...")

            # Main detection loop
            while self.is_running:
                # Read audio frame
                pcm, overflowed = self.audio_stream.read(self.porcupine.frame_length)
                if overflowed:
                    logger.warning("Audio buffer overflow detected")
                
                # Convert to 1D array and process
                pcm = pcm.flatten()
                keyword_index = self.porcupine.process(pcm)

                if keyword_index >= 0:
                    print("✨ Wake word detected! Activating ANA...")
                    self._handle_wake_word()

        except KeyboardInterrupt:
            print("\n⏹️  Wake word detector stopped by user.")
        except Exception as e:
            print(f"❌ Error in wake word detector: {e}")
            raise
        finally:
            self.stop()

    def stop(self):
        """Stop the wake word detector."""
        self.is_running = False

        if self.audio_stream is not None:
            self.audio_stream.stop()
            self.audio_stream.close()
            self.audio_stream = None

        if self.porcupine is not None:
            self.porcupine.delete()
            self.porcupine = None

    def _handle_wake_word(self):
        """Handle wake word detection."""
        if self.on_wake_callback:
            self.on_wake_callback()
        else:
            # Default behavior: launch ANA
            self._launch_ana()

    def _is_ana_running(self) -> bool:
        """Check if ANA is already running."""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline')
                    if cmdline and 'python' in proc.info['name'].lower():
                        # Check if main.py is in the command line
                        cmdline_str = ' '.join(cmdline)
                        if 'main.py' in cmdline_str and 'ANA' in cmdline_str:
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return False
        except Exception:
            return False

    def _launch_ana(self):
        """Launch the main ANA agent."""
        # Check if ANA is already running
        if self._is_ana_running():
            print("⚠️  ANA is already running. Skipping launch.")
            return

        try:
            project_root = Path(__file__).parent.parent.parent
            main_script = project_root / "main.py"

            print("🚀 Launching ANA...")

            if sys.platform == "win32":
                # Windows: Start in new console window with uv run
                # Use 'python' explicitly to ensure visible terminal (not pythonw)
                process = subprocess.Popen(
                    ["cmd", "/c", "start", "cmd", "/k", "uv", "run", "python", str(main_script), "console"],
                    cwd=str(project_root),
                    shell=True,
                )
            else:
                # Unix-like: Start in background
                process = subprocess.Popen(
                    [sys.executable, str(main_script), "console"],
                    cwd=str(project_root),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            # Wait briefly to check if process started successfully
            time.sleep(1)
            if process.poll() is None:
                print("✅ ANA launched successfully!")
            else:
                print("⚠️  ANA process exited immediately. Check for errors.")

        except Exception as e:
            print(f"❌ Failed to launch ANA: {e}")


def main():
    """Main entry point for wake word detector."""
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    access_key = os.getenv("PICOVOICE_KEY")
    if not access_key:
        print("❌ Error: PICOVOICE_KEY not found in .env file")
        print("Please get your free access key from https://console.picovoice.ai/")
        sys.exit(1)

    # Create and start detector
    detector = WakeWordDetector(access_key=access_key)

    try:
        detector.start()
    except KeyboardInterrupt:
        print("\n👋 Shutting down wake word detector...")
        detector.stop()


if __name__ == "__main__":
    main()
