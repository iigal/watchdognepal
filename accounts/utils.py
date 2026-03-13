import requests
import logging
import json
from django.conf import settings
from django.core.mail import send_mail
from .models import SMSLog

logger = logging.getLogger(__name__)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_sms_credits():
    """
    Fetches the available SMS credits from Aakash SMS API.
    """
    url = 'https://sms.aakashsms.com/sms/v4/credit'
    token = getattr(settings, 'AAKASH_SMS_TOKEN', '')
    
    if not token:
        return "N/A (Token missing)"
        
    payload = {'auth_token': token}
    
    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data.get('error'):
            return data.get('available_credit', 'Unknown')
        else:
            return "Error fetching credits"
    except Exception as e:
        logger.error(f"Failed to fetch SMS credits: {e}")
        return "Error fetching credits"

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

def send_otp_sms(mobile_number, otp, ip_address=None):
    """
    Sends an OTP message via Aakash SMS API v4 and logs it.
    """
    url = 'https://sms.aakashsms.com/sms/v4/send-user'
    token = getattr(settings, 'AAKASH_SMS_TOKEN', '')
    
    if not token:
        logger.error("AAKASH_SMS_TOKEN is not configured in settings.")
        if ip_address:
            SMSLog.objects.create(mobile_number=mobile_number, ip_address=ip_address, is_success=False, response_data="Token missing")
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
        
        is_success = True
        if 'error' in data and data['error'] is True:
            logger.error(f"Failed to send SMS to {mobile_number}: {data.get('message')}")
            is_success = False
        else:
            logger.info(f"OTP sent successfully to {mobile_number}")
            
        if ip_address:
            SMSLog.objects.create(
                mobile_number=mobile_number, 
                ip_address=ip_address, 
                is_success=is_success, 
                response_data=json.dumps(data)
            )
            
        return is_success
    except Exception as e:
        logger.error(f"Exception occurred while sending SMS to {mobile_number}: {e}")
        if ip_address:
             SMSLog.objects.create(
                mobile_number=mobile_number, 
                ip_address=ip_address, 
                is_success=False, 
                response_data=str(e)
            )
        return False
