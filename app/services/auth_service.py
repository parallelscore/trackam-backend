import random
import string
import secrets
import hashlib
from typing import Optional, Tuple

from app.core.config import settings
from app.utils.redis_util import redis_util
from app.utils.logging_util import setup_logger



class AuthService:
    """Service for OTP generation, verification, and authentication."""

    @classmethod
    def __init__(cls):
        cls.redis_conn = redis_util
        cls.logger = setup_logger(__name__)
        cls.OTP_EXPIRY_SECONDS = settings.OTP_EXPIRY_SECONDS

    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """Generate a numeric OTP of specified length."""
        return ''.join(random.choices(string.digits, k=length))

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate a random secure token."""
        return secrets.token_urlsafe(length)

    @staticmethod
    def hash_otp(otp: str, tracking_id: str) -> str:
        """Hash the OTP with the tracking ID for secure storage."""
        combined = f"{otp}:{tracking_id}"
        return hashlib.sha256(combined.encode()).hexdigest()

    @classmethod
    def store_otp(cls, otp: str, tracking_id: str) -> Tuple[bool, Optional[str]]:
        """
        Store OTP in Redis with expiration.

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            # Hash the OTP with tracking ID for secure storage
            hashed_otp = cls.hash_otp(otp, tracking_id)

            # Store in Redis with expiration
            key = f"otp:{tracking_id}"
            cls.redis_conn.set(key, hashed_otp)
            cls.redis_conn.expire(key, cls.OTP_EXPIRY_SECONDS)

            return True, None

        except Exception as e:
            return False, str(e)

    @classmethod
    def verify_otp(cls, otp: str, tracking_id: str) -> Tuple[bool, Optional[str]]:
        """
        Verify OTP against stored value in Redis.

        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            key = f"otp:{tracking_id}"

            # Get stored hashed OTP
            stored_hash = cls.redis_conn.get(key)
            if not stored_hash:
                return False, "OTP expired or not found"

            # Hash the provided OTP for comparison
            input_hash = cls.hash_otp(otp, tracking_id)

            # Compare hashes
            if input_hash == stored_hash.decode():
                # Delete the used OTP for security
                cls.redis_conn.delete(key)
                return True, None
            else:
                return False, "Invalid OTP"
        except Exception as e:
            return False, str(e)

    @classmethod
    def invalidate_otp(cls, tracking_id: str) -> bool:
        """Invalidate an OTP for a given tracking ID."""
        try:
            key = f"otp:{tracking_id}"
            return bool(cls.redis_conn.delete(key))
        except Exception:
            return False

    @classmethod
    def generate_tracking_links(cls, tracking_id: str) -> Tuple[str, str]:
        """
        Generate unique tracking links for driver and customer.

        Returns:
            Tuple[str, str]: (driver_link, customer_link)
        """
        # Generate unique tokens for security
        driver_token = cls.generate_token(16)
        customer_token = cls.generate_token(16)

        # Create the links
        driver_link = f"{settings.BASE_URL}/driver/{tracking_id}?token={driver_token}"
        customer_link = f"{settings.BASE_URL}/track/{tracking_id}?token={customer_token}"

        # Store tokens in Redis for validation
        cls.redis_conn.set(f"driver_token:{tracking_id}", driver_token)
        cls.redis_conn.set(f"customer_token:{tracking_id}", customer_token)

        # No expiration for these tokens as they should be valid until delivery is complete

        return driver_link, customer_link

    @classmethod
    def validate_tracking_token(cls, tracking_id: str, token: str, token_type: str) -> bool:
        """
        Validate a tracking token.

        Args:
            tracking_id: The tracking ID
            token: The token to validate
            token_type: Either 'driver' or 'customer'

        Returns:
            bool: True if token is valid
        """
        try:
            key = f"{token_type}_token:{tracking_id}"
            stored_token = cls.redis_conn.get(key)

            if not stored_token:
                return False

            return token == stored_token.decode()
        except Exception:
            return False