from fastapi import status, HTTPException
from fastapi.responses import JSONResponse

from app.utils.logging_util import setup_logger
from app.services.auth_service import AuthService
from app.api.routes.base_router import RouterManager
from app.schemas.otp_verify_schema import OTPVerifySchema
from app.services.delivery_service import DeliveryService


class AuthRouter:

    @classmethod
    def __init__(cls):

        cls.router_manager = RouterManager()
        cls.logger = setup_logger(__name__)
        cls.delivery_service = DeliveryService()
        cls.auth_service = AuthService()

        cls.router_manager.add_route(
            path='/verify-otp',
            handler_method=cls.verify_otp,
            methods=['POST'],
            tags=['auth'],
            status_code=status.HTTP_200_OK
        )

        cls.router_manager.add_route(
            path='/validate-tracking-token',
            handler_method=cls.validate_tracking_token,
            methods=['GET'],
            tags=['auth'],
            status_code=status.HTTP_200_OK
        )

    @classmethod
    async def verify_otp(
            cls,
            otp_data: OTPVerifySchema
    ):
        """
        Verify OTP for driver authentication.

        Args:
            otp_data: OTP verification data

        Returns:
            Dict: Verification result and tracking info
        """
        try:
            is_valid, delivery = await cls.delivery_service.verify_driver_otp(
                otp_data.tracking_id, otp_data.otp_code
            )

            if not is_valid or not delivery:
                cls.logger.warning(f"Invalid OTP attempt for tracking ID: {otp_data.tracking_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid OTP code or tracking ID"
                )

            cls.logger.info(f"OTP verified successfully for tracking ID: {otp_data.tracking_id}")

            # Return successful validation response
            return {
                "verified": True,
                "tracking_id": delivery["tracking_id"],
                "status": delivery["status"],
                "message": "OTP verification successful. You can now start tracking."
            }
        except HTTPException as e:
            raise e
        except Exception as e:
            cls.logger.error(f"Error verifying OTP: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error verifying OTP: {str(e)}"
            )

    @classmethod
    async def validate_tracking_token(
            cls,
            tracking_id: str,
            token: str,
            token_type: str
    ):
        """
        Validate tracking token for customer or driver.

        Args:
            tracking_id: Delivery tracking ID
            token: Token to validate
            token_type: Either 'customer' or 'driver'

        Returns:
            Dict: Validation result
        """
        try:
            if token_type not in ["customer", "driver"]:
                cls.logger.warning(f"Invalid token type requested: {token_type}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token type. Must be 'customer' or 'driver'"
                )

            # Check if delivery exists
            delivery = await DeliveryService.get_delivery_by_tracking_id(tracking_id)
            if not delivery:
                cls.logger.warning(f"Attempted to validate token for non-existent delivery: {tracking_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Delivery not found"
                )

            is_valid = cls.auth_service.validate_tracking_token(tracking_id, token, token_type)

            if not is_valid:
                cls.logger.warning(f"Invalid token validation attempt for tracking ID: {tracking_id}, token type: {token_type}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid tracking token"
                )

            cls.logger.info(f"Token validated successfully for tracking ID: {tracking_id}, token type: {token_type}")

            return {
                "valid": True,
                "tracking_id": tracking_id,
                "token_type": token_type
            }
        except HTTPException as e:
            raise e
        except Exception as e:
            cls.logger.error(f"Error validating token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error validating token: {str(e)}"
            )