"""Hardware control tools (Arduino, LED, etc.)."""

import logging
import time
from typing import Optional
import atexit
import threading

import serial
from livekit.agents import RunContext, function_tool

from ..config import config
from ..event_manager import event_manager, Event, EventType


class ArduinoController:
    """Manages serial connection to Arduino with automatic cleanup."""

    def __init__(self):
        self._connection: Optional[serial.Serial] = None
        self._config = config.hardware
        self._last_used = time.time()
        self._idle_timeout = 300  # 5 minutes of inactivity
        self._pir_monitor_thread: Optional[threading.Thread] = None
        self._pir_monitor_running = False

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
        """Send command to Arduino and return response."""
        try:
            conn = self.get_connection()
            conn.write(f"{command}\n".encode())
            time.sleep(0.1)
            return conn.readline().decode().strip() if conn.in_waiting else "OK"
        except Exception as e:
            logging.error(f"Arduino command error: {e}")
            return f"Error: {e}"
    
    def _format_response(self, response: str, success_msg: str) -> str:
        """Format Arduino response for user."""
        return f"✓ {success_msg}" if "OK" in response or "Error" not in response else response

    def start_pir_monitoring(self, auto_start: bool = False):
        """Start monitoring PIR sensor events from Arduino.
        
        Args:
            auto_start: If True, only start if enabled in config
        """
        # Check config if auto-starting
        if auto_start and not self._config.get("pir_monitoring_enabled", False):
            return
        
        if self._pir_monitor_running:
            logging.warning("PIR monitoring already running")
            return
        
        self._pir_monitor_running = True
        
        def monitor_pir():
            """Monitor Arduino serial for PIR events."""
            logging.info("PIR monitoring started")
            while self._pir_monitor_running:
                try:
                    conn = self.get_connection()
                    if conn.in_waiting:
                        line = conn.readline().decode().strip()
                        if line == "EVENT:PERSON_AT_DOOR":
                            event = Event(
                                event_type=EventType.SENSOR,
                                message="Someone is at your door!",
                                data={"sensor": "pir", "location": "front_door"}
                            )
                            event_manager.add_event(event)
                            logging.info("PIR event detected")
                    time.sleep(0.1)
                except Exception as e:
                    logging.error(f"PIR monitoring error: {e}")
                    time.sleep(1)
        
        self._pir_monitor_thread = threading.Thread(target=monitor_pir, daemon=True)
        self._pir_monitor_thread.start()
        logging.info("PIR monitoring thread started")
    
    def stop_pir_monitoring(self):
        """Stop PIR monitoring."""
        self._pir_monitor_running = False
        if self._pir_monitor_thread:
            self._pir_monitor_thread.join(timeout=2)
            self._pir_monitor_thread = None
        logging.info("PIR monitoring stopped")

    def close(self):
        """Close the serial connection."""
        self.stop_pir_monitoring()
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
async def turn_led_on(context: RunContext) -> str:  # type: ignore
    """Turn ON the LED."""
    return _arduino._format_response(_arduino.send_command("12:ON"), "LED turned ON")


@function_tool()
async def turn_led_off(context: RunContext) -> str:  # type: ignore
    """Turn OFF the LED."""
    return _arduino._format_response(_arduino.send_command("12:OFF"), "LED turned OFF")


@function_tool()
async def turn_led_on_for_duration(context: RunContext, seconds: int) -> str:  # type: ignore
    """Turn ON the LED for specified seconds, then turn it OFF."""
    _arduino.send_command("12:ON")
    time.sleep(seconds)
    _arduino.send_command("12:OFF")
    return f"✓ LED was ON for {seconds} seconds"


@function_tool()
async def turn_fan_on(context: RunContext) -> str:  # type: ignore
    """Turn ON the fan."""
    return _arduino._format_response(_arduino.send_command("10:ON"), "Fan turned ON")


@function_tool()
async def turn_fan_off(context: RunContext) -> str:  # type: ignore
    """Turn OFF the fan."""
    return _arduino._format_response(_arduino.send_command("10:OFF"), "Fan turned OFF")


@function_tool()
async def open_door(context: RunContext) -> str:  # type: ignore
    """Open the door (servo to 90 degrees)."""
    return _arduino._format_response(_arduino.send_command("8:OPEN"), "Door opened")


@function_tool()
async def close_door(context: RunContext) -> str:  # type: ignore
    """Close the door (servo to 0 degrees)."""
    return _arduino._format_response(_arduino.send_command("8:CLOSE"), "Door closed")


def start_pir_monitoring_if_enabled():
    """Start PIR monitoring if enabled in config."""
    _arduino.start_pir_monitoring(auto_start=True)


def cleanup_hardware():
    """Cleanup hardware connections."""
    _arduino.send_command("12:OFF")
    _arduino.send_command("10:OFF")
    _arduino.close()
