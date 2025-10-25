"""Background service for ANA wake word detection.

This script runs continuously in the background, listening for the wake word.
"""

import atexit
import logging
import os
import signal
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ana.config import config
from ana.wake_word import WakeWordDetector


def setup_logging():
    """Configure logging for the service."""
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / "wake_service.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )

    return logging.getLogger(__name__)


def main():
    """Main service entry point."""
    logger = setup_logging()
    logger.info("=" * 60)
    logger.info("ANA Wake Word Service Starting...")
    logger.info("=" * 60)

    # Load environment variables
    load_dotenv()

    access_key = os.getenv("PICOVOICE_KEY")
    if not access_key:
        logger.error("PICOVOICE_KEY not found in .env file")
        logger.error("Get your free key from: https://console.picovoice.ai/")
        sys.exit(1)

    # Get wake word settings from config
    wake_config = config.wake_word
    sensitivity = wake_config.get("sensitivity", 0.5)
    max_retries = wake_config.get("max_retries", 5)
    retry_delay = wake_config.get("retry_delay_seconds", 5)

    detector = None
    retry_count = 0

    def cleanup_handler(signum=None, frame=None):
        """Handle shutdown signals gracefully."""
        logger.info("Shutdown signal received. Cleaning up...")
        if detector:
            detector.stop()
        logger.info("Wake word service stopped cleanly")
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup_handler)
    signal.signal(signal.SIGTERM, cleanup_handler)
    atexit.register(lambda: cleanup_handler() if detector else None)

    while retry_count < max_retries:
        try:
            logger.info(f"Initializing wake word detector (sensitivity: {sensitivity})")
            detector = WakeWordDetector(
                access_key=access_key,
                sensitivity=sensitivity,
            )

            logger.info("Wake word detector initialized successfully")
            logger.info("🎤 Listening for 'Hey ANA'...")
            logger.info("Press Ctrl+C to stop")

            detector.start()

        except KeyboardInterrupt:
            logger.info("Service stopped by user")
            break

        except Exception as e:
            retry_count += 1
            logger.error(f"Error in wake word detector: {e}", exc_info=True)

            if retry_count < max_retries:
                wait_time = min(30, retry_delay * retry_count)
                logger.info(
                    f"Retrying in {wait_time} seconds... (Attempt {retry_count}/{max_retries})"
                )
                time.sleep(wait_time)
            else:
                logger.error("Max retries reached. Service stopping.")
                break

        finally:
            if detector:
                detector.stop()

    logger.info("ANA Wake Word Service Stopped")


if __name__ == "__main__":
    main()
