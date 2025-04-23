# app/api/routes/delivery.py
import uuid
import string
import random
from typing import Optional
from datetime import timezone
from sqlalchemy import or_, and_
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, Query

from app.core.config import settings
from app.utils.logging_util import setup_logger
from app.utils.security_util import SecurityUtil
from app.api.routes.base_router import RouterManager
from app.schemas.delivery_schema import CreateDelivery
from app.api.models.delivery_model import DeliveryModel
from app.utils.database_operator_util import database_operator_util

security_util = SecurityUtil()
get_current_user = security_util.get_current_user


class DeliveryRouter:
    """
    Router for delivery-related endpoints.
    """

    def __init__(self):
        self.router_manager = RouterManager()
        self.logger = setup_logger(__name__)

        # Get all deliveries with filtering and pagination
        self.router_manager.add_route(
            path="/deliveries",
            handler_method=self.get_deliveries,
            methods=["GET"],
            tags=["delivery"],
            status_code=status.HTTP_200_OK
        )

        # Create new delivery
        self.router_manager.add_route(
            path="/deliveries",
            handler_method=self.create_delivery,
            methods=["POST"],
            tags=["delivery"],
            status_code=status.HTTP_201_CREATED
        )

        # Get delivery by ID
        self.router_manager.add_route(
            path="/deliveries/{delivery_id}",
            handler_method=self.get_delivery,
            methods=["GET"],
            tags=["delivery"],
            status_code=status.HTTP_200_OK
        )

        # Get delivery by tracking ID
        self.router_manager.add_route(
            path="/deliveries/tracking/{tracking_id}",
            handler_method=self.get_delivery_by_tracking,
            methods=["GET"],
            tags=["delivery"],
            status_code=status.HTTP_200_OK
        )

        self.router_manager.add_route(
            path="/deliveries/{tracking_id}/cancel",
            handler_method=self.cancel_delivery,
            methods=["POST"],
            tags=["delivery"],
            status_code=status.HTTP_200_OK
        )

    async def get_deliveries(
            self,
            delivery_status: Optional[str] = Query(None, description="Filter by delivery status"),
            search: Optional[str] = Query(None, description="Search by tracking ID, customer name, or rider name"),
            page: int = Query(1, ge=1, description="Page number"),
            limit: int = Query(10, ge=1, le=100, description="Items per page"),
            current_user: dict = Depends(get_current_user)
    ):
        """
        Get all deliveries with optional filtering and pagination.
        """
        try:
            # Build filter expression
            filter_conditions = []

            # Only show deliveries for the current vendor
            filter_conditions.append(DeliveryModel.vendor_id == current_user["id"])

            # Apply status filter if provided
            if status:
                filter_conditions.append(DeliveryModel.status == delivery_status)

            # Apply search filter if provided
            if search:
                search_term = f"%{search}%"
                search_condition = or_(
                    DeliveryModel.tracking_id.ilike(search_term),
                    DeliveryModel.customer_name.ilike(search_term),
                    DeliveryModel.rider_name.ilike(search_term)
                )
                filter_conditions.append(search_condition)

            # Combine all conditions
            filter_expr = and_(*filter_conditions)

            # Calculate pagination
            offset = (page - 1) * limit

            # Get total count for pagination
            count_query = f"SELECT COUNT(*) FROM deliveries WHERE vendor_id = '{current_user['id']}'"
            if status:
                count_query += f" AND status = '{status}'"
            if search:
                count_query += f" AND (tracking_id ILIKE '%{search}%' OR customer_name ILIKE '%{search}%' OR rider_name ILIKE '%{search}%')"

            # Get deliveries
            deliveries = await database_operator_util.find_all(
                DeliveryModel,
                filter_expr,
                limit=limit,
                offset=offset,
                order_by=DeliveryModel.created_at.desc()
            )

            # Get total count
            total_count = await database_operator_util.execute_raw_query(count_query)
            total_count = total_count[0]['count'] if total_count else 0

            return {
                "items": deliveries,
                "total": total_count,
                "page": page,
                "limit": limit,
                "pages": (total_count + limit - 1) // limit  # Ceiling division
            }
        except Exception as e:
            self.logger.error(f"Error getting deliveries: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve deliveries"
            )

    async def create_delivery(self, delivery_data: CreateDelivery, current_user: dict = Depends(get_current_user)):
        """
        Create a new delivery.
        """
        try:
            # Generate a unique tracking ID
            tracking_id = self._generate_tracking_id()

            # Generate OTP for rider
            otp = ''.join(random.choices(string.digits, k=6))
            otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=60)  # OTP valid for 1 hour

            # Generate tracking links
            base_url = settings.FRONTEND_URL
            rider_link = f"{base_url}/rider/{tracking_id}"
            customer_link = f"{base_url}/track/{tracking_id}"

            # Create delivery object
            delivery = {
                "id": str(uuid.uuid4()),
                "tracking_id": tracking_id,
                "status": "created",

                "vendor_id": current_user["id"],

                "customer_name": delivery_data.customer.name,
                "customer_phone": delivery_data.customer.phone_number,
                "customer_address": delivery_data.customer.address,
                "customer_location": None,  # Will be set later

                "rider_name": delivery_data.rider.name,
                "rider_phone": delivery_data.rider.phone_number,
                "rider_id": None,  # Will be assigned when rider accepts
                "rider_current_location": None,  # Will be updated during tracking

                "package_description": delivery_data.package.description,
                "package_size": delivery_data.package.size,
                "package_special_instructions": delivery_data.package.special_instructions,

                "otp": otp,
                "otp_expiry": otp_expiry,
                "rider_link": rider_link,
                "customer_link": customer_link,
                "is_tracking_active": False,
                "location_history": [],

                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }

            # Save to database
            await database_operator_util.save_to_database(
                model=DeliveryModel,
                data=delivery,
                filter_by={"tracking_id": tracking_id}
            )

            # Get the created delivery
            created_delivery = await database_operator_util.find_one(
                DeliveryModel,
                DeliveryModel.tracking_id == tracking_id
            )

            if not created_delivery:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create delivery"
                )

            return created_delivery

        except Exception as e:
            self.logger.error(f"Error creating delivery: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create delivery: {str(e)}"
            )

    async def get_delivery(self, delivery_id: str, current_user: dict = Depends(get_current_user)):
        """
        Get delivery by ID.
        """
        try:
            delivery = await database_operator_util.find_one(
                DeliveryModel,
                and_(
                    DeliveryModel.id == delivery_id,
                    DeliveryModel.vendor_id == current_user["id"]
                )
            )

            if not delivery:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Delivery not found"
                )

            return delivery

        except Exception as e:
            self.logger.error(f"Error getting delivery: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve delivery"
            )

    async def get_delivery_by_tracking(self, tracking_id: str, current_user: dict = Depends(get_current_user)):
        """
        Get delivery by tracking ID.
        """
        try:
            delivery = await database_operator_util.find_one(
                DeliveryModel,
                and_(
                    DeliveryModel.tracking_id == tracking_id,
                    DeliveryModel.vendor_id == current_user["id"]
                )
            )

            if not delivery:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Delivery not found"
                )

            return delivery

        except Exception as e:
            self.logger.error(f"Error getting delivery by tracking ID: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve delivery"
            )

    def _generate_tracking_id(self, length=6):
        """
        Generate a unique tracking ID.
        """
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choices(chars, k=length))

    async def cancel_delivery(self, tracking_id: str, current_user: dict = Depends(get_current_user)):
        """
        Cancel a delivery by its tracking ID.
        """
        try:
            # Check if delivery exists and belongs to this vendor
            delivery = await database_operator_util.find_one(
                DeliveryModel,
                and_(
                    DeliveryModel.tracking_id == tracking_id,
                    DeliveryModel.vendor_id == current_user["id"]
                )
            )

            if not delivery:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Delivery not found"
                )

            # Check if delivery is already completed or cancelled
            if delivery.status in ['completed', 'cancelled']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot cancel a delivery with status '{delivery.status}'"
                )

            # Update delivery status to cancelled
            update_data = {
                "status": "cancelled",
                "updated_at": datetime.now(timezone.utc),
                "is_tracking_active": False
            }

            await database_operator_util.update(
                model=DeliveryModel,
                filter_by={"tracking_id": tracking_id},
                data=update_data
            )

            # Get the updated delivery
            updated_delivery = await database_operator_util.find_one(
                DeliveryModel,
                DeliveryModel.tracking_id == tracking_id
            )

            return updated_delivery

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error cancelling delivery: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel delivery"
            )

