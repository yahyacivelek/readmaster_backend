from abc import ABC, abstractmethod
from typing import List, Any
import asyncio # Required for asyncio.gather if that approach is used

class NotificationObserver(ABC):
    @abstractmethod
    async def update(self, event: str, data: Any) -> None:
        pass

class NotificationService:
    def __init__(self):
        self._observers: List[NotificationObserver] = []

    def subscribe(self, observer: NotificationObserver):
        if observer not in self._observers:
            self._observers.append(observer)

    def unsubscribe(self, observer: NotificationObserver): # Added unsubscribe
        if observer in self._observers:
            self._observers.remove(observer)

    async def notify(self, event: str, data: Any):
        # This will run observer updates sequentially.
        # If true parallelism is needed and observers are I/O bound,
        # asyncio.gather can be used.
        for observer in self._observers:
            try:
                await observer.update(event, data)
            except Exception as e:
                # Handle exceptions from observers, e.g., log them
                print(f"Error notifying observer {observer.__class__.__name__}: {e}")
                # Decide if other observers should still be notified.
