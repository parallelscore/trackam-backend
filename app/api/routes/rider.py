# app/api/routes/rider.py
import json
from datetime import datetime, timezone
from fastapi import HTTPException, status

from app.utils.logging_util import setup_logger
from app.api.routes.base_router import RouterManager
from app.api.models.delivery_model import DeliveryModel
from app.schemas.rider_schema import OtpVerification, LocationUpdate
from app.utils.database_operator_util import database_operator_util
from app.websockets.events_websocket import EventsWebsocket


class RiderRouter:
    """
    Router for rider-related endpoints.
    All endpoints are public - no authentication required.
    Riders authenticate using OTP verification per delivery.
    """

    def __init__(self):
        self.router_manager = RouterManager()
        self.logger = setup_logger(__name__)

        # Verify rider OTP (no auth required)
        self.router_manager.add_route(
            path="/rider/verify-otp",
            handler_method=self.verify_otp,
            methods=["POST"],
            tags=["rider"],
            status_code=status.HTTP_200_OK
        )

        # Accept delivery (no auth required)
        self.router_manager.add_route(
            path="/rider/accept/{tracking_id}",
            handler_method=self.accept_delivery,
            methods=["POST"],
            tags=["rider"],
            status_code=status.HTTP_200_OK
        )

        # Decline or cancel delivery (no auth required)
        self.router_manager.add_route(
            path="/rider/decline/{tracking_id}",
            handler_method=self.decline_delivery,
            methods=["POST"],
            tags=["rider"],
            status_code=status.HTTP_200_OK
        )

        # Start tracking a delivery (no auth required)
        self.router_manager.add_route(
            path="/rider/start-tracking/{tracking_id}",
            handler_method=self.start_tracking,
            methods=["POST"],
            tags=["rider"],
            status_code=status.HTTP_200_OK
        )

        # Update rider location (no auth required)
        self.router_manager.add_route(
            path="/rider/update-location",
            handler_method=self.update_location,
            methods=["POST"],
            tags=["rider"],
            status_code=status.HTTP_200_OK
        )

        # Complete a delivery (no auth required)
        self.router_manager.add_route(
            path="/rider/complete/{tracking_id}",
            handler_method=self.complete_delivery,
            methods=["POST"],
            tags=["rider"],
            status_code=status.HTTP_200_OK
        )

    async def verify_otp(self, data: OtpVerification):
        """
        Verify rider OTP for a delivery.
        No authentication required - OTP serves as the authentication method.
        """
        try:
            # Get the delivery
            delivery = await database_operator_util.find_one(
                DeliveryModel,
                DeliveryModel.tracking_id == data.tracking_id
            )

            if not delivery:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Delivery not found"
                )

            # Check if OTP is correct
            if delivery.get('tracking').get('otp') != data.otp:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid OTP"
                )

            # Check if OTP is expired
            otp_expiry = delivery.get('tracking').get('otp_expiry')

            if not otp_expiry:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OTP has expired"
                )

            # Parse the expiry time and ensure it's timezone-aware
            expiry_datetime = datetime.fromisoformat(otp_expiry)
            if expiry_datetime.tzinfo is None:
                expiry_datetime = expiry_datetime.replace(tzinfo=timezone.utc)

            # Now compare with the current UTC time
            if datetime.now(timezone.utc) > expiry_datetime:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OTP has expired"
                )

            # Update delivery status to 'accepted'
            update_data = {
                "status": "accepted",
                "updated_at": datetime.now(timezone.utc)
            }

            await database_operator_util.update(
                model=DeliveryModel,
                filter_by={"tracking_id": data.tracking_id},
                data=update_data
            )

            # Get updated delivery
            updated_delivery = await database_operator_util.find_one(
                DeliveryModel,
                DeliveryModel.tracking_id == data.tracking_id
            )

            # Broadcast status update via WebSocket
            await EventsWebsocket.process_status_update({
                "tracking_id": data.tracking_id,
                "status": "accepted"
            })

            return {
                "success": True,
                "message": "OTP verified successfully",
                "delivery": updated_delivery
            }

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error verifying OTP: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to verify OTP"
            )

    async def accept_delivery(self, tracking_id: str):
        """
        Accept a delivery assignment (no authentication required).
        """
        try:
            # Check if delivery exists
            delivery = await database_operator_util.find_one(
                DeliveryModel,
                DeliveryModel.tracking_id == tracking_id
            )

            if not delivery:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Delivery not found"
                )

            # Check if delivery is in a state that can be accepted
            if delivery.get('status') not in ['created', 'assigned']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot accept delivery with status '{delivery.get('status')}'"
                )

            # Update delivery to the assigned state (it will be accepted after OTP verification)
            update_data = {
                "status": "assigned",
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

            # Broadcast status update via WebSocket
            await EventsWebsocket.process_status_update({
                "tracking_id": tracking_id,
                "status": "assigned"
            })

            return {
                "success": True,
                "message": "Delivery assignment accepted",
                "delivery": updated_delivery
            }

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error accepting delivery: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to accept delivery"
            )

    async def decline_delivery(self, tracking_id: str):
        """
        Decline a delivery assignment (no authentication required).
        """
        try:
            # Check if delivery exists
            delivery = await database_operator_util.find_one(
                DeliveryModel,
                DeliveryModel.tracking_id == tracking_id
            )

            if not delivery:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Delivery not found"
                )

            # Check if delivery is in a state that can be declined
            if delivery.get('status') not in ['created', 'assigned']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot decline delivery with status '{delivery.get('status')}'"
                )

            # Update delivery to cancelled state
            update_data = {
                "status": "cancelled",
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

            # Broadcast status update via WebSocket
            await EventsWebsocket.process_status_update({
                "tracking_id": tracking_id,
                "status": "cancelled"
            })

            return {
                "success": True,
                "message": "Delivery declined successfully",
                "delivery": updated_delivery
            }

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error declining delivery: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to decline delivery"
            )

    async def start_tracking(self, tracking_id: str):
        """
        Start tracking a delivery (no authentication required).
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

            # Check if delivery is in a state that can be tracked
            if delivery.get('status') != 'accepted':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot start tracking delivery with status '{delivery.get('status')}'"
                )

            # Update delivery status to 'in_progress' and activate tracking
            update_data = {
                "status": "in_progress",
                "is_tracking_active": True,
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

            # Broadcast status update via WebSocket
            await EventsWebsocket.process_status_update({
                "tracking_id": tracking_id,
                "status": "in_progress"
            })

            return {
                "success": True,
                "message": "Tracking started successfully",
                "delivery": updated_delivery
            }

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error starting tracking: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start tracking"
            )

    async def update_location(self, location: LocationUpdate):
        """
        Update rider's current location for a delivery (no authentication required).
        """
        try:
            # Get the delivery
            delivery = await database_operator_util.find_one(
                DeliveryModel,
                DeliveryModel.tracking_id == location.tracking_id
            )

            if not delivery:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Delivery not found"
                )

            self.logger.info('delivery: %s', delivery)

            # Check if tracking is active
            if not delivery.get('tracking').get('active'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tracking is not active for this delivery"
                )

            # Build location data
            location_data = {
                "latitude": location.latitude,
                "longitude": location.longitude,
                "accuracy": location.accuracy,
                "speed": location.speed,
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
            }

            # Append to location history
            location_history = delivery.get('location_history', [])
            location_history.append(location_data)

            # Update delivery with new location data
            update_data = {
                "rider_current_location": json.dumps(location_data),
                "location_history": json.dumps(location_history),
                "updated_at": datetime.now(timezone.utc)
            }

            await database_operator_util.update(
                model=DeliveryModel,
                filter_by={"tracking_id": location.tracking_id},
                data=update_data
            )

            # Get updated delivery
            updated_delivery = await database_operator_util.find_one(
                DeliveryModel,
                DeliveryModel.tracking_id == location.tracking_id
            )

            # Process location update via WebSocket
            await EventsWebsocket.process_location_update({
                "tracking_id": location.tracking_id,
                "location": location_data
            })

            return {
                "success": True,
                "message": "Location updated successfully",
                "delivery": updated_delivery
            }

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error updating location: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update location"
            )

    async def complete_delivery(self, tracking_id: str):
        """
        Mark a delivery as completed by the rider (no authentication required).
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

            # Check if delivery is in a state that can be completed
            if delivery.get('status') != 'in_progress':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot complete delivery with status '{delivery.get('status')}'"
                )

            # Update the delivery status to 'completed' and deactivate tracking
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

            # Broadcast status update via WebSocket
            await EventsWebsocket.process_status_update({
                "tracking_id": tracking_id,
                "status": "completed"
            })

            return {
                "success": True,
                "message": "Delivery completed successfully",
                "delivery": updated_delivery
            }

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error completing delivery: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to complete delivery"
            )