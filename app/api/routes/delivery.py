# app/api/routes/delivery.py

import math
from typing import Optional
from fastapi import status, HTTPException, Query

from app.utils.logging_util import setup_logger
from app.services.auth_service import AuthService
from app.api.routes.base_router import RouterManager
from app.services.delivery_service import DeliveryService
from app.api.models.delivery_model import DeliveryStatusModel
from app.schemas.create_delivery_schema import CreateDeliverySchema
from app.schemas.delivery_response_schema import DeliveryResponseSchema
from app.schemas.delivery_list_response_schema import DeliveryListResponseSchema
from app.schemas.delivery_status_update_schema import DeliveryStatusUpdateSchema


class DeliveryRouter:

    @classmethod
    def __init__(cls):

        cls.router_manager = RouterManager()
        cls.logger = setup_logger(__name__)
        cls.delivery_service = DeliveryService()
        cls.auth_service = AuthService()

        cls.router_manager.add_route(
            path='/deliveries',
            handler_method=cls.create_delivery,
            methods=['POST'],
            tags=['delivery'],
            status_code=status.HTTP_200_OK
        )

        cls.router_manager.add_route(
            path='/deliveries',
            handler_method=cls.get_deliveries,
            methods=['GET'],
            tags=['delivery'],
            status_code=status.HTTP_200_OK
        )

        cls.router_manager.add_route(
            path='/deliveries/{delivery_id}',
            handler_method=cls.get_delivery,
            methods=['GET'],
            tags=['delivery'],
            status_code=status.HTTP_200_OK
        )

        cls.router_manager.add_route(
            path='/deliveries/tracking/{tracking_id}',
            handler_method=cls.get_delivery_by_tracking_id,
            methods=['GET'],
            tags=['delivery'],
            status_code=status.HTTP_200_OK
        )

        cls.router_manager.add_route(
            path='/deliveries/{tracking_id}/status',
            handler_method=cls.update_delivery_status,
            methods=['PUT'],
            tags=['delivery'],
            status_code=status.HTTP_200_OK
        )


    @classmethod
    async def create_delivery(
            cls,
            delivery_data: CreateDeliverySchema
    ):
        """
        Create a new delivery.

        Args:
            delivery_data: Delivery creation data

        Returns:
            DeliveryResponse: Created delivery
        """
        try:
            delivery = await cls.delivery_service.create_delivery(delivery_data)

            # Construct response
            response = DeliveryResponseSchema(
                **delivery,
                vendor=delivery.get("vendor"),
                driver=delivery.get("driver"),
                customer=delivery.get("customer"),
                latest_location=delivery.get("latest_location")
            )

            return response
        except HTTPException as e:
            # Re-raise HTTPExceptions
            raise
        except Exception as e:
            cls.logger.error(f"Error creating delivery: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating delivery: {str(e)}"
            )

    @classmethod
    async def get_deliveries(
            cls,
            delivery_status: Optional[DeliveryStatusModel] = None,
            vendor_id: Optional[int] = None,
            driver_id: Optional[int] = None,
            customer_id: Optional[int] = None,
            page: int = Query(1, ge=1),
            size: int = Query(10, ge=1, le=100)
    ):
        """
        Get deliveries with optional filtering and pagination.

        Args:
            delivery_status: Filter by delivery status
            vendor_id: Filter by vendor ID
            driver_id: Filter by driver ID
            customer_id: Filter by customer ID
            page: Page number
            size: Page size

        Returns:
            DeliveryListResponse: List of deliveries with pagination info
        """
        try:
            # Calculate skip for pagination
            skip = (page - 1) * size

            # Get deliveries with total count
            deliveries, total = await DeliveryService.get_deliveries(
                skip=skip,
                limit=size,
                status=delivery_status,
                vendor_id=vendor_id,
                driver_id=driver_id,
                customer_id=customer_id
            )

            # Calculate total pages
            pages = math.ceil(total / size) if total > 0 else 1

            # Construct response items
            items = []
            for delivery in deliveries:
                # Fetch related data
                vendor = delivery.get("vendor", {})
                driver = delivery.get("driver", {})
                customer = delivery.get("customer", {})
                latest_location = None

                # Try to get the latest location
                if "id" in delivery:
                    latest_location = await DeliveryService.get_latest_location(delivery["id"])

                # Create response item
                response_item = DeliveryResponseSchema(
                    **delivery,
                    vendor=vendor,
                    driver=driver,
                    customer=customer,
                    latest_location=latest_location
                )
                items.append(response_item)

            return DeliveryListResponseSchema(
                items=items,
                total=total,
                page=page,
                size=size,
                pages=pages
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            cls.logger.error(f"Error getting deliveries: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting deliveries: {str(e)}"
            )

    @classmethod
    async def get_delivery(
            cls,
            delivery_id: int
    ):
        """
        Get a delivery by ID.

        Args:
            delivery_id: Delivery ID

        Returns:
            DeliveryResponse: Delivery details
        """
        try:
            delivery = await DeliveryService.get_delivery_by_id(delivery_id)

            if not delivery:
                cls.logger.warning(f"Delivery not found with ID: {delivery_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Delivery not found"
                )

            # Get related data
            vendor = delivery.get("vendor", {})
            driver = delivery.get("driver", {})
            customer = delivery.get("customer", {})
            latest_location = await DeliveryService.get_latest_location(delivery["id"])

            # Construct response
            response = DeliveryResponseSchema(
                **delivery,
                vendor=vendor,
                driver=driver,
                customer=customer,
                latest_location=latest_location
            )

            return response
        except HTTPException as e:
            raise e
        except Exception as e:
            cls.logger.error(f"Error getting delivery: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting delivery: {str(e)}"
            )

    @classmethod
    async def get_delivery_by_tracking_id(
            cls,
            tracking_id: str
    ):
        """
        Get a delivery by tracking ID.

        Args:
            tracking_id: Delivery tracking ID

        Returns:
            DeliveryResponse: Delivery details
        """
        try:
            delivery = await DeliveryService.get_delivery_by_tracking_id(tracking_id)

            if not delivery:
                cls.logger.warning(f"Delivery not found with tracking ID: {tracking_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Delivery not found"
                )

            # Get related data
            vendor = delivery.get("vendor", {})
            driver = delivery.get("driver", {})
            customer = delivery.get("customer", {})
            latest_location = None

            if "id" in delivery:
                latest_location = await DeliveryService.get_latest_location(delivery["id"])

            # Construct response
            response = DeliveryResponseSchema(
                **delivery,
                vendor=vendor,
                driver=driver,
                customer=customer,
                latest_location=latest_location
            )

            return response
        except HTTPException as e:
            raise e
        except Exception as e:
            cls.logger.error(f"Error getting delivery by tracking ID: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting delivery by tracking ID: {str(e)}"
            )

    @classmethod
    async def update_delivery_status(
            cls,
            tracking_id: str,
            status_update: DeliveryStatusUpdateSchema
    ):
        """
        Update delivery status.

        Args:
            tracking_id: Delivery tracking ID
            status_update: Status update data

        Returns:
            DeliveryResponse: Updated delivery
        """
        try:
            # Ensure tracking IDs match
            if tracking_id != status_update.tracking_id:
                cls.logger.warning(f"Tracking ID mismatch: path={tracking_id}, body={status_update.tracking_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tracking ID mismatch between path and body"
                )

            delivery = await DeliveryService.update_delivery_status(
                tracking_id, status_update.status
            )

            # Get related data
            vendor = delivery.get("vendor", {})
            driver = delivery.get("driver", {})
            customer = delivery.get("customer", {})
            latest_location = None

            if "id" in delivery:
                latest_location = await DeliveryService.get_latest_location(delivery["id"])

            # Construct response
            response = DeliveryResponseSchema(
                **delivery,
                vendor=vendor,
                driver=driver,
                customer=customer,
                latest_location=latest_location
            )

            return response
        except HTTPException as e:
            raise e
        except Exception as e:
            cls.logger.error(f"Error updating delivery status: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating delivery status: {str(e)}"
            )
