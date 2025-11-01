"""Hardware control tools (Arduino, LED, etc.)."""

import atexit
import logging
import time
from typing import Optional

import serial
from livekit.agents import RunContext, function_tool

from ..config import config


class ArduinoController:
    """Manages serial connection to Arduino with startup-only connection check."""

    def __init__(self):
        self._connection: Optional[serial.Serial] = None
        self._config = config.hardware
        self._available = False  # <- track availability
        self._initialized = False  # <- track if initialization was attempted

        # Check connection once at initialization
        self._initialize_connection()

    def _initialize_connection(self) -> None:
        """Attempt to establish Arduino connection once at startup."""
        if self._initialized:
            return

        self._initialized = True
        try:
            self._connection = serial.Serial(
                self._config["serial_port"],
                self._config["baud_rate"],
                timeout=self._config["timeout"],
            )
            time.sleep(2)
            self._available = True
            logging.info("✅ Arduino connection established at startup")
        except Exception as e:
            logging.warning(f"⚠️ Arduino not connected at startup: {e}")
            self._available = False
            self._connection = None

    def get_connection(self) -> Optional[serial.Serial]:
        """Get existing Arduino connection (no reconnection attempts)."""
        if self._available and self._connection and self._connection.is_open:
            return self._connection
        return None

    def send_command(self, command: str) -> str:
        """Send command to Arduino and return response or skip if unavailable."""
        conn = self.get_connection()
        if not conn:
            return "⚠️ Arduino not connected"
        try:
            conn.write(f"{command}\n".encode())
            time.sleep(0.1)
            return conn.readline().decode().strip() if conn.in_waiting else "OK"
        except Exception as e:
            logging.error(f"Arduino command error: {e}")
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
