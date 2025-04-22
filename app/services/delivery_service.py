# app/services/delivery_service.py
import uuid
from sqlalchemy import and_
from fastapi import HTTPException, status
from typing import Optional, List, Tuple, Dict
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.utils.logging_util import setup_logger
from app.services.auth_service import AuthService
from app.services.whatsapp_service import WhatsAppService
from app.api.models.user_model import UserRoleModel, UserModel
from app.schemas.create_delivery_schema import CreateDeliverySchema
from app.utils.database_operator_util import database_operator_util
from app.api.models.location_update_model import LocationUpdateModel
from app.api.models.delivery_model import DeliveryModel, DeliveryStatusModel
from app.schemas.create_location_update_schema import CreateLocationUpdateSchema


class DeliveryService:
    """Service for managing deliveries."""

    @classmethod
    def __init__(cls):
        cls.logger = setup_logger(__name__)
        cls.whats_app_service = WhatsAppService()

    @classmethod
    async def create_delivery(
            cls,
            delivery_data: CreateDeliverySchema,
            current_user_id: Optional[int] = None
    ) -> DeliveryModel:
        """
        Create a new delivery with tracking information.

        Args:
            delivery_data: Delivery creation data
            current_user_id: Optional ID of the current user (vendor)

        Returns:
            Dict: Created delivery instance
        """
        # Use current user as vendor if not specified
        vendor_id = delivery_data.vendor_id or current_user_id
        if not vendor_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vendor ID is required"
            )

        # Validate that users exist and have correct roles
        vendor = await database_operator_util.find_one(
            UserModel,
            and_(UserModel.id == vendor_id, UserModel.role == UserRoleModel.VENDOR)
        )

        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found or does not have vendor role"
            )

        driver = await database_operator_util.find_one(
            UserModel,
            and_(UserModel.id == delivery_data.driver_id, UserModel.role == UserRoleModel.DRIVER)
        )

        if not driver:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Driver not found or does not have driver role"
            )

        customer = await database_operator_util.find_one(
            UserModel,
            and_(UserModel.id == delivery_data.customer_id, UserModel.role == UserRoleModel.CUSTOMER)
        )

        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found or does not have customer role"
            )

        # Generate tracking ID if not provided
        tracking_id = delivery_data.tracking_id or f"TRK-{uuid.uuid4().hex[:8].upper()}"

        # Generate OTP for driver authentication
        otp_code = AuthService.generate_otp()
        otp_expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.OTP_EXPIRY_SECONDS)

        # Store OTP in Redis
        success, error = AuthService.store_otp(otp_code, tracking_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to store OTP: {error}"
            )

        # Generate tracking links
        driver_link, customer_link = AuthService.generate_tracking_links(tracking_id)

        # Create delivery data dictionary
        delivery_dict = {
            "tracking_id": tracking_id,
            "vendor_id": vendor_id,
            "driver_id": delivery_data.driver_id,
            "customer_id": delivery_data.customer_id,
            "package_info": delivery_data.package_info,
            "delivery_address": delivery_data.delivery_address,
            "delivery_latitude": delivery_data.delivery_latitude,
            "delivery_longitude": delivery_data.delivery_longitude,
            "pickup_address": delivery_data.pickup_address,
            "pickup_latitude": delivery_data.pickup_latitude,
            "pickup_longitude": delivery_data.pickup_longitude,
            "notes": delivery_data.notes,
            "metadata": delivery_data.metadata,
            "status": DeliveryStatusModel.CREATED.value,
            "otp_code": otp_code,
            "otp_expires_at": otp_expires_at,
            "driver_tracking_link": driver_link,
            "customer_tracking_link": customer_link,
        }

        # Save to database
        await database_operator_util.save_to_database(
            DeliveryModel,
            delivery_dict,
            filter_by={"tracking_id": tracking_id}
        )

        # Get the saved delivery
        delivery = await database_operator_util.find_one(
            DeliveryModel,
            DeliveryModel.tracking_id == tracking_id
        )

        # Send WhatsApp messages to driver and customer
        try:
            # Send OTP and tracking link to driver
            await cls.whats_app_service.send_driver_assignment(
                driver["phone"],
                delivery["tracking_id"],
                delivery["driver_tracking_link"],
                otp_code,
                vendor["name"],
                customer["name"],
                delivery["delivery_address"]
            )

            # Send tracking link to customer
            await cls.whats_app_service.send_customer_notification(
                customer["phone"],
                delivery["tracking_id"],
                delivery["customer_tracking_link"],
                driver["name"],
                delivery["package_info"]
            )
        except Exception as e:
            # Log the error but don't fail the delivery creation
            cls.logger.error(f"WhatsApp notification error: {str(e)}")

        return delivery

    @staticmethod
    async def get_delivery_by_tracking_id(tracking_id: str) -> Optional[Dict]:
        """Get a delivery by its tracking ID."""
        return await database_operator_util.find_one(
            DeliveryModel,
            DeliveryModel.tracking_id == tracking_id
        )

    @staticmethod
    async def get_delivery_by_id(delivery_id: int) -> Optional[Dict]:
        """Get a delivery by its database ID."""
        return await database_operator_util.find_one(
            DeliveryModel,
            DeliveryModel.id == delivery_id
        )

    @staticmethod
    async def get_deliveries(
            skip: int = 0,
            limit: int = 100,
            status: Optional[DeliveryStatusModel] = None,
            vendor_id: Optional[int] = None,
            driver_id: Optional[int] = None,
            customer_id: Optional[int] = None
    ) -> Tuple[List[Dict], int]:
        """
        Get deliveries with optional filtering.

        Returns:
            Tuple[List[Dict], int]: (deliveries, total_count)
        """
        # Build filter expression
        filters = []
        if status:
            filters.append(DeliveryModel.status == status)
        if vendor_id:
            filters.append(DeliveryModel.vendor_id == vendor_id)
        if driver_id:
            filters.append(DeliveryModel.driver_id == driver_id)
        if customer_id:
            filters.append(DeliveryModel.customer_id == customer_id)

        # Combine filters with AND
        filter_expr = and_(*filters) if filters else None

        # Get deliveries
        if filter_expr:
            deliveries = await database_operator_util.find_all(DeliveryModel, filter_expr)
        else:
            deliveries = await database_operator_util.find_all(DeliveryModel, True)

        # Since we need to apply pagination manually without SQLAlchemy query
        total = len(deliveries)
        paginated_deliveries = deliveries[skip:skip+limit]

        return paginated_deliveries, total

    @classmethod
    async def update_delivery_status(
            cls,
            tracking_id: str,
            delivery_status: DeliveryStatusModel,
            user_id: Optional[int] = None,
            user_role: Optional[UserRoleModel] = None
    ) -> Dict:
        """
        Update a delivery's status and relevant timestamp.

        Args:
            tracking_id: Delivery tracking ID
            delivery_status: New status
            user_id: ID of the user making the update (for permission checking)
            user_role: Role of the user making the update

        Returns:
            Dict: Updated delivery instance
        """
        delivery = await DeliveryService.get_delivery_by_tracking_id(tracking_id)
        if not delivery:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Delivery not found"
            )

        # Check permissions based on user role and status change
        if user_id and user_role:
            if user_role == UserRoleModel.DRIVER and user_id != delivery["driver_id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to update this delivery"
                )
            if user_role == UserRoleModel.CUSTOMER and user_id != delivery["customer_id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to update this delivery"
                )

        # Check valid status transitions
        valid_transitions = {
            DeliveryStatusModel.CREATED: [DeliveryStatusModel.ASSIGNED, DeliveryStatusModel.CANCELLED],
            DeliveryStatusModel.ASSIGNED: [DeliveryStatusModel.ACCEPTED, DeliveryStatusModel.CANCELLED],
            DeliveryStatusModel.ACCEPTED: [DeliveryStatusModel.IN_TRANSIT, DeliveryStatusModel.CANCELLED],
            DeliveryStatusModel.IN_TRANSIT: [DeliveryStatusModel.DELIVERED, DeliveryStatusModel.CANCELLED],
            DeliveryStatusModel.DELIVERED: [],  # Terminal state
            DeliveryStatusModel.CANCELLED: [],  # Terminal state
        }

        current_status = DeliveryStatusModel(delivery["status"])
        if status not in valid_transitions.get(current_status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from {current_status} to {status}"
            )

        # Update status and timestamp
        update_data = {"status": status.value}

        # Update the corresponding timestamp based on the new status
        now = datetime.now(timezone.utc)
        if delivery_status == DeliveryStatusModel.ASSIGNED:
            update_data["assigned_at"] = now
        elif delivery_status == DeliveryStatusModel.ACCEPTED:
            update_data["accepted_at"] = now
        elif delivery_status == DeliveryStatusModel.IN_TRANSIT:
            update_data["in_transit_at"] = now
        elif delivery_status == DeliveryStatusModel.DELIVERED:
            update_data["delivered_at"] = now
        elif delivery_status == DeliveryStatusModel.CANCELLED:
            update_data["cancelled_at"] = now

        # Update the delivery
        await database_operator_util.update_database(
            DeliveryModel,
            DeliveryModel.tracking_id == tracking_id,
            update_data
        )

        # Get updated delivery
        updated_delivery = await database_operator_util.find_one(
            DeliveryModel,
            DeliveryModel.tracking_id == tracking_id
        )

        # Send notifications based on status change
        try:
            if delivery_status == DeliveryStatusModel.ACCEPTED:
                # Notify customer that driver has accepted the delivery
                customer = await database_operator_util.find_one(UserModel, UserModel.id == delivery["customer_id"])
                driver = await database_operator_util.find_one(UserModel, UserModel.id == delivery["driver_id"])
                if customer and driver:
                    await cls.whats_app_service.send_delivery_accepted(
                        customer["phone"],
                        delivery["tracking_id"],
                        driver["name"],
                        delivery["package_info"]
                    )

            elif delivery_status == DeliveryStatusModel.IN_TRANSIT:
                # Notify customer that delivery is on the way
                customer = await database_operator_util.find_one(UserModel, UserModel.id == delivery["customer_id"])
                if customer:
                    await cls.whats_app_service.send_delivery_in_transit(
                        customer["phone"],
                        delivery["tracking_id"],
                        delivery["customer_tracking_link"]
                    )

            elif delivery_status == DeliveryStatusModel.DELIVERED:
                # Notify vendor that delivery is complete
                vendor = await database_operator_util.find_one(UserModel, UserModel.id == delivery["vendor_id"])
                customer = await database_operator_util.find_one(UserModel, UserModel.id == delivery["customer_id"])
                if vendor and customer:
                    await cls.whats_app_service.send_delivery_completed(
                        vendor["phone"],
                        delivery["tracking_id"],
                        customer["name"]
                    )
        except Exception as e:
            # Log the error but don't fail the status update
            cls.logger.error(f"WhatsApp notification error: {str(e)}")

        return updated_delivery

    @staticmethod
    async def verify_driver_otp(
            tracking_id: str,
            otp_code: str
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Verify OTP for driver authentication.

        Returns:
            Tuple[bool, Optional[Dict]]: (is_valid, delivery_if_valid)
        """
        delivery = await DeliveryService.get_delivery_by_tracking_id(tracking_id)
        if not delivery:
            return False, None

        # Verify OTP against Redis
        is_valid, error = AuthService.verify_otp(otp_code, tracking_id)
        if not is_valid:
            return False, None

        # If valid, update delivery status to ACCEPTED if currently ASSIGNED or CREATED
        current_status = DeliveryStatusModel(delivery["status"])
        if current_status in [DeliveryStatusModel.CREATED, DeliveryStatusModel.ASSIGNED]:
            delivery = await DeliveryService.update_delivery_status(
                tracking_id, DeliveryStatusModel.ACCEPTED
            )

        return True, delivery

    @staticmethod
    async def add_location_update(
            tracking_id: str,
            location_data: CreateLocationUpdateSchema
    ) -> Dict:
        """
        Add a new location update for a delivery.

        Args:
            tracking_id: Delivery tracking ID
            location_data: Location update data

        Returns:
            Dict: Created location update instance
        """
        delivery = await DeliveryService.get_delivery_by_tracking_id(tracking_id)
        if not delivery:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Delivery not found"
            )

        # Create location update data
        location_dict = {
            "delivery_id": delivery["id"],
            "latitude": location_data.latitude,
            "longitude": location_data.longitude,
            "accuracy": location_data.accuracy,
            "speed": location_data.speed,
            "heading": location_data.heading,
            "altitude": location_data.altitude,
            "battery_level": location_data.battery_level,
            "is_moving": location_data.is_moving,
            "metadata": location_data.metadata,
        }

        # Save to database
        await database_operator_util.save_to_database(
            LocationUpdateModel,
            location_dict,
            filter_by={}  # Always create new location updates
        )

        # Get the newest location for this delivery
        location = await DeliveryService.get_latest_location(delivery["id"])

        return location

    @staticmethod
    async def get_latest_location(delivery_id: int) -> Optional[Dict]:
        """Get the latest location update for a delivery."""
        locations = await database_operator_util.find_all(
            LocationUpdateModel,
            LocationUpdateModel.delivery_id == delivery_id
        )

        # Sort by created_at descending and take the first
        if locations:
            return sorted(locations, key=lambda x: x["created_at"], reverse=True)[0]
        return None

    @staticmethod
    async def get_location_history(
            delivery_id: int,
            limit: int = 100
    ) -> List[Dict]:
        """Get the location history for a delivery."""
        locations = await database_operator_util.find_all(
            LocationUpdateModel,
            LocationUpdateModel.delivery_id == delivery_id
        )

        # Sort by created_at descending and limit
        sorted_locations = sorted(locations, key=lambda x: x["created_at"], reverse=True)
        return sorted_locations[:limit]