"""
Domain service for handling notifications.
Uses an observer pattern to allow different parts of the system
to react to notification events (e.g., send email, WebSocket message).
"""
from abc import ABC, abstractmethod
from typing import List, Any, Dict
import asyncio
import uuid # For user_id type hint consistency

# Import the global connection manager instance from the presentation layer.
# This creates a dependency from domain service to a presentation layer component.
# While not ideal in strict Clean Architecture, for real-time notifications
# that are inherently tied to client connections (managed by presentation),
# this can be a pragmatic approach.
# Alternatives:
# 1. Domain events + application service handler: Domain emits event, app service handles it
#    and then calls presentation layer (WebSocket manager). This adds more layers.
# 2. Injecting an interface: Define INotificationSender in domain, implement in presentation,
#    and inject. This is cleaner but means NotificationService can't directly know about
#    WebSockets, which might be fine.
# For this implementation, we directly use the connection_manager via an observer.
from readmaster_ai.presentation.websockets.connection_manager import manager as global_connection_manager

# Example: from readmaster_ai.domain.value_objects.common_enums import NotificationType # If event_type is an Enum


class NotificationObserver(ABC):
    """
    Abstract Base Class for notification observers.
    Observers implement the update method to react to notifications.
    """
    @abstractmethod
    async def update(self, user_id: uuid.UUID, event_type: str, data: Dict[str, Any]) -> None:
        """
        Called when a notification event occurs that this observer is subscribed to.
        Args:
            user_id: The ID of the user to whom the notification is targeted.
            event_type: A string representing the type of event (e.g., "assessment_completed").
            data: A dictionary containing the payload of the notification.
        """
        pass

class WebSocketNotificationObserver(NotificationObserver):
    """
    A NotificationObserver that sends notifications via WebSockets.
    It uses a ConnectionManager to find active WebSocket connections for a user.
    """
    def __init__(self, connection_manager): # Type hint: connection_manager: ConnectionManager
        if connection_manager is None:
            # This check is important if global_connection_manager might not be initialized
            # when WebSocketNotificationObserver is created.
            raise ValueError("ConnectionManager cannot be None for WebSocketNotificationObserver")
        self.connection_manager = connection_manager
        print("WebSocketNotificationObserver initialized.")

    async def update(self, user_id: uuid.UUID, event_type: str, data: Dict[str, Any]) -> None:
        """
        Sends a notification to the specified user via WebSocket.
        The message payload is structured with "event", "userId", and "payload".
        """
        # Prepare the message payload for WebSocket.
        # This structure should be agreed upon with the frontend client.
        message_payload = {
            "event": event_type,
            "userId": str(user_id), # Ensure UUID is stringified for JSON
            "payload": data         # The actual notification content
        }
        print(f"WebSocketObserver: Preparing to send notification event '{event_type}' to user {user_id}.")
        # The send_personal_message method handles finding active connections for the user
        # and sending the message to each. It also handles serialization to JSON.
        await self.connection_manager.send_personal_message(message_payload, user_id)
        print(f"WebSocketObserver: Attempted to send notification for event '{event_type}' to user {user_id}.")


class NotificationService:
    """
    Manages observers and dispatches notifications to them.
    This service allows decoupling the source of a notification event
    from the specific ways notifications are delivered (e.g., WebSocket, email).
    """
    def __init__(self):
        self._observers: List[NotificationObserver] = []
        print("NotificationService initialized.")
        # Conceptual: Auto-subscribe WebSocket observer if this service is a singleton.
        # However, explicit registration (e.g., in main.py or DI setup) is clearer.
        # Example if auto-subscribing:
        # try:
        #     self.subscribe(WebSocketNotificationObserver(global_connection_manager))
        #     print("WebSocketNotificationObserver auto-subscribed to NotificationService.")
        # except Exception as e:
        #     print(f"Error auto-subscribing WebSocketNotificationObserver: {e}")


    def subscribe(self, observer: NotificationObserver):
        """Subscribes an observer to receive notifications."""
        if observer not in self._observers:
            self._observers.append(observer)
            print(f"Observer {type(observer).__name__} subscribed to NotificationService.")

    def unsubscribe(self, observer: NotificationObserver):
        """Unsubscribes an observer from receiving notifications."""
        if observer in self._observers:
            self._observers.remove(observer)
            print(f"Observer {type(observer).__name__} unsubscribed from NotificationService.")

    async def notify(self, user_id: uuid.UUID, event_type: str, data: Dict[str, Any]):
        """
        Notifies all subscribed observers about an event targeted at a specific user.
        Args:
            user_id: The UUID of the user to notify.
            event_type: A string identifier for the type of event (e.g., "new_assessment_result").
            data: A dictionary payload containing details about the event.
        """
        if not self._observers:
            print(f"NotificationService: No observers subscribed. Notification for user {user_id}, event '{event_type}' will not be sent.")
            return

        print(f"NotificationService: Notifying {len(self._observers)} observer(s) for user {user_id}, event '{event_type}'.")

        # Prepare coroutines for all observer updates
        tasks: List[asyncio.Coroutine] = [
            observer.update(user_id, event_type, data) for observer in self._observers
        ]

        if tasks:
            # asyncio.gather runs all tasks concurrently and collects results.
            # return_exceptions=True ensures that if an observer fails, other observers
            # are still processed, and the exception is returned in the results list.
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # Log the exception from the observer.
                    # In a real app, use structured logging.
                    observer_name = type(self._observers[i]).__name__
                    print(f"Error in NotificationObserver '{observer_name}' during notify for user {user_id}, event '{event_type}': {type(result).__name__} - {result}")
                    # Depending on policy, you might want to retry or take other actions for failed observers.
        print(f"NotificationService: Finished notifying observers for user {user_id}, event '{event_type}'.")


# --- Example of how this might be instantiated and used (conceptual) ---
# This part is typically handled in application setup (e.g., main.py or a DI container)

# 1. Create a global or DI-managed instance of NotificationService:
# notification_service = NotificationService()

# 2. Create instances of observers:
# ws_observer = WebSocketNotificationObserver(global_connection_manager) # global_connection_manager from websockets module
# email_observer = EmailNotificationObserver() # Assuming EmailNotificationObserver is defined elsewhere

# 3. Subscribe observers to the service:
# notification_service.subscribe(ws_observer)
# notification_service.subscribe(email_observer)

# 4. When a notification needs to be sent (e.g., from a use case or another service):
# async def some_business_logic_that_triggers_notification():
#     user_to_notify = uuid.uuid4() # Example user ID
#     event = "new_badge_awarded"
#     payload = {"badge_name": "Reader Pro", "level": 5}
#     await notification_service.notify(user_id=user_to_notify, event_type=event, data=payload)
