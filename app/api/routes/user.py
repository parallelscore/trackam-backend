# app/api/routes/user_router.py
from fastapi import Depends, HTTPException, status

from app.api.models.user_model import UserModel
from app.utils.logging_util import setup_logger
from app.utils.security_util import SecurityUtil
from app.api.routes.base_router import RouterManager
from app.utils.database_operator_util import database_operator_util

security_util = SecurityUtil()
get_current_user = security_util.get_current_user

class UserRouter:
    """
    Router for user-related endpoints.
    """

    def __init__(self):
        self.router_manager = RouterManager()
        self.logger = setup_logger(__name__)

        self.router_manager.add_route(
            path="/users/me",
            handler_method=self.get_current_user_profile,
            methods=["GET"],
            tags=["users"],
            status_code=status.HTTP_200_OK
        )

    async def get_current_user_profile(self, current_user: dict = Depends(get_current_user)):
        """
        Get current authenticated user's profile
        """
        try:
            user_id = current_user.get("id")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            # Fetch user details from database
            user_data = await database_operator_util.find_one(
                UserModel,
                UserModel.id == user_id
            )

            if not user_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )

            return user_data

        except Exception as e:
            self.logger.error(f"Error fetching current user profile: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve user profile"
            )
