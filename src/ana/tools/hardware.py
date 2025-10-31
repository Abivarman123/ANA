"""Hardware control tools (Arduino, LED, etc.)."""

import asyncio
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
        self._available = False
        self._error_logged = False  # Only log connection error once per session

    async def get_connection(self) -> Optional[serial.Serial]:
        """Get or create serial connection to Arduino if available."""
        # Close idle connection
        if self._connection and self._connection.is_open:
            if time.time() - self._last_used > self._idle_timeout:
                logging.info("Closing idle Arduino connection")
                self._connection.close()
                self._connection = None

        if self._connection is None or not self._connection.is_open:
            try:
                # Run blocking serial connection in executor to avoid blocking event loop
                loop = asyncio.get_event_loop()
                self._connection = await loop.run_in_executor(
                    None,
                    lambda: serial.Serial(
                        self._config["serial_port"],
                        self._config["baud_rate"],
                        timeout=self._config["timeout"],
                    ),
                )
                # Use async sleep instead of blocking
                await asyncio.sleep(2)
                self._available = True
                self._error_logged = False  # Reset on successful connection
                logging.info("✅ Arduino connection established")
            except Exception as e:
                # Only log once per session to avoid spam
                if not self._error_logged:
                    logging.warning(f"⚠️ Arduino not connected: {e}")
                    self._error_logged = True
                self._available = False
                return None

        self._last_used = time.time()
        return self._connection

    async def send_command(self, command: str) -> str:
        """Send command to Arduino and return response or skip if unavailable."""
        conn = await self.get_connection()
        if not conn or not self._available:
            return "⚠️ Arduino not connected"
        try:
            # Run blocking I/O in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: conn.write(f"{command}\n".encode()))
            await asyncio.sleep(0.1)
            response = await loop.run_in_executor(
                None, lambda: conn.readline().decode().strip() if conn.in_waiting else "OK"
            )
            return response
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
    response = await _arduino.send_command("12:ON")
    return _arduino._format_response(response, "LED turned ON")


@function_tool()
async def turn_led_off(context: RunContext) -> str:
    response = await _arduino.send_command("12:OFF")
    return _arduino._format_response(response, "LED turned OFF")


@function_tool()
async def turn_led_on_for_duration(context: RunContext, seconds: int) -> str:
    ping_response = await _arduino.send_command("PING")
    if "not connected" in ping_response:
        return "⚠️ Arduino not connected"
    await _arduino.send_command("12:ON")
    await asyncio.sleep(seconds)
    await _arduino.send_command("12:OFF")
    return f"✓ LED was ON for {seconds} seconds"


@function_tool()
async def turn_fan_on(context: RunContext) -> str:
    response = await _arduino.send_command("10:ON")
    return _arduino._format_response(response, "Fan turned ON")


@function_tool()
async def turn_fan_off(context: RunContext) -> str:
    response = await _arduino.send_command("10:OFF")
    return _arduino._format_response(response, "Fan turned OFF")


@function_tool()
async def open_door(context: RunContext) -> str:
    response = await _arduino.send_command("8:OPEN")
    return _arduino._format_response(response, "Door opened")


@function_tool()
async def close_door(context: RunContext) -> str:
    response = await _arduino.send_command("8:CLOSE")
    return _arduino._format_response(response, "Door closed")


async def cleanup_hardware():
    await _arduino.send_command("12:OFF")
    await _arduino.send_command("10:OFF")
    _arduino.close()
