"""Background tasks for timers and sensors."""

import logging
import threading
from typing import Callable

from .event_manager import event_manager, EventType, Event


class BackgroundTimer:
    """Manages background timers."""

    def __init__(self):
        self._active_timers: dict[str, threading.Event] = {}

    def set_timer(self, name: str, seconds: int, message: str) -> str:
        """Set a timer that triggers an event after specified seconds."""
        if name in self._active_timers:
            return f"Timer '{name}' already exists"

        stop_event = threading.Event()
        self._active_timers[name] = stop_event

        def timer_task():
            logging.info(f"Timer '{name}' started for {seconds}s")
            if stop_event.wait(timeout=seconds):
                return  # Cancelled
            
            # Timer completed - create event
            event = Event(
                event_type=EventType.TIMER,
                message=message,
                data={"timer_name": name, "duration": seconds}
            )
            event_manager.add_event(event)
            
            if name in self._active_timers:
                del self._active_timers[name]

        thread = threading.Thread(target=timer_task, daemon=True)
        thread.start()
        
        return f"✓ Timer '{name}' set for {seconds} seconds"

    def cancel_timer(self, name: str) -> str:
        """Cancel an active timer."""
        if name not in self._active_timers:
            return f"Timer '{name}' not found"
        
        self._active_timers[name].set()
        del self._active_timers[name]
        return f"✓ Timer '{name}' cancelled"

    def list_timers(self) -> list[str]:
        """List all active timers."""
        return list(self._active_timers.keys())


class SensorMonitor:
    """Monitors sensors and triggers events."""

    def __init__(self):
        self._active_sensors: dict[str, threading.Event] = {}

    def start_sensor(self, name: str, check_interval: float, sensor_func: Callable[[], bool], alert_message: str) -> str:
        """Start monitoring a sensor."""
        if name in self._active_sensors:
            return f"Sensor '{name}' already active"

        stop_event = threading.Event()
        self._active_sensors[name] = stop_event

        def sensor_task():
            logging.info(f"Sensor '{name}' monitoring started")
            while not stop_event.is_set():
                try:
                    if sensor_func():
                        event = Event(
                            event_type=EventType.SENSOR,
                            message=alert_message,
                            data={"sensor_name": name}
                        )
                        event_manager.add_event(event)
                    stop_event.wait(timeout=check_interval)
                except Exception as e:
                    logging.error(f"Sensor '{name}' error: {e}")
                    stop_event.wait(timeout=check_interval)

        thread = threading.Thread(target=sensor_task, daemon=True)
        thread.start()
        
        return f"✓ Sensor '{name}' monitoring started"

    def stop_sensor(self, name: str) -> str:
        """Stop monitoring a sensor."""
        if name not in self._active_sensors:
            return f"Sensor '{name}' not found"
        
        self._active_sensors[name].set()
        del self._active_sensors[name]
        return f"✓ Sensor '{name}' stopped"


# Global instances
background_timer = BackgroundTimer()
sensor_monitor = SensorMonitor()
