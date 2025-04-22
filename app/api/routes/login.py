# app/api/routes/auth.py
from typing import Any
from datetime import timedelta
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.utils.logging_util import setup_logger
from app.api.models.user_model import UserModel
from app.services.otp_service import OTPService
from app.schemas.user_schema import PhoneNumber, UserCreate
from app.utils.security_util import SecurityUtil
from app.api.routes.base_router import RouterManager
from app.utils.database_operator_util import database_operator_util


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


class LoginRouter:

    def __init__(self):

        self.router_manager = RouterManager()
        self.logger = setup_logger(__name__)
        self.otp_service = OTPService()
        self.security_util = SecurityUtil()

        self.router_manager.add_route(
            "/login/request-otp",
            handler_method=self.request_login_otp,
            methods=["POST"],
            tags=["login"],
            status_code=status.HTTP_201_CREATED
        )

        self.router_manager.add_route(
            "/login/verify-otp",
            handler_method=self.verify_login_otp,
            methods=["POST"],
            tags=["login"],
            status_code=status.HTTP_201_CREATED
        )

    async def request_login_otp(self, phone: PhoneNumber) -> Any:
        """
        Request OTP for login.
        """
        # Check if user exists
        user_result = await database_operator_util.find_one(
            UserModel,
            UserModel.phone_number == phone.phone_number
        )

        if not user_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Generate and store OTP
        otp = await self.otp_service.store_otp(phone.phone_number, "login")

        # In a real application, send the OTP via SMS
        return {"message": "OTP sent successfully", "debug_otp": otp}

    async def verify_login_otp(
            self,
            user_in: UserCreate,
    ) -> Any:
        """
        Verify OTP and log user in.
        """

        self.logger.info(f"Verifying OTP for user {user_in.phone_number}")

        # Verify OTP
        is_valid = await self.otp_service.verify_otp(user_in.phone_number, user_in.otp, "login")
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP",
            )

        # Get user
        user_result = await database_operator_util.find_one(
            UserModel,
            UserModel.phone_number == user_in.phone_number
        )

        if not user_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = await self.security_util.create_access_token(
            subject=user_result["id"], expires_delta=access_token_expires
        )

        self.logger.info(f"User {user_result['id']} logged in successfully")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user_result["id"],
        }
