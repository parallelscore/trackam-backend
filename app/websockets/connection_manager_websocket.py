import asyncio
from fastapi import WebSocket
from typing import Dict, Set, Any

from app.utils.logging_util import setup_logger


class ConnectionManagerWebsocket:
    """
    Manages WebSocket connections for real-time updates.

    This class handles:
    - Tracking connections by delivery ID
    - Broadcasting updates to connected clients
    - Managing connection state
    """

    @classmethod
    def __init__(cls):
        cls.logger = setup_logger(__name__)
        cls.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        cls.client_tracking_id: Dict[str, str] = {}
        cls.lock = asyncio.Lock()

    @classmethod
    async def connect(cls, websocket: WebSocket, tracking_id: str, client_id: str):
        """
        Connect a new client for a specific tracking ID.

        Args:
            websocket: WebSocket connection
            tracking_id: Delivery tracking ID
            client_id: Unique client identifier
        """
        await websocket.accept()

        async with cls.lock:
            # Initialize tracking_id key if not exists
            if tracking_id not in cls.active_connections:
                cls.active_connections[tracking_id] = {}

            # Store connection
            cls.active_connections[tracking_id][client_id] = websocket
            cls.client_tracking_id[client_id] = tracking_id

            # Log connection
            connections_count = len(cls.active_connections[tracking_id])
            cls.logger.info(f"New connection for tracking ID {tracking_id}. Total connections: {connections_count}")

            # Notify client of successful connection
            await cls.send_personal_message(
                {"type": "connection_status", "status": "connected", "tracking_id": tracking_id},
                websocket
            )
    @classmethod
    async def disconnect(cls, client_id: str):
        """
        Disconnect a client.

        Args:
            client_id: Unique client identifier
        """
        async with cls.lock:
            # Get tracking ID for this client
            tracking_id = cls.client_tracking_id.get(client_id)
            if not tracking_id:
                return

            # Remove connection
            if tracking_id in cls.active_connections:
                if client_id in cls.active_connections[tracking_id]:
                    del cls.active_connections[tracking_id][client_id]

                # Clean up empty tracking IDs
                if not cls.active_connections[tracking_id]:
                    del cls.active_connections[tracking_id]

            # Clean up client mapping
            if client_id in cls.client_tracking_id:
                del cls.client_tracking_id[client_id]

            cls.logger.info(f"Client {client_id} disconnected from tracking ID {tracking_id}")

    @staticmethod
    async def send_personal_message(message: Any, websocket: WebSocket):
        """
        Send a message to a specific client.

        Args:
            message: Message to send (will be converted to JSON)
            websocket: WebSocket connection
        """
        if isinstance(message, dict) or isinstance(message, list):
            await websocket.send_json(message)
        else:
            await websocket.send_text(str(message))

    @classmethod
    async def broadcast(cls, tracking_id: str, message: Any):
        """
        Broadcast a message to all clients connected to a specific tracking ID.

        Args:
            tracking_id: Delivery tracking ID
            message: Message to broadcast (will be converted to JSON)
        """
        if tracking_id not in cls.active_connections:
            return

        # Copy connection dict to avoid concurrent modification
        connections = list(cls.active_connections[tracking_id].items())

        for client_id, websocket in connections:
            try:
                await cls.send_personal_message(message, websocket)
            except Exception as e:
                cls.logger.error(f"Error sending message to client {client_id}: {str(e)}")
                # Connection might be broken, disconnect client
                await cls.disconnect(client_id)

    @classmethod
    def get_connections_count(cls, tracking_id: str) -> int:
        """Get the number of active connections for a tracking ID."""
        if tracking_id not in cls.active_connections:
            return 0
        return len(cls.active_connections[tracking_id])

    @classmethod
    def get_all_tracking_ids(cls) -> Set[str]:
        """Get all active tracking IDs."""
        return set(cls.active_connections.keys())


# Create a singleton instance
connection_manager_websocket = ConnectionManagerWebsocket()