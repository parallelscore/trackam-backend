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
from app.services.sms_service import sms_service
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
        self.base_url = settings.FRONTEND_URL

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

        self.router_manager.add_route(
            path="/deliveries/{tracking_id}/resend-notifications",
            handler_method=self.resend_notifications,
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
            if delivery_status:
                filter_conditions.append(DeliveryModel.status == delivery_status)

                self.logger.info(f"Filtering deliveries by status: {delivery_status}")

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

            # Get deliveries with pagination
            deliveries = await database_operator_util.find_all(
                DeliveryModel,
                filter_expr,
                limit=limit,
                offset=offset,
                order_by=DeliveryModel.created_at.desc()
            )

            # Get total count using ORM count method instead of raw SQL
            total_count = await database_operator_util.count_entries(
                DeliveryModel,
                filter_expr
            )

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
            rider_link = f"{self.base_url}/rider/{tracking_id}"
            customer_link = f"{self.base_url}/track/{tracking_id}"

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

            self.logger.info(f"Delivery created successfully with tracking ID: {tracking_id}")
            self.logger.info(f"Delivery details: {created_delivery}")

            if not created_delivery:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create delivery"
                )

            # Send WhatsApp messages to rider and customer
            await self._send_delivery_notifications(created_delivery)

            return created_delivery

        except Exception as e:
            self.logger.error(f"Error creating delivery: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create delivery: {str(e)}"
            )

    async def _send_delivery_notifications(self, delivery):
        """
        Send WhatsApp notifications to rider and customer.

        Args:
            delivery: The delivery object
        """
        try:
            # Extract necessary information
            tracking_id = delivery.get("tracking_id")

            # Extract from nested structures
            customer = delivery.get("customer", {})
            rider = delivery.get("rider", {})
            package = delivery.get("package", {})
            tracking = delivery.get("tracking", {})

            otp = tracking.get("otp")
            rider_phone = rider.get("phone_number")
            customer_phone = customer.get("phone_number")
            rider_accept_link = f"{self.base_url}/rider/accept/{tracking_id}"
            customer_link = tracking.get("customer_link")
            customer_name = customer.get("name")
            customer_address = customer.get("address")
            package_description = package.get("description")
            special_instructions = package.get("special_instructions", "")

            # Create rider message
            rider_message = (
                f"*New Delivery Request* 🚚\n\n"
                f"*Tracking ID:* {tracking_id}\n"
                f"*Customer:* {customer_name}\n"
                f"*Address:* {customer_address}\n"
                f"*Package:* {package_description}\n"
            )

            # Add special instructions if any
            if special_instructions:
                rider_message += f"Special Instructions: {special_instructions}\n\n"
            else:
                rider_message += "\n"

            rider_message += (
                f"*Your OTP:* {otp}\n\n"
                f"Click the link below to accept the delivery:\n"
                f"{rider_accept_link}"
            )

            self.logger.info(f"rider_message: {rider_message}")

            # Create customer message
            customer_message = (
                f"*TrackAm Delivery Confirmation* ✅\n\n"
                f"Your delivery has been created and a rider will be assigned soon.\n\n"
                f"*Tracking ID:* {tracking_id}\n"
                f"*Package:* {package_description}\n\n"
                f"Use this link to track your delivery in real-time:\n"
                f"{customer_link}\n\n"
                f"Thank you for using TrackAm! 🙏"
            )

            self.logger.info(f"customer_message: {customer_message}")

            self.logger.info(f"Sending WhatsApp messages to rider: {rider_phone} and customer: {customer_phone}")

            # Send WhatsApp messages
            rider_sent = await sms_service.send_whatsapp(rider_phone, rider_message)
            customer_sent = await sms_service.send_whatsapp(customer_phone, customer_message)

            self.logger.info(f"WhatsApp messages sent to rider: {rider_sent}, customer: {customer_sent}")

            if rider_sent and customer_sent:
                self.logger.info(f"WhatsApp notifications sent successfully for delivery {tracking_id}")
            else:
                self.logger.warning(f"Some WhatsApp notifications failed for delivery {tracking_id}")

            return rider_sent and customer_sent

        except Exception as e:
            self.logger.error(f"Error sending delivery notifications: {str(e)}")
            return False

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

    async def resend_notifications(self, tracking_id: str, current_user: dict = Depends(get_current_user)):
        """
        Resend WhatsApp notifications to rider and customer.
        If OTP has expired, generate a new one before sending.
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

            # Get the current time and OTP expiry time
            current_time = datetime.now(timezone.utc)
            otp_expiry_str = delivery.get("tracking", {}).get("otp_expiry")

            otp_expired = True
            if otp_expiry_str:
                try:
                    otp_expiry_datetime = datetime.fromisoformat(otp_expiry_str)
                    otp_expired = current_time > otp_expiry_datetime
                except (ValueError, TypeError):
                    self.logger.error(f"Invalid OTP expiry format for delivery {tracking_id}")
                    # Default to generating a new OTP if we can't parse the expiry
                    otp_expired = True

            # If OTP has expired, generate a new one
            if otp_expired:
                self.logger.info(f"OTP expired for delivery {tracking_id}, generating new OTP")

                # Generate new OTP
                new_otp = ''.join(random.choices(string.digits, k=6))
                new_otp_expiry = current_time + timedelta(minutes=60)  # OTP valid for 1 hour

                # Update delivery with new OTP (use the actual column names)
                update_data = {
                    "otp": new_otp,
                    "otp_expiry": new_otp_expiry,
                    "updated_at": current_time
                }

                await database_operator_util.update(
                    model=DeliveryModel,
                    filter_by={"tracking_id": tracking_id},
                    data=update_data
                )

                # Fetch updated delivery data
                delivery = await database_operator_util.find_one(
                    DeliveryModel,
                    DeliveryModel.tracking_id == tracking_id
                )

                self.logger.info(f"Generated new OTP {new_otp} for delivery {tracking_id}")
            else:
                self.logger.info(f"Using existing OTP for delivery {tracking_id}")

            # Send notifications with current (potentially new) OTP
            success = await self._send_delivery_notifications(delivery)

            if not success:
                return {
                    "success": False,
                    "message": "Failed to send some notifications. Please try again later."
                }

            return {
                "success": True,
                "message": "Notifications resent successfully" + (", with new OTP" if otp_expired else "")
            }

        except Exception as e:
            self.logger.error(f"Error resending notifications: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to resend notifications"
            )