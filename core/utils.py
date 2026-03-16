import logging
import requests
import threading
from django.conf import settings
from .models import IPLocationCache

logger = logging.getLogger(__name__)

def fetch_ip_location(ip_address):
    """
    Fetches IP geolocation data from ip-api.com and saves/updates it in IPLocationCache.
    """
    # IP-API limit: 45 requests per minute for free tier
    url = f"http://ip-api.com/json/{ip_address}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == 'success':
            IPLocationCache.objects.update_or_create(
                ip_address=ip_address,
                defaults={
                    'city': data.get('city'),
                    'country': data.get('country'),
                    'latitude': data.get('lat'),
                    'longitude': data.get('lon'),
                }
            )
        else:
            logger.warning(f"Failed to fetch IP location for {ip_address}: {data.get('message')}")
            # Save empty so we don't keep retrying failed IPs constantly
            IPLocationCache.objects.update_or_create(
                ip_address=ip_address,
                defaults={'city': 'Unknown'}
            )
    except Exception as e:
        logger.error(f"Error fetching IP location for {ip_address}: {e}")

def get_client_ip(request):
    """
    Extracts the client's IP from the request.
    (Duplicated from accounts, but kept here for app independence)
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR')
    return ip
