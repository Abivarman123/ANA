"""Hardware control tools (Arduino, LED, etc.)."""

import atexit
import logging
import time
from typing import Optional

import serial
from livekit.agents import RunContext, function_tool

from ..config import config


class ArduinoController:
    """Manages serial connection to Arduino with automatic cleanup."""

    def __init__(self):
        self._connection: Optional[serial.Serial] = None
        self._config = config.hardware
        self._last_used = time.time()
        self._idle_timeout = 300  # 5 minutes
        self._available = False  # <- track availability
        self._last_error_log = 0  # <- prevent spam (log every N sec)
        self._error_cooldown = 60  # seconds between identical error logs

    def get_connection(self) -> Optional[serial.Serial]:
        """Get or create serial connection to Arduino if available."""
        # Close idle connection
        if self._connection and self._connection.is_open:
            if time.time() - self._last_used > self._idle_timeout:
                logging.info("Closing idle Arduino connection")
                self._connection.close()
                self._connection = None

        if self._connection is None or not self._connection.is_open:
            try:
                self._connection = serial.Serial(
                    self._config["serial_port"],
                    self._config["baud_rate"],
                    timeout=self._config["timeout"],
                )
                time.sleep(2)
                self._available = True
                logging.info("✅ Arduino connection established")
            except Exception as e:
                # Avoid spamming error messages
                now = time.time()
                if now - self._last_error_log > self._error_cooldown:
                    logging.warning(f"⚠️ Arduino not connected: {e}")
                    self._last_error_log = now
                self._available = False
                return None

        self._last_used = time.time()
        return self._connection

    def send_command(self, command: str) -> str:
        """Send command to Arduino and return response or skip if unavailable."""
        conn = self.get_connection()
        if not conn or not self._available:
            return "⚠️ Arduino not connected"
        try:
            conn.write(f"{command}\n".encode())
            time.sleep(0.1)
            return conn.readline().decode().strip() if conn.in_waiting else "OK"
        except Exception as e:
            logging.error(f"Arduino command error: {e}")
            self._available = False
            return f"Error: {e}"

    def _format_response(self, response: str, success_msg: str) -> str:
        """Format Arduino response for user."""
        if "not connected" in response:
            return "⚠️ Arduino not connected"
        return (
            f"✓ {success_msg}"
            if "OK" in response or "Error" not in response
            else response
        )

    def close(self):
        """Close the serial connection."""
        if self._connection and self._connection.is_open:
            logging.info("Closing Arduino connection")
            self._connection.close()
            self._connection = None
        self._available = False

    def __del__(self):
        """Cleanup on deletion."""
        self.close()


# Global Arduino controller instance
_arduino = ArduinoController()
atexit.register(_arduino.close)


# --- Tools --- #
@function_tool()
async def turn_led_on(context: RunContext) -> str:
    return _arduino._format_response(_arduino.send_command("12:ON"), "LED turned ON")


@function_tool()
async def turn_led_off(context: RunContext) -> str:
    return _arduino._format_response(_arduino.send_command("12:OFF"), "LED turned OFF")


@function_tool()
async def turn_led_on_for_duration(context: RunContext, seconds: int) -> str:
    if "not connected" in _arduino.send_command("PING"):
        return "⚠️ Arduino not connected"
    _arduino.send_command("12:ON")
    time.sleep(seconds)
    _arduino.send_command("12:OFF")
    return f"✓ LED was ON for {seconds} seconds"


@function_tool()
async def turn_fan_on(context: RunContext) -> str:
    return _arduino._format_response(_arduino.send_command("10:ON"), "Fan turned ON")


@function_tool()
async def turn_fan_off(context: RunContext) -> str:
    return _arduino._format_response(_arduino.send_command("10:OFF"), "Fan turned OFF")


@function_tool()
async def open_door(context: RunContext) -> str:
    return _arduino._format_response(_arduino.send_command("8:OPEN"), "Door opened")


@function_tool()
async def close_door(context: RunContext) -> str:
    return _arduino._format_response(_arduino.send_command("8:CLOSE"), "Door closed")


def cleanup_hardware():
    _arduino.send_command("12:OFF")
    _arduino.send_command("10:OFF")
    _arduino.close()
