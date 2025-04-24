# app/api/routes/websocket.py
import uuid
import json
from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Depends

from app.utils.logging_util import setup_logger
from app.websockets.events_websocket import EventsWebsocket
from app.websockets.connection_manager_websocket import connection_manager_websocket


logger = setup_logger(__name__)
router = APIRouter()


@router.websocket("/ws/delivery/{tracking_id}")
async def websocket_endpoint(websocket: WebSocket, tracking_id: str):
    """
    WebSocket endpoint for real-time delivery updates.
    """
    # Generate unique client ID for this connection
    client_id = str(uuid.uuid4())

    try:
        # Accept connection
        await connection_manager_websocket.connect(websocket, tracking_id, client_id)
        logger.info(f"WebSocket connection established for tracking ID: {tracking_id}, client ID: {client_id}")

        # Notify about connection count
        await EventsWebsocket.send_connection_info(tracking_id)

        # Main WebSocket loop
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()

            # Process received message
            try:
                message_data = json.loads(data)

                # Process the message based on its type
                response = await EventsWebsocket.process_message(message_data)

                # Send response back to the client
                if response:
                    await websocket.send_json(response)

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from client {client_id}")
                await websocket.send_json({
                    "error": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"Error processing message from client {client_id}: {str(e)}")
                await websocket.send_json({
                    "error": "Error processing message"
                })

    except WebSocketDisconnect:
        # Handle client disconnect
        logger.info(f"WebSocket client disconnected: {client_id}")
        await connection_manager_websocket.disconnect(client_id)
        await EventsWebsocket.send_connection_info(tracking_id)

    except Exception as e:
        # Handle any other exceptions
        logger.error(f"WebSocket error: {str(e)}")
        await connection_manager_websocket.disconnect(client_id)
