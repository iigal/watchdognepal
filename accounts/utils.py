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
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR')
    return ip

def get_sms_credits():
    """
    Fetches the available SMS credits from Aakash SMS API.
    """
    token = getattr(settings, 'AAKASH_SMS_TOKEN', '').strip()
    
    if not token:
        return "N/A (Token missing)"
        
    # Try standard v1 using form data first (Most common for Aakash SMS credit checking)
    v1_url = 'https://sms.aakashsms.com/sms/v1/credit'
    payload = {'auth_token': token}
    
    try:
        response = requests.post(v1_url, data=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'available_credit' in data:
                return data['available_credit']
            elif 'credit' in data:
                return data['credit']
            elif 'response' in data and not getattr(data, 'error', False):
                return data['response']
                
        # If v1 fails/isn't 200, try v4 with headers
        v4_url = 'https://sms.aakashsms.com/sms/v4/credit'
        v4_response = requests.post(v4_url, headers={'auth-token': token}, json={}, timeout=10)
        if v4_response.status_code == 200:
            v4_data = v4_response.json()
            if not v4_data.get('error'):
                if 'available_credit' in v4_data:
                    return v4_data['available_credit']
                elif 'data' in v4_data and isinstance(v4_data['data'], dict):
                    return v4_data['data'].get('available_credit', 'Format Unknown')
                    
        return f"API Error: HTTP {response.status_code}"
        
    except Exception as e:
        logger.error(f"Failed to fetch SMS credits: {e}")
        return "Error fetching API (Check Logs)"

def send_otp_email(email_address, otp):
    """
    Sends an OTP message via Email.
    """
    subject = "Your Watchdog Nepal Verification Code"
    message = f"Your Verification Code is: {otp}"
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@watchdognepal.com')
    
    backend = getattr(settings, 'EMAIL_BACKEND', 'Unknown')
    logger.info(f"Attempting to send OTP email to {email_address} using backend: {backend}")
    
    try:
        sent_count = send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[email_address],
            fail_silently=False,
        )
        if sent_count > 0:
            logger.info(f"OTP email sent successfully to {email_address}")
            return True
        else:
            logger.warning(f"send_mail returned 0 for {email_address}")
            return False
    except Exception as e:
        logger.error(f"Failed to send verification email to {email_address}. Error: {str(e)}")
        # In production, this might be due to missing connection settings
        if not settings.DEBUG:
            logger.error("Check if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD are set correctly in the environment.")
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
