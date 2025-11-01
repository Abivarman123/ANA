"""Wake word detection module for ANA using Porcupine."""

import atexit
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Optional, Set

import numpy as np
import psutil
import pvporcupine
import sounddevice as sd

logger = logging.getLogger(__name__)

_spawned_processes: Set[subprocess.Popen] = set()


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
        self._cleanup_registered = False

        wake_config = config.wake_word
        self.sensitivity = (
            sensitivity
            if sensitivity is not None
            else wake_config.get("sensitivity", 0.5)
        )
        if keyword_path is None:
            project_root = Path(__file__).parent.parent.parent
            keyword_filename = wake_config.get(
                "keyword_path", "../wake_word/Hey-ANA.ppn"
            )
            keyword_path = project_root / "wake_word" / keyword_filename
        else:
            keyword_path = Path(keyword_path)

        if not keyword_path.exists():
            raise FileNotFoundError(f"Wake word file not found: {keyword_path}")

        self.keyword_path = str(keyword_path)
        self.porcupine = None
        self.audio_stream = None

        if not self._cleanup_registered:
            atexit.register(self.stop)
            self._cleanup_registered = True

    def start(self):
        """Start listening for wake word."""
        try:
            self.porcupine = pvporcupine.create(
                access_key=self.access_key,
                keyword_paths=[self.keyword_path],
                sensitivities=[self.sensitivity],
            )

            self.audio_stream = sd.InputStream(
                samplerate=self.porcupine.sample_rate,
                channels=1,
                dtype=np.int16,
                blocksize=self.porcupine.frame_length,
            )
            self.audio_stream.start()

            self.is_running = True
            print("🎤 Wake word detector started. Say 'Hey ANA' to activate...")

            while self.is_running:
                pcm, overflowed = self.audio_stream.read(self.porcupine.frame_length)
                if overflowed:
                    logger.warning("Audio buffer overflow detected")

                pcm = pcm.flatten()
                keyword_index = self.porcupine.process(pcm)

                if keyword_index >= 0:
                    print("✨ Wake word detected! Activating ANA...")
                    self._handle_wake_word()

        except KeyboardInterrupt:
            logger.info("Service stopped by user")
            cleanup_spawned_processes()
        except Exception as e:
            print(f"❌ Error in wake word detector: {e}")
            raise
        finally:
            self.stop()

    def stop(self):
        """Stop the wake word detector and cleanup resources."""
        self.is_running = False

        if self.audio_stream is not None:
            try:
                self.audio_stream.stop()
                self.audio_stream.close()
                logger.info("Audio stream closed")
            except Exception as e:
                logger.warning(f"Error closing audio stream: {e}")
            finally:
                self.audio_stream = None

        if self.porcupine is not None:
            try:
                self.porcupine.delete()
                logger.info("Porcupine instance deleted")
            except Exception as e:
                logger.warning(f"Error deleting Porcupine: {e}")
            finally:
                self.porcupine = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.stop()
        return False

    def __del__(self):
        """Cleanup on deletion."""
        self.stop()

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
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    cmdline = proc.info.get("cmdline")
                    if cmdline and "python" in proc.info["name"].lower():
                        # Check if main.py is in the command line
                        cmdline_str = " ".join(cmdline)
                        if "main.py" in cmdline_str and "ANA" in cmdline_str:
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
                process = subprocess.Popen(
                    [
                        "cmd",
                        "/c",
                        "start",
                        "cmd",
                        "/k",
                        "uv",
                        "run",
                        "python",
                        str(main_script),
                        "console",
                    ],
                    cwd=str(project_root),
                    shell=True,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            else:
                process = subprocess.Popen(
                    [sys.executable, str(main_script), "console"],
                    cwd=str(project_root),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )

            _spawned_processes.add(process)

            # Wait briefly to check if process started successfully
            time.sleep(1)
            if process.poll() is None:
                print("✅ ANA launched successfully!")
            else:
                print("⚠️  ANA process exited immediately. Check for errors.")

        except Exception as e:
            print(f"❌ Failed to launch ANA: {e}")


def cleanup_spawned_processes():
    """Cleanup any spawned ANA processes that are still running."""
    for process in list(_spawned_processes):
        try:
            if process.poll() is None:  # Process still running
                logger.info(f"Cleaning up spawned process {process.pid}")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            _spawned_processes.remove(process)
        except Exception as e:
            logger.warning(f"Error cleaning up process: {e}")


# Register cleanup on exit
atexit.register(cleanup_spawned_processes)


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

    # Create and start detector with context manager
    with WakeWordDetector(access_key=access_key) as detector:
        try:
            detector.start()
        except KeyboardInterrupt:
            print("\n👋 Shutting down wake word detector...")


if __name__ == "__main__":
    main()
