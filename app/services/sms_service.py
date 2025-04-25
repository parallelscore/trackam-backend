# app/services/sms_service.py
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.core.config import settings
from app.utils.logging_util import setup_logger

class SMSService:

    def __init__(self):
        self.logger = setup_logger(__name__)
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.sms_from_number = settings.TWILIO_PHONE_NUMBER
        self.whatsapp_from_number = settings.TWILIO_WHATSAPP_NUMBER
        self.client = Client(self.account_sid, self.auth_token) if self.account_sid and self.auth_token else None
        self.enabled = settings.SMS_SERVICE_ENABLED

    async def send_sms(self, to_number: str, message: str) -> bool:
        """
        Send SMS using Twilio API

        Args:
            to_number: Recipient phone number (should be in E.164 format)
            message: Text message to send

        Returns:
            bool: True if the message was sent successfully, False otherwise
        """
        # If SMS service is disabled, log message and return
        if not self.enabled or not self.client:
            self.logger.info(f"SMS service disabled. Would have sent to {to_number}: {message}")
            return True

        # Format phone number to E.164 format for Twilio
        formatted_number = self._format_phone_number(to_number)

        try:
            # Send message via Twilio
            sms_message = self.client.messages.create(
                body=message,
                from_=self.sms_from_number,
                to=formatted_number
            )

            self.logger.info(f"SMS sent to {to_number}, Twilio SID: {sms_message.sid}")
            return True

        except TwilioRestException as e:
            self.logger.error(f"Twilio error when sending SMS to {to_number}: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error when sending SMS to {to_number}: {str(e)}")
            return False

    async def send_whatsapp(self, to_number: str, message: str) -> bool:
        """
        Send WhatsApp message using Twilio API

        Args:
            to_number: Recipient phone number (should be in E.164 format)
            message: Text message to send

        Returns:
            bool: True if the message was sent successfully, False otherwise
        """
        # If WhatsApp service is disabled, log message and return
        whatsapp_enabled = getattr(settings, "WHATSAPP_SERVICE_ENABLED", self.enabled)
        if not whatsapp_enabled or not self.client:
            self.logger.info(f"WhatsApp service disabled. Would have sent to {to_number}: {message}")
            return True

        # Format phone number to E.164 format for Twilio
        formatted_number = self._format_phone_number(to_number)

        try:
            # Send message via Twilio WhatsApp
            # For Twilio WhatsApp, we prefix with 'whatsapp:' for both from and to
            whatsapp_message = self.client.messages.create(
                body=message,
                from_=f"whatsapp:{self.whatsapp_from_number}",
                to=f"whatsapp:{formatted_number}"
            )

            self.logger.info(f"WhatsApp message sent to {to_number}, Twilio SID: {whatsapp_message.sid}")
            return True

        except TwilioRestException as e:
            self.logger.error(f"Twilio error when sending WhatsApp to {to_number}: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error when sending WhatsApp to {to_number}: {str(e)}")
            return False

    def _format_phone_number(self, phone_number: str) -> str:
        """
        Format phone number to E.164 format for Twilio

        Args:
            phone_number: Phone number in various formats

        Returns:
            str: Phone number in E.164 format
        """
        # Remove any non-digit characters
        digits_only = ''.join(filter(str.isdigit, phone_number))

        # If it's a Nigerian number starting with 0, replace with +234
        if len(digits_only) == 11 and digits_only.startswith('0'):
            return f"+234{digits_only[1:]}"

        # If it has 10 digits, assume Nigerian number without leading 0
        elif len(digits_only) == 10 and digits_only.startswith(('7', '8', '9')):
            return f"+234{digits_only}"

        # If it's already in international format (starts with 234)
        elif len(digits_only) == 13 and digits_only.startswith('234'):
            return f"+{digits_only}"

        # If it's already in full E.164 format with +
        elif phone_number.startswith('+'):
            return phone_number

        # Default to adding + if it looks like a complete international number
        elif len(digits_only) > 10:
            return f"+{digits_only}"

        # Return original if we can't determine format
        return phone_number

# Create a singleton instance
sms_service = SMSService()