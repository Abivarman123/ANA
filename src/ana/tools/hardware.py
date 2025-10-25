"""Hardware control tools (Arduino, LED, etc.)."""

import logging
import time
from typing import Optional
import atexit

import serial
from livekit.agents import RunContext, function_tool

from ..config import config


class ArduinoController:
    """Manages serial connection to Arduino with automatic cleanup."""

    def __init__(self):
        self._connection: Optional[serial.Serial] = None
        self._config = config.hardware
        self._last_used = time.time()
        self._idle_timeout = 300  # 5 minutes of inactivity

    def get_connection(self) -> serial.Serial:
        """Get or create serial connection to Arduino."""
        # Close idle connection to free resources
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
                logging.info("Arduino connection established")
            except Exception as e:
                logging.error(f"Failed to connect to Arduino: {e}")
                raise
        
        self._last_used = time.time()
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
            logging.info("Closing Arduino connection")
            self._connection.close()
            self._connection = None
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()


# Global Arduino controller instance
_arduino = ArduinoController()

# Register cleanup on exit
atexit.register(_arduino.close)


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
