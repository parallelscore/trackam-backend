# app/api/routes/auth.py
import uuid
from typing import Any
from datetime import timedelta
from fastapi import HTTPException, status

from app.core.config import settings
from app.utils.logging_util import setup_logger
from app.api.models.user_model import UserModel
from app.services.otp_service import OTPService
from app.utils.security_util import SecurityUtil
from app.api.routes.base_router import RouterManager
from app.schemas.user_schema import PhoneNumber, UserCreate
from app.utils.database_operator_util import database_operator_util


class RegisterRouter:
    """
    Router for authentication-related endpoints.
    """

    def __init__(self):

        self.router_manager = RouterManager()
        self.logger = setup_logger(__name__)
        self.otp_service = OTPService()
        self.security_util = SecurityUtil()

        self.router_manager.add_route(
            path="/register/request-otp",
            handler_method=self.request_registration_otp,
            methods=["POST"],
            tags=["register"],
            status_code=status.HTTP_202_ACCEPTED
        )

        self.router_manager.add_route(
            "/register/verify-otp",
            handler_method=self.verify_registration_otp,
            methods=["POST"],
            tags=["register"],
            status_code=status.HTTP_201_CREATED
        )

    async def request_registration_otp(self, user_in: PhoneNumber) -> Any:
        """
        Request OTP for vendor registration.
        """
        # Check if user already exists
        user_result = await database_operator_util.find_one(
            UserModel,
            UserModel.phone_number == user_in.phone_number
        )

        if user_result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this phone number already exists",
            )

        # Generate and store OTP
        otp = await self.otp_service.store_otp(user_in.phone_number, "registration")

        # In development mode, include the OTP in the response
        response = {"message": "OTP sent successfully to your phone number"}

        if not settings.SMS_SERVICE_ENABLED:
            response["debug_otp"] = otp

        return response

    async def verify_registration_otp(self,
                                      user_in: UserCreate,
                                      ) -> Any:
        """
        Verify OTP and create user account.
        """
        # Verify OTP
        is_valid = await self.otp_service.verify_otp(user_in.phone_number, user_in.otp, "registration")
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP",
            )

        # Check if user already exists
        user_result = await database_operator_util.find_one(
            UserModel,
            UserModel.phone_number == user_in.phone_number
        )

        if user_result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this phone number already exists",
            )

        # Create user
        user_data = {
            "id": str(uuid.uuid4()),
            "phone_number": user_in.phone_number,
            "is_phone_verified": True,
            "is_active": True
        }

        await database_operator_util.save_to_database(
            model=UserModel,
            data=user_data,
            filter_by={"phone_number": user_in.phone_number}
        )

        # Get the newly created user
        new_user = await database_operator_util.find_one(
            UserModel,
            UserModel.phone_number == user_in.phone_number
        )

        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = await self.security_util.create_access_token(
            subject=new_user["id"], expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": new_user["id"],
        }
