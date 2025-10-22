"""Hardware control tools (Arduino, LED, etc.)."""

import logging
import time
from typing import Optional

import serial
from livekit.agents import RunContext, function_tool

from ..config import config


class ArduinoController:
    """Manages serial connection to Arduino."""

    def __init__(self):
        self._connection: Optional[serial.Serial] = None
        self._config = config.hardware

    def get_connection(self) -> serial.Serial:
        """Get or create serial connection to Arduino."""
        if self._connection is None or not self._connection.is_open:
            self._connection = serial.Serial(
                self._config["serial_port"],
                self._config["baud_rate"],
                timeout=self._config["timeout"],
            )
            time.sleep(2)
        return self._connection

    def send_command(self, command: str) -> str:
        """Send command to Arduino."""
        try:
            conn = self.get_connection()
            conn.write(f"{command}\n".encode())
            time.sleep(0.1)
            return conn.readline().decode().strip() if conn.in_waiting else "OK"
        except Exception as e:
            logging.error(f"Arduino command error: {e}")
            return f"Error: {e}"

    def close(self):
        """Close the serial connection."""
        if self._connection and self._connection.is_open:
            self._connection.close()


# Global Arduino controller instance
_arduino = ArduinoController()


@function_tool()
async def turn_led_on(
    context: RunContext,  # type: ignore
) -> str:
    """Turn ON the LED."""
    response = _arduino.send_command("12:ON")
    return (
        "✓ LED turned ON" if "OK" in response or "Error" not in response else response
    )


@function_tool()
async def turn_led_off(
    context: RunContext,  # type: ignore
) -> str:
    """Turn OFF the LED."""
    response = _arduino.send_command("12:OFF")
    return (
        "✓ LED turned OFF" if "OK" in response or "Error" not in response else response
    )


@function_tool()
async def turn_led_on_for_duration(
    context: RunContext,  # type: ignore
    seconds: int,
) -> str:
    """Turn ON the LED for specified seconds, then turn it OFF."""
    _arduino.send_command("12:ON")
    time.sleep(seconds)
    _arduino.send_command("12:OFF")
    return f"✓ LED was ON for {seconds} seconds"


def cleanup_hardware():
    """Cleanup hardware connections."""
    _arduino.send_command("12:OFF")
    _arduino.close()
