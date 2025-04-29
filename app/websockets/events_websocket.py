# app/websockets/events_websocket.py
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.utils.logging_util import setup_logger
from app.api.models.delivery_model import DeliveryModel
from app.utils.database_operator_util import database_operator_util
from app.websockets.connection_manager_websocket import connection_manager_websocket


class EventsWebsocket:

    @classmethod
    def __init__(cls):
        """
        Initialize the EventsWebsocket class.
        """
        cls.logger = setup_logger(__name__)

    @classmethod
    async def process_location_update(cls, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process location update from driver.

        Args:
            data: Location update data with tracking_id and location details

        Returns:
            Optional[Dict[str, Any]]: Processed location data or None if error
        """
        try:
            # Extract tracking ID
            tracking_id = data.get("tracking_id")
            if not tracking_id:
                cls.logger.error("Missing tracking_id in location update")
                return None

            # Extract location data
            location_data = data.get("location", {})
            if not location_data:
                cls.logger.error("Missing location data in update")
                return None

            # Get the delivery
            delivery = await database_operator_util.find_one(
                DeliveryModel,
                DeliveryModel.tracking_id == tracking_id
            )

            if not delivery:
                cls.logger.error(f"Delivery not found for tracking ID: {tracking_id}")
                return None

            # Update location data in database
            location_history = delivery.get("location_history", [])

            # Add timestamp if not provided
            if "timestamp" not in location_data:
                location_data["timestamp"] = int(datetime.now(timezone.utc).timestamp() * 1000)

            # Append to location history
            location_history.append(location_data)

            # Update delivery with new location
            await database_operator_util.update(
                model=DeliveryModel,
                filter_by={"tracking_id": tracking_id},
                data={
                    "rider_current_location": location_data,
                    "location_history": location_history,
                    "updated_at": datetime.now(timezone.utc)
                }
            )

            # Prepare data for broadcasting
            broadcast_data = {
                "type": "location_update",
                "tracking_id": tracking_id,
                "location": {
                    "latitude": location_data.get("latitude"),
                    "longitude": location_data.get("longitude"),
                    "accuracy": location_data.get("accuracy"),
                    "speed": location_data.get("speed"),
                    "heading": location_data.get("heading", 0),
                    "timestamp": location_data.get("timestamp"),
                    "battery_level": location_data.get("battery_level", 100),
                    "is_moving": location_data.get("is_moving", True)
                }
            }

            # Broadcast to all clients tracking this delivery
            await connection_manager_websocket.broadcast(tracking_id, broadcast_data)
            cls.logger.info(f"Location update broadcasted for tracking ID: {tracking_id}")

            return broadcast_data

        except Exception as e:
            cls.logger.error(f"Error processing location update: {str(e)}")
            return None

    @classmethod
    async def process_status_update(cls, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process delivery status update.

        Args:
            data: Status update data with tracking_id and status

        Returns:
            Optional[Dict[str, Any]]: Processed status data or None if error
        """
        try:
            # Extract tracking ID
            tracking_id = data.get("tracking_id")
            if not tracking_id:
                cls.logger.error("Missing tracking_id in status update")
                return None

            # Extract status
            status = data.get("status")
            if not status:
                cls.logger.error("Missing status in update")
                return None

            # Validate status value
            valid_statuses = ['created', 'assigned', 'accepted', 'in_progress', 'completed', 'cancelled']
            if status not in valid_statuses:
                cls.logger.error(f"Invalid status value: {status}")
                return None

            # Update delivery status in database
            await database_operator_util.update(
                model=DeliveryModel,
                filter_by={"tracking_id": tracking_id},
                data={
                    "status": status,
                    "updated_at": datetime.now(timezone.utc)
                }
            )

            # Prepare data for broadcasting
            broadcast_data = {
                "type": "status_update",
                "tracking_id": tracking_id,
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Broadcast to all clients tracking this delivery
            await connection_manager_websocket.broadcast(tracking_id, broadcast_data)
            cls.logger.info(f"Status update broadcasted for tracking ID: {tracking_id}")

            return broadcast_data

        except Exception as e:
            cls.logger.error(f"Error processing status update: {str(e)}")
            return None

    @classmethod
    async def process_delivery_confirmation(cls, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process delivery confirmation from customer.

        Args:
            data: Confirmation data with tracking_id

        Returns:
            Optional[Dict[str, Any]]: Processed confirmation data or None if error
        """
        try:
            # Extract tracking ID
            tracking_id = data.get("tracking_id")
            if not tracking_id:
                cls.logger.error("Missing tracking_id in delivery confirmation")
                return None

            # Update delivery status to DELIVERED
            await database_operator_util.update(
                model=DeliveryModel,
                filter_by={"tracking_id": tracking_id},
                data={
                    "status": "completed",
                    "is_tracking_active": False,
                    "updated_at": datetime.now(timezone.utc)
                }
            )

            # Prepare data for broadcasting
            broadcast_data = {
                "type": "delivery_confirmation",
                "tracking_id": tracking_id,
                "status": "completed",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Broadcast to all clients tracking this delivery
            await connection_manager_websocket.broadcast(tracking_id, broadcast_data)
            cls.logger.info(f"Delivery confirmation broadcasted for tracking ID: {tracking_id}")

            return broadcast_data

        except Exception as e:
            cls.logger.error(f"Error processing delivery confirmation: {str(e)}")
            return None

    @classmethod
    async def process_message(cls, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process WebSocket message based on its type.

        Args:
            message_data: Message data with type and other details

        Returns:
            Dict[str, Any]: Response data or error message
        """
        message_type = message_data.get("type")
        if not message_type:
            cls.logger.error("Missing message type in WebSocket message")
            return {"error": "Missing message type"}

        try:
            if message_type == "location_update":
                result = await cls.process_location_update(message_data)
                return result or {"error": "Failed to process location update"}

            elif message_type == "status_update":
                result = await cls.process_status_update(message_data)
                return result or {"error": "Failed to process status update"}

            elif message_type == "delivery_confirmation":
                result = await cls.process_delivery_confirmation(message_data)
                return result or {"error": "Failed to process delivery confirmation"}

            elif message_type == "ping":
                # Simple ping to keep connection alive
                return {"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()}

            else:
                cls.logger.warning(f"Unknown message type: {message_type}")
                return {"error": f"Unknown message type: {message_type}"}

        except Exception as e:
            cls.logger.error(f"Error processing message: {str(e)}")
            return {"error": f"Error processing message: {str(e)}"}

    @classmethod
    async def send_connection_info(cls, tracking_id: str) -> None:
        """
        Send connection count info to all clients tracking a delivery.

        Args:
            tracking_id: Delivery tracking ID
        """
        connections_count = connection_manager_websocket.get_connections_count(tracking_id)

        broadcast_data = {
            "type": "connections_info",
            "tracking_id": tracking_id,
            "connections_count": connections_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        await connection_manager_websocket.broadcast(tracking_id, broadcast_data)
        cls.logger.info(f"Connection info sent for tracking ID: {tracking_id}, count: {connections_count}")