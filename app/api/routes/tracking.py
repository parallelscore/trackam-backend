# app/api/routes/tracking.py

from datetime import datetime, timezone
from typing import List, Dict, Optional
from fastapi import  HTTPException, status, Query

from app.utils.logging_util import setup_logger
from app.services.auth_service import AuthService
from app.api.routes.base_router import RouterManager
from app.services.delivery_service import DeliveryService
from app.api.models.delivery_model import DeliveryStatusModel
from app.schemas.create_location_update_schema import CreateLocationUpdateSchema
from app.schemas.location_update_response_schema import LocationUpdateResponseSchema




class TrackingRouter:
    """
    Tracking Router for handling delivery tracking operations.
    """

    @classmethod
    def __init__(cls):

        cls.router_manager = RouterManager()
        cls.logger = setup_logger(__name__)
        cls.delivery_service = DeliveryService()
        cls.auth_service = AuthService()

        cls.router_manager.add_route(
            path='/tracking/{tracking_id}/location',
            handler_method=cls.add_location_update,
            methods=['POST'],
            tags=['tracking'],
            status_code=status.HTTP_200_OK
        )

        cls.router_manager.add_route(
            path='/tracking/{tracking_id}/locations',
            handler_method=cls.get_location_history,
            methods=['GET'],
            tags=['tracking'],
            status_code=status.HTTP_200_OK
        )

        cls.router_manager.add_route(
            path='/tracking/{tracking_id}/latest-location',
            handler_method=cls.get_latest_location,
            methods=['GET'],
            tags=['tracking'],
            status_code=status.HTTP_200_OK
        )

        cls.router_manager.add_route(
            path='/tracking/{tracking_id}/confirm-delivery',
            handler_method=cls.confirm_delivery,
            methods=['POST'],
            tags=['tracking'],
            status_code=status.HTTP_200_OK
        )

    @classmethod
    async def add_location_update(
            cls,
            tracking_id: str,
            location_data: CreateLocationUpdateSchema
    ):
        """
        Add a new location update for a delivery.

        Args:
            tracking_id: Delivery tracking ID
            location_data: Location update data

        Returns:
            LocationUpdateResponse: Created location update
        """
        try:
            location = await DeliveryService.add_location_update(
                tracking_id, location_data
            )
            return LocationUpdateResponseSchema(**location)
        except HTTPException as e:
            raise e
        except Exception as e:
            cls.logger.error(f"Error adding location update: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error adding location update: {str(e)}"
            )

    @classmethod
    async def get_location_history(
            cls,
            tracking_id: str,
            limit: int = Query(100, ge=1, le=1000)
    ):
        """
        Get location history for a delivery.

        Args:
            tracking_id: Delivery tracking ID
            limit: Maximum number of location updates to return

        Returns:
            List[LocationUpdateResponse]: Location history
        """
        try:
            # Check if delivery exists
            delivery = await DeliveryService.get_delivery_by_tracking_id(tracking_id)
            if not delivery:
                cls.logger.warning(f"Attempted to get locations for non-existent delivery: {tracking_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Delivery not found"
                )

            # Get location history
            locations = await DeliveryService.get_location_history(delivery["id"], limit)

            return [LocationUpdateResponseSchema(**loc) for loc in locations]
        except HTTPException as e:
            raise e
        except Exception as e:
            cls.logger.error(f"Error getting location history: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting location history: {str(e)}"
            )

    @classmethod
    async def get_latest_location(
            cls,
            tracking_id: str
    ):
        """
        Get the latest location update for a delivery.

        Args:
            tracking_id: Delivery tracking ID

        Returns:
            Optional[LocationUpdateResponse]: Latest location update or None
        """
        try:
            # Check if delivery exists
            delivery = await DeliveryService.get_delivery_by_tracking_id(tracking_id)
            if not delivery:
                cls.logger.warning(f"Attempted to get latest location for non-existent delivery: {tracking_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Delivery not found"
                )

            # Get latest location
            location = await DeliveryService.get_latest_location(delivery["id"])

            if not location:
                return None

            return LocationUpdateResponseSchema(**location)
        except HTTPException as e:
            raise e
        except Exception as e:
            cls.logger.error(f"Error getting latest location: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting latest location: {str(e)}"
            )

    @classmethod
    async def confirm_delivery(
            cls,
            tracking_id: str
    ):
        """
        Confirm package delivery by customer.

        Args:
            tracking_id: Delivery tracking ID

        Returns:
            Dict: Confirmation result
        """
        try:
            # Update delivery status to DELIVERED
            delivery = await DeliveryService.update_delivery_status(
                tracking_id, DeliveryStatusModel.DELIVERED
            )

            return {
                "success": True,
                "tracking_id": tracking_id,
                "status": delivery["status"],
                "confirmed_at": datetime.now(timezone.utc).isoformat(),
                "message": "Delivery confirmed successfully"
            }
        except HTTPException as e:
            raise e
        except Exception as e:
            cls.logger.error(f"Error confirming delivery: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error confirming delivery: {str(e)}"
            )
