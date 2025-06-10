"""
API Router for WebSocket communication.
Handles WebSocket connections, authentication, and basic message lifecycle.
"""
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from builtins import ValueError as InvalidUUIDError

# Connection Manager (global instance)
from readmaster_ai.presentation.websockets.connection_manager import manager

# Authentication related imports
from readmaster_ai.application.services.auth_service import AuthenticationService
from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.repositories.user_repository import UserRepository
from readmaster_ai.infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl
from readmaster_ai.infrastructure.database.config import AsyncSessionLocal # Direct session for auth helper

router = APIRouter(tags=["WebSockets"])

async def get_authenticated_user_for_ws(token: Optional[str] = Query(None)) -> Optional[DomainUser]:
    """
    Authenticates a user for a WebSocket connection using a token from query parameters.
    This is a helper function called upon new WebSocket connection.

    Args:
        token: The JWT access token.

    Returns:
        The authenticated DomainUser if token is valid, otherwise None.
        Raises WebSocketDisconnect on authentication failure.
    """
    if not token:
        print("WebSocket connection attempt without token.")
        raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication token")

    # Manual DI for auth_service and user_repo within this async scope.
    # This is necessary because WebSocket routes don't support Depends for complex DI setups
    # in the same way as HTTP routes for the initial connection handshake parameters.
    async with AsyncSessionLocal() as session:
        user_repo_instance = UserRepositoryImpl(session) # Create concrete repo
        auth_service_instance = AuthenticationService(user_repo_instance) # Create auth service

        token_data = await auth_service_instance.decode_token(token)
        if token_data is None:
            print(f"WebSocket connection attempt with invalid token: {token[:20]}...")
            raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token")

        user_id_str = token_data.get("sub")
        token_type = token_data.get("type")

        if user_id_str is None or token_type != "access":
            print(f"WebSocket connection attempt: Invalid token type ('{token_type}') or missing user ID.")
            raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token type or payload")

        try:
            user_id = UUID(user_id_str)
        except (ValueError, InvalidUUIDError): # Catch more specific errors for UUID
            print(f"WebSocket connection attempt: Invalid user ID format in token ('{user_id_str}').")
            raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid user ID format in token")

        user = await user_repo_instance.get_by_id(user_id) # Fetch user from DB
        if user is None:
            print(f"WebSocket connection attempt: User ID '{user_id}' from token not found in DB.")
            raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")

        print(f"WebSocket authentication successful for user: {user.user_id}")
        return user


@router.websocket("/ws") # Path for the WebSocket connection
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for real-time communication.
    Authenticates user via token in query param (e.g., /ws?token=xxx).
    Manages connection lifecycle and handles incoming/outgoing messages.
    """
    token = websocket.query_params.get("token")
    current_user: Optional[DomainUser] = None

    try:
        # Authenticate the user for this WebSocket session
        current_user = await get_authenticated_user_for_ws(token=token)
        if not current_user:
            # get_authenticated_user_for_ws raises WebSocketDisconnect, so this check is redundant
            # but kept for clarity that connection proceeds only if current_user is valid.
            # This path should not be reached if auth fails as WebSocketDisconnect will be raised.
            print("WebSocket authentication failed, user is None. (Should have been caught by exception)")
            return # Connection will be closed by WebSocketDisconnect exception handling

        # If authentication successful, connect to the manager
        await manager.connect(websocket, current_user.user_id)

        # Keep the connection alive and listen for messages or handle server pushes
        while True:
            # This will wait until a message is received from the client or connection is closed.
            # If your WebSocket is primarily for server-to-client push, you might not need to
            # actively receive_text() here unless for keep-alive pings from client.
            # For many server-push applications, this loop might just `asyncio.sleep()` and check
            # for external triggers to send messages.
            data = await websocket.receive_text()
            print(f"Message received from user {current_user.user_id} (WebSocket {websocket}): {data}")
            # Example: Echoing message back or processing it
            # await manager.send_personal_message({"echo_response": data, "user": str(current_user.user_id)}, current_user.user_id)

    except WebSocketDisconnect as e:
        # This handles disconnections initiated by client or by our auth logic raising WebSocketDisconnect
        print(f"WebSocket disconnected for user {current_user.user_id if current_user else 'unknown'} (WebSocket {websocket}). Reason: {e.reason} (Code: {e.code})")
        if current_user:
            manager.disconnect(websocket, current_user.user_id)
    except Exception as e:
        # Catch any other unexpected errors during WebSocket handling
        error_code = status.WS_1011_INTERNAL_ERROR
        error_reason = "Internal server error"
        print(f"Unexpected error in WebSocket connection for user {current_user.user_id if current_user else 'unknown'} (WebSocket {websocket}): {type(e).__name__} - {e}")

        try:
            # Attempt to send a WebSocket close frame with an error code
            await websocket.close(code=error_code, reason=error_reason)
        except RuntimeError:
            # This can happen if the socket is already closed or in an invalid state
            print(f"RuntimeError while trying to close WebSocket {websocket} for user {current_user.user_id if current_user else 'unknown'}. Socket may be already closed.")
            pass

        # Ensure cleanup from ConnectionManager if user was identified and connected
        if current_user:
            manager.disconnect(websocket, current_user.user_id)
    finally:
        # Final cleanup attempt, though previous blocks should handle most cases.
        # This ensures that if current_user was identified and socket added to manager, it's removed.
        if current_user and websocket in manager.active_connections.get(current_user.user_id, set()):
            print(f"Final cleanup: Disconnecting WebSocket {websocket} for user {current_user.user_id}")
            manager.disconnect(websocket, current_user.user_id)
