# app/api/routes/customer.py
from datetime import datetime, timezone
from fastapi import HTTPException, status

from app.utils.logging_util import setup_logger
from app.api.routes.base_router import RouterManager
from app.api.models.delivery_model import DeliveryModel
from app.utils.database_operator_util import database_operator_util
from app.websockets.events_websocket import EventsWebsocket


class CustomerRouter:
    """
    Router for customer-related endpoints.
    """

    def __init__(self):
        self.router_manager = RouterManager()
        self.logger = setup_logger(__name__)

        # Get public delivery by tracking ID (no auth required)
        self.router_manager.add_route(
            path="/customer/track/{tracking_id}",
            handler_method=self.get_public_delivery,
            methods=["GET"],
            tags=["customer"],
            status_code=status.HTTP_200_OK
        )

        # Confirm delivery receipt
        self.router_manager.add_route(
            path="/customer/confirm/{tracking_id}",
            handler_method=self.confirm_delivery,
            methods=["POST"],
            tags=["customer"],
            status_code=status.HTTP_200_OK
        )

    async def get_public_delivery(self, tracking_id: str):
        """
        Get public delivery information by tracking ID without authentication.
        This allows customers to track their deliveries with just the tracking ID.
        """
        try:
            # Get the delivery
            delivery = await database_operator_util.find_one(
                DeliveryModel,
                DeliveryModel.tracking_id == tracking_id
            )

            if not delivery:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Delivery not found"
                )

            # Create a sanitized version for public access
            public_delivery = {
                "tracking_id": delivery.get("tracking_id"),
                "status": delivery.get("status"),
                "created_at": delivery.get("created_at"),
                "updated_at": delivery.get("updated_at"),
                "estimated_delivery_time": delivery.get("estimated_delivery_time"),

                # Customer info (limited)
                "customer": {
                    "name": delivery.get("customer_name"),
                    "address": delivery.get("customer_address"),
                },

                # Rider info (limited)
                "rider": {
                    "name": delivery.get("rider_name"),
                    "current_location": delivery.get("rider_current_location"),
                } if delivery.get("rider_name") else None,

                # Package info
                "package": {
                    "description": delivery.get("package_description"),
                    "size": delivery.get("package_size"),
                    "special_instructions": delivery.get("package_special_instructions"),
                },

                # Tracking info (limited)
                "tracking": {
                    "active": delivery.get("is_tracking_active"),
                }
            }

            return public_delivery

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error retrieving public delivery: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve delivery information"
            )

    async def confirm_delivery(self, tracking_id: str):
        """
        Confirm delivery receipt by customer.
        """
        try:
            # Get the delivery
            delivery = await database_operator_util.find_one(
                DeliveryModel,
                DeliveryModel.tracking_id == tracking_id
            )

            if not delivery:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Delivery not found"
                )

            # Check if delivery is in a state that can be confirmed
            if delivery.get('status') != 'in_progress':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot confirm delivery with status '{delivery.get('status')}'"
                )

            # Update delivery status to 'completed' and deactivate tracking
            update_data = {
                "status": "completed",
                "is_tracking_active": False,
                "updated_at": datetime.now(timezone.utc)
            }

            await database_operator_util.update(
                model=DeliveryModel,
                filter_by={"tracking_id": tracking_id},
                data=update_data
            )

            # Get updated delivery
            updated_delivery = await database_operator_util.find_one(
                DeliveryModel,
                DeliveryModel.tracking_id == tracking_id
            )

            # Broadcast confirmation via WebSocket
            await EventsWebsocket.process_delivery_confirmation({
                "tracking_id": tracking_id
            })

            return {
                "success": True,
                "message": "Delivery confirmed successfully",
                "delivery": updated_delivery
            }

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error confirming delivery: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to confirm delivery"
            )