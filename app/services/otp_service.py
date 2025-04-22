# app/services/otp_service.py
import random
import string
from sqlalchemy import and_
from datetime import datetime, timedelta, timezone

from app.api.models.otp_model import OTPModel
from app.utils.logging_util import setup_logger
from app.services.sms_service import sms_service
from app.utils.database_operator_util import database_operator_util

class OTPService:

    def __init__(self):
        self.logger = setup_logger(__name__)

    @staticmethod
    def _generate_otp(length=6):
        """Generate a numeric OTP of specified length"""
        return ''.join(random.choices(string.digits, k=length))

    async def store_otp(self, phone_number: str, purpose: str):
        """Create and store an OTP for a user"""
        # Generate a 6-digit OTP
        otp_code = self._generate_otp(6)

        self.logger.info(f"Generated OTP: {otp_code} for {phone_number} for purpose: {purpose}")

        # Prepare OTP data
        otp_data = {
            "phone_number": phone_number,
            "code": otp_code,
            "purpose": purpose,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
            "is_used": False
        }

        # Save to database using the utility
        filter_by = {"phone_number": phone_number, "purpose": purpose}
        await database_operator_util.save_to_database(
            model=OTPModel,
            data=otp_data,
            filter_by=filter_by,
            update_fields={"code": otp_code, "expires_at": otp_data["expires_at"], "is_used": False}
        )

        # Send OTP via SMS based on purpose
        if purpose == "registration":
            message = f"Your TrackAm registration code is: {otp_code}. It will expire in 10 minutes."
        elif purpose == "login":
            message = f"Your TrackAm login code is: {otp_code}. It will expire in 10 minutes."
        else:
            message = f"Your TrackAm verification code is: {otp_code}. It will expire in 10 minutes."

        # Send the SMS
        sms_sent = await sms_service.send_sms(phone_number, message)

        if not sms_sent:
            self.logger.warning(f"Failed to send OTP SMS to {phone_number} for {purpose}")

        return otp_code

    async def verify_otp(self, phone_number: str, otp_code: str, purpose: str):
        """Verify if an OTP is valid"""
        # Find the most recent unused OTP for this phone number and purpose
        filter_expr = and_(
            OTPModel.phone_number == phone_number,
            OTPModel.code == otp_code,
            OTPModel.purpose == purpose,
            OTPModel.is_used == False,
            OTPModel.expires_at > datetime.now(timezone.utc)
        )

        otp_result = await database_operator_util.find_one(OTPModel, filter_expr)

        if not otp_result:
            return False

        # Mark OTP as used
        await database_operator_util.update_database(
            model=OTPModel,
            filter_expr=OTPModel.id == otp_result["id"],
            update_data={"is_used": True}
        )

        return True
