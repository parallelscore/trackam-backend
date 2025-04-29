# app/api/routes/websocket.py
import uuid
import json
import asyncio
from fastapi import status
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect

from app.utils.logging_util import setup_logger
from app.api.routes.base_router import RouterManager
from app.websockets.events_websocket import EventsWebsocket
from app.websockets.connection_manager_websocket import connection_manager_websocket


class WebSocketRouter:
    """
    WebSocket router for handling real-time delivery updates.

    This router handles:
    - WebSocket connection establishment
    - Real-time updates between clients (vendor, rider, customer)
    - Graceful disconnection
    """

    def __init__(self):
        """
        Initialize the WebSocket router.
        """
        self.logger = setup_logger(__name__)
        self.router_manager = RouterManager()
        self.events_websocket = EventsWebsocket()

        # Add WebSocket route
        self.router_manager.add_route(
            path="/ws/delivery/{tracking_id}",
            handler_method=self.websocket_endpoint,
            methods=["GET"],
            tags=["websocket"],
            status_code=status.HTTP_200_OK
        )

    async def websocket_endpoint(self, websocket: WebSocket, tracking_id: str):
        """
        WebSocket endpoint for real-time delivery updates.

        This endpoint handles:
        - Connection establishment
        - Real-time updates between clients (vendor, rider, customer)
        - Graceful disconnection

        Args:
            websocket: The WebSocket connection
            tracking_id: The delivery tracking ID
        """
        # Generate unique client ID for this connection
        client_id = str(uuid.uuid4())

        try:
            # Accept connection
            await connection_manager_websocket.connect(websocket, tracking_id, client_id)
            self.logger.info(f"WebSocket connection established for tracking ID: {tracking_id}, client ID: {client_id}")

            # Notify about connection count
            await self.events_websocket.send_connection_info(tracking_id)

            # Main WebSocket loop
            while True:
                # Set a timeout for receiving messages (30 seconds)
                try:
                    # Wait for messages from client with timeout
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                    # Process received message
                    try:
                        message_data = json.loads(data)

                        # Process the message based on its type
                        response = await self.events_websocket.process_message(message_data)

                        # Send response back to the client
                        if response:
                            await websocket.send_json(response)

                    except json.JSONDecodeError:
                        self.logger.error(f"Invalid JSON received from client {client_id}")
                        await websocket.send_json({
                            "error": "Invalid JSON format"
                        })
                    except Exception as e:
                        self.logger.error(f"Error processing message from client {client_id}: {str(e)}")
                        await websocket.send_json({
                            "error": "Error processing message",
                            "detail": str(e)
                        })

                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    try:
                        await websocket.send_json({
                            "type": "ping",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                    except Exception as e:
                        self.logger.error(f"Error sending ping to client {client_id}: {str(e)}")
                        # Connection might be broken, exit the loop
                        break

        except WebSocketDisconnect:
            # Handle client disconnect
            self.logger.info(f"WebSocket client disconnected: {client_id}")
            await connection_manager_websocket.disconnect(client_id)
            await self.events_websocket.send_connection_info(tracking_id)

        except Exception as e:
            # Handle any other exceptions
            self.logger.error(f"WebSocket error for client {client_id}: {str(e)}")
            try:
                await connection_manager_websocket.disconnect(client_id)
                await self.events_websocket.send_connection_info(tracking_id)
            except Exception as disconnect_error:
                self.logger.error(f"Error during disconnect cleanup: {str(disconnect_error)}")
