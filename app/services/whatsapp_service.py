# app/services/whatsapp_service.py
from twilio.rest import Client

from app.core.config import settings
from app.utils.logging_util import setup_logger

class WhatsAppService:
    """Service for sending WhatsApp messages through Twilio."""

    @classmethod
    def __int__(cls):
        cls.logger = setup_logger(__name__)
        cls.TWILIO_ACCOUNT_SID = settings.TWILIO_ACCOUNT_SID
        cls.TWILIO_AUTH_TOKEN = settings.TWILIO_AUTH_TOKEN

    @classmethod
    async def _get_client(cls) -> Client:
        """Get Twilio client with credentials from settings."""
        return Client(cls.TWILIO_ACCOUNT_SID, cls.TWILIO_AUTH_TOKEN)

    @classmethod
    async def _format_phone_for_whatsapp(cls, phone: str) -> str:
        """Format phone number for WhatsApp API."""
        # Remove any non-digit characters
        phone_digits = ''.join(filter(str.isdigit, phone))

        # Ensure number starts with country code (default to Nigeria +234)
        if phone_digits.startswith('0'):
            # Replace leading 0 with Nigeria country code
            phone_digits = '234' + phone_digits[1:]
        elif not phone_digits.startswith('234'):
            # Add Nigeria country code if not present
            phone_digits = '234' + phone_digits

        return f"whatsapp:+{phone_digits}"

    @classmethod
    async def send_message(cls, to_phone: str, message: str) -> bool:
        """
        Send a WhatsApp message using Twilio.

        Args:
            to_phone: Recipient phone number
            message: Message content

        Returns:
            bool: True if message was sent successfully
        """
        try:
            client = cls._get_client()
            from_number = f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}"
            to_number = cls._format_phone_for_whatsapp(to_phone)

            message = client.messages.create(
                from_=from_number,
                body=message,
                to=to_number
            )

            cls.logger.info(f"WhatsApp message sent. SID: {message.sid}")
            return True
        except Exception as e:
            cls.logger.error(f"Failed to send WhatsApp message: {str(e)}")
            return False

    @classmethod
    async def send_driver_assignment(
            cls,
            driver_phone: str,
            tracking_id: str,
            tracking_link: str,
            otp_code: str,
            vendor_name: str,
            customer_name: str,
            delivery_address: str
    ) -> bool:
        """Send assignment notification to driver with OTP."""
        message = (
            f"🚚 *New Delivery Assignment* 🚚\n\n"
            f"Tracking ID: *{tracking_id}*\n"
            f"Vendor: {vendor_name}\n"
            f"Customer: {customer_name}\n"
            f"Delivery Address: {delivery_address}\n\n"
            f"*Your OTP code is: {otp_code}*\n\n"
            f"Click this link to start tracking: {tracking_link}\n\n"
            f"Please enter the OTP code when prompted."
        )
        return await cls.send_message(driver_phone, message)

    @classmethod
    async def send_customer_notification(
            cls,
            customer_phone: str,
            tracking_id: str,
            tracking_link: str,
            driver_name: str,
            package_info: str
    ) -> bool:
        """Send delivery notification to customer."""
        message = (
            f"📦 *Package On The Way* 📦\n\n"
            f"Your package: {package_info}\n"
            f"Tracking ID: *{tracking_id}*\n"
            f"Driver: {driver_name}\n\n"
            f"Track your delivery in real-time: {tracking_link}\n\n"
            f"You will receive updates when your package is on the way."
        )
        return await cls.send_message(customer_phone, message)

    @classmethod
    async def send_delivery_accepted(
            cls,
            customer_phone: str,
            tracking_id: str,
            driver_name: str,
            package_info: str
    ) -> bool:
        """Notify customer that driver has accepted the delivery."""
        message = (
            f"✅ *Delivery Update* ✅\n\n"
            f"Your package: {package_info}\n"
            f"Tracking ID: *{tracking_id}*\n\n"
            f"Driver {driver_name} has accepted your delivery and will pick it up soon."
        )
        return await cls.send_message(customer_phone, message)

    @classmethod
    async def send_delivery_in_transit(
            cls,
            customer_phone: str,
            tracking_id: str,
            tracking_link: str
    ) -> bool:
        """Notify customer that delivery is on the way."""
        message = (
            f"🚚 *Your Package Is On The Way* 🚚\n\n"
            f"Tracking ID: *{tracking_id}*\n\n"
            f"Your driver is on the way with your package!\n\n"
            f"Track your delivery in real-time: {tracking_link}\n\n"
            f"You'll be notified when the driver arrives."
        )
        return await cls.send_message(customer_phone, message)

    @classmethod
    async def send_delivery_completed(
            cls,
            vendor_phone: str,
            tracking_id: str,
            customer_name: str
    ) -> bool:
        """Notify vendor that delivery is complete."""
        message = (
            f"✅ *Delivery Completed* ✅\n\n"
            f"Tracking ID: *{tracking_id}*\n\n"
            f"Your package has been successfully delivered to {customer_name}."
        )
        return await cls.send_message(vendor_phone, message)
