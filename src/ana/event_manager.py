"""Event manager for background notifications and alerts."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from queue import Queue, Empty
import threading


class EventType(Enum):
    """Types of events."""
    TIMER = "timer"
    SENSOR = "sensor"
    ALERT = "alert"


@dataclass
class Event:
    """Represents a background event."""
    event_type: EventType
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: dict = field(default_factory=dict)


class EventManager:
    """Manages background events."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._event_queue: Queue = Queue()
            self._initialized = True

    def add_event(self, event: Event) -> None:
        """Add an event to the queue."""
        self._event_queue.put(event)
        logging.info(f"Event added: {event.event_type.value} - {event.message}")

    def get_pending_events(self) -> list[Event]:
        """Get all pending events."""
        events = []
        while not self._event_queue.empty():
            try:
                events.append(self._event_queue.get_nowait())
            except Empty:
                break
        return events

    def has_pending_events(self) -> bool:
        """Check if there are pending events."""
        return not self._event_queue.empty()


# Global instance
event_manager = EventManager()
