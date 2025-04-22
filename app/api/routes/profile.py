from typing import Any
from sqlalchemy import and_
from fastapi import Depends, HTTPException, status

from app.utils.logging_util import setup_logger
from app.api.models.user_model import UserModel
from app.services.otp_service import OTPService
from app.utils.security_util import SecurityUtil
from app.api.routes.base_router import RouterManager
from app.schemas.user_schema import UserCompleteProfile
from app.utils.database_operator_util import database_operator_util

security_util = SecurityUtil()
get_current_user = security_util.get_current_user


class ProfileRouter:
    """
    Router for authentication-related endpoints.
    """

    def __init__(self):

        self.router_manager = RouterManager()
        self.logger = setup_logger(__name__)
        self.otp_service = OTPService()

        self.router_manager.add_route(
            "/complete-profile",
            handler_method=self.complete_profile,
            methods=["POST"],
            tags=["profile"],
            status_code=status.HTTP_201_CREATED
        )


    async def complete_profile(
            self,
            profile_data: UserCompleteProfile,
            current_user: dict = Depends(get_current_user)
    ) -> Any:
        """
        Complete user profile after registration.
        """
        # Get user
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        # Check if email already exists
        if profile_data.email:
            existing_email = await database_operator_util.find_one(
                UserModel,
                and_(
                    UserModel.email == profile_data.email,
                    UserModel.id != user_id
                )
            )

            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )

        # Update user profile
        update_data = {}

        # Add fields only if they are provided (not None)
        if profile_data.first_name is not None:
            update_data["first_name"] = profile_data.first_name

        if profile_data.last_name is not None:
            update_data["last_name"] = profile_data.last_name

        if profile_data.business_name is not None:
            update_data["business_name"] = profile_data.business_name

        if profile_data.email is not None:
            update_data["email"] = profile_data.email

        if profile_data.profile_image_url:
            update_data["profile_image_url"] = profile_data.profile_image_url

        # Only update if there are fields to update
        if update_data:
            await database_operator_util.update_database(
                model=UserModel,
                filter_expr=UserModel.id == user_id,
                update_data=update_data
            )

        # Get updated user
        updated_user = await database_operator_util.find_one(
            UserModel,
            UserModel.id == user_id
        )

        return updated_user