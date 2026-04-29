import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


async def send_sms_confirmation(
    to_number: str,
    patient_name: str,
    doctor_name: str,
    date: str,
    time: str,
) -> bool:
    """
    Send an SMS appointment confirmation via Twilio.
    Returns True on success, False on failure.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_number = os.getenv("TWILIO_PHONE_NUMBER", "")

    if not all([account_sid, auth_token, from_number]):
        logger.warning("Twilio credentials not configured. Skipping SMS.")
        return False

    message_body = (
        f"Hello {patient_name}, your appointment has been confirmed.\n"
        f"Doctor: {doctor_name}\n"
        f"Date: {date}\n"
        f"Time: {time}\n"
        f"Please arrive 10 minutes early. Reply CANCEL to cancel."
    )

    try:
        from twilio.rest import Client

        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=message_body,
            from_=from_number,
            to=to_number,
        )
        logger.info("SMS sent: %s", message.sid)
        return True
    except Exception as exc:
        logger.error("Failed to send SMS: %s", exc)
        return False
