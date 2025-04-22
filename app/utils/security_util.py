# app/utils/security_util.py
from typing import Optional
from jose import jwt, JWTError
from pydantic import ValidationError
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.api.models.user_model import UserModel
from app.utils.database_operator_util import database_operator_util

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

class SecurityUtil:

    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


    async def create_access_token(self, subject: str, expires_delta: Optional[timedelta] = None) -> str:
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode = {"exp": expire, "sub": str(subject)}
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    async def get_current_user(self, token: str = Depends(oauth2_scheme)) -> dict:
        """
        Validate access token and return user
        """
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            user_id: str = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except (JWTError, ValidationError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = await database_operator_util.find_one(UserModel, UserModel.id == user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user

    async def get_current_active_user(self, current_user: dict = Depends(get_current_user)) -> dict:
        """
        Get current active user
        """
        if not current_user.get("is_active"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
            )
        return current_user