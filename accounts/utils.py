import requests
import logging
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

def send_otp_email(email_address, otp):
    """
    Sends an OTP message via Email.
    """
    subject = "Your Watchdog Nepal Verification Code"
    message = f"Your Verification Code is: {otp}"
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@watchdognepal.com')
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[email_address],
            fail_silently=False,
        )
        logger.info(f"OTP sent successfully to {email_address}")
        return True
    except Exception as e:
        logger.error(f"Exception occurred while sending Email to {email_address}: {e}")
        return False


def send_otp_sms(mobile_number, otp):
    """
    Sends an OTP message via Aakash SMS API v4.
    """
    url = 'https://sms.aakashsms.com/sms/v4/send-user'
    token = getattr(settings, 'AAKASH_SMS_TOKEN', '')
    
    if not token:
        logger.error("AAKASH_SMS_TOKEN is not configured in settings.")
        return False
        
    headers = {
        'auth-token': token,
        'Content-Type': 'application/json'
    }
    
    message = f"Your Verification Code is: {otp}"
    
    payload = {
        'to': [mobile_number],
        'text': [message]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Log response or handle specific errors if needed
        # The API wraps response in a list like {"responses": [{"error": false, ...}]}
        
        # Just check for explicit failure returned
        if 'error' in data and data['error'] is True:
            logger.error(f"Failed to send SMS to {mobile_number}: {data.get('message')}")
            return False
            
        logger.info(f"OTP sent successfully to {mobile_number}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Exception occurred while sending SMS to {mobile_number}: {e}")
        return False
