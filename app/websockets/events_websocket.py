# app/websockets/events_websocket.py

from typing import Dict, Any
from datetime import datetime, timezone

from app.utils.logging_util import setup_logger
from app.websockets.connection_manager_websocket import connection_manager_websocket


class EventsWebsocket:

    @classmethod
    def __int__(cls):

        cls.logger = setup_logger(__name__)

    @classmethod
    async def process_location_update(cls, data: Dict[str, Any]):
        """
        Process location update from driver.

        Args:
            data: Location update data
        """
        try:
            # Extract tracking ID
            tracking_id = data.get("tracking_id")
            if not tracking_id:
                cls.logger.error("Missing tracking_id in location update")
                return

            # Extract location data
            location_data = data.get("location", {})
            if not location_data:
                cls.logger.error("Missing location data in update")
                return

            # Create location update schema
            location_update = CreateLocationUpdateSchema(
                latitude=location_data.get("latitude"),
                longitude=location_data.get("longitude"),
                accuracy=location_data.get("accuracy"),
                speed=location_data.get("speed"),
                heading=location_data.get("heading"),
                altitude=location_data.get("altitude"),
                battery_level=location_data.get("battery_level"),
                is_moving=location_data.get("is_moving", True),
                metadata=location_data.get("metadata")
            )

            # Save location update to database
            location = await cls.delivery_service.add_location_update(
                tracking_id, location_update
            )

            # Prepare data for broadcasting
            broadcast_data = {
                "type": "location_update",
                "tracking_id": tracking_id,
                "location": {
                    "latitude": location["latitude"],
                    "longitude": location["longitude"],
                    "accuracy": location["accuracy"],
                    "speed": location["speed"],
                    "heading": location["heading"],
                    "timestamp": location["created_at"].isoformat() if isinstance(location["created_at"], datetime) else location["created_at"],
                    "battery_level": location["battery_level"],
                    "is_moving": location["is_moving"]
                }
            }

            # Broadcast to all clients tracking this delivery
            await connection_manager_websocket.broadcast(tracking_id, broadcast_data)
            cls.logger.info(f"Location update broadcasted for tracking ID: {tracking_id}")

            return location

        except Exception as e:
            cls.logger.error(f"Error processing location update: {str(e)}")
            return None

    @classmethod
    async def process_status_update(cls, data: Dict[str, Any]):
        """
        Process delivery status update.

        Args:
            data: Status update data
        """
        try:
            # Extract tracking ID
            tracking_id = data.get("tracking_id")
            if not tracking_id:
                cls.logger.error("Missing tracking_id in status update")
                return

            # Extract status
            status_value = data.get("status")
            if not status_value:
                cls.logger.error("Missing status in update")
                return

            try:
                status = DeliveryStatusModel(status_value)
            except ValueError:
                cls.logger.error(f"Invalid status value: {status_value}")
                return

            # Update delivery status in database
            delivery = await DeliveryService.update_delivery_status(
                tracking_id, status
            )

            # Prepare data for broadcasting
            broadcast_data = {
                "type": "status_update",
                "tracking_id": tracking_id,
                "status": status.value,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Broadcast to all clients tracking this delivery
            await connection_manager_websocket.broadcast(tracking_id, broadcast_data)
            cls.logger.info(f"Status update broadcasted for tracking ID: {tracking_id}")

            return delivery

        except Exception as e:
            cls.logger.error(f"Error processing status update: {str(e)}")
            return None

    @classmethod
    async def process_delivery_confirmation(cls, data: Dict[str, Any]):
        """
        Process delivery confirmation from customer.

        Args:
            data: Confirmation data
        """
        try:
            # Extract tracking ID
            tracking_id = data.get("tracking_id")
            if not tracking_id:
                cls.logger.error("Missing tracking_id in delivery confirmation")
                return

            # Update delivery status to DELIVERED
            delivery = await DeliveryService.update_delivery_status(
                tracking_id, DeliveryStatusModel.DELIVERED
            )

            # Prepare data for broadcasting
            broadcast_data = {
                "type": "delivery_confirmation",
                "tracking_id": tracking_id,
                "status": DeliveryStatusModel.DELIVERED.value,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Broadcast to all clients tracking this delivery
            await connection_manager_websocket.broadcast(tracking_id, broadcast_data)
            cls.logger.info(f"Delivery confirmation broadcasted for tracking ID: {tracking_id}")

            return delivery

        except Exception as e:
            cls.logger.error(f"Error processing delivery confirmation: {str(e)}")
            return None

    @classmethod
    async def process_message(cls, message_data: Dict[str, Any]):
        """
        Process WebSocket message based on its type.

        Args:
            message_data: Message data

        Returns:
            Dict or None: Response data or None
        """
        message_type = message_data.get("type")
        if not message_type:
            cls.logger.error("Missing message type in WebSocket message")
            return {"error": "Missing message type"}

        try:
            if message_type == "location_update":
                return await cls.process_location_update(message_data)

            elif message_type == "status_update":
                return await cls.process_status_update(message_data)

            elif message_type == "delivery_confirmation":
                return await cls.process_delivery_confirmation(message_data)

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
    async def send_connection_info(cls, tracking_id: str):
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
