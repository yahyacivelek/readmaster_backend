"""
Manages active WebSocket connections for real-time communication.
Allows sending messages to specific users or broadcasting to all.
"""
from fastapi import WebSocket
from typing import Dict, List, Optional, Set
from uuid import UUID
import json # For serializing dictionaries to JSON strings for WebSocket transport

class ConnectionManager:
    """
    Manages WebSocket connections, mapping user IDs to their active WebSocket instances.
    Supports multiple connections per user (e.g., from different devices or browser tabs).
    """
    def __init__(self):
        # active_connections: A dictionary where keys are user_ids (UUID)
        # and values are sets of WebSocket objects for that user.
        self.active_connections: Dict[UUID, Set[WebSocket]] = {}
        print("ConnectionManager initialized.")

    async def connect(self, websocket: WebSocket, user_id: UUID):
        """
        Accepts a new WebSocket connection and associates it with a user ID.
        """
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        print(f"User {user_id} connected via WebSocket {websocket}. Total connections for user: {len(self.active_connections[user_id])}")

    def disconnect(self, websocket: WebSocket, user_id: UUID):
        """
        Removes a WebSocket connection from the active list for a user.
        If the user has no more active connections, their entry is removed.
        """
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
                if not self.active_connections[user_id]: # No more connections for this user
                    del self.active_connections[user_id]
                    print(f"User {user_id} has no more active WebSocket connections. Removing user entry.")
                else:
                    print(f"User {user_id} disconnected WebSocket {websocket}. Remaining connections for user: {len(self.active_connections[user_id])}")
            else:
                # This might happen if disconnect is called multiple times for the same socket or if socket was never added.
                print(f"Warning: WebSocket {websocket} not found in active set for user {user_id} during disconnect.")
        else:
            # This might happen if disconnect is called for a user_id that never connected or was already fully disconnected.
            print(f"Warning: User {user_id} not found in active_connections during disconnect call for WebSocket {websocket}.")


    async def send_personal_message(self, message: Dict, user_id: UUID):
        """
        Sends a JSON-serialized message to all active WebSocket connections for a specific user.
        Handles disconnections if sending fails.
        """
        if user_id in self.active_connections:
            disconnected_sockets_for_user: List[WebSocket] = []
            json_message = json.dumps(message) # Serialize dict to JSON string

            # Iterate over a copy of the set in case of modifications during iteration
            for websocket_instance in list(self.active_connections[user_id]):
                try:
                    await websocket_instance.send_text(json_message)
                    print(f"Sent message to user {user_id} via WebSocket {websocket_instance}.")
                except Exception as e:
                    # Common exceptions: websockets.exceptions.ConnectionClosed, RuntimeError if socket is closing.
                    print(f"Error sending message to user {user_id} on WebSocket {websocket_instance}: {type(e).__name__} - {e}. Marking for disconnect.")
                    disconnected_sockets_for_user.append(websocket_instance)

            # Clean up any sockets that failed during send operation
            if disconnected_sockets_for_user:
                print(f"Cleaning up {len(disconnected_sockets_for_user)} disconnected sockets for user {user_id}.")
                for sock_to_remove in disconnected_sockets_for_user:
                    # The disconnect method handles removal from the set and user entry if set becomes empty.
                    self.disconnect(sock_to_remove, user_id)
        else:
            print(f"User {user_id} has no active WebSocket connections to send message to.")

    async def broadcast(self, message: Dict):
        """
        Broadcasts a JSON-serialized message to all connected users and all their devices.
        """
        json_message = json.dumps(message) # Serialize once
        # Iterate over a list of user_ids to avoid issues if active_connections changes during iteration
        all_user_ids_at_broadcast_start = list(self.active_connections.keys())

        print(f"Broadcasting message to {len(all_user_ids_at_broadcast_start)} user(s).")
        for user_id in all_user_ids_at_broadcast_start:
            # Re-check if user_id is still active as send_personal_message might modify active_connections
            if user_id in self.active_connections:
                 # Using send_personal_message ensures consistent error handling and cleanup
                await self.send_personal_message(message, user_id) # Pass original dict, it will be dumped again

# Global instance of ConnectionManager.
# This makes it accessible throughout the application, particularly in routers or services
# that need to send WebSocket messages.
manager = ConnectionManager()
