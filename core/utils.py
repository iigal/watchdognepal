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
    # Skip for local/reserved IPs
    if ip_address in ['127.0.0.1', '::1'] or ip_address.startswith('192.168.') or ip_address.startswith('10.'):
        return

    # Skip during tests to avoid database locking and external requests
    import sys
    if 'test' in sys.argv:
        return

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

def get_country_from_ip(ip_address):
    """
    Synchronously fetches the country name for a given IP.
    Returns 'Nepal' if in Nepal, otherwise the country name or 'Unknown'.
    """
    # Quick defaults for local development
    if ip_address in ['127.0.0.1', '::1'] or ip_address.startswith('192.168.') or ip_address.startswith('10.'):
        return "Nepal" # Default to Nepal for local dev unless specified

    # Check cache first
    cached = IPLocationCache.objects.filter(ip_address=ip_address).first()
    if cached and cached.country:
        return cached.country

    # Fetch synchronously if not in cache
    url = f"http://ip-api.com/json/{ip_address}"
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                country = data.get('country', 'Unknown')
                # Save to cache for next time
                IPLocationCache.objects.update_or_create(
                    ip_address=ip_address,
                    defaults={
                        'city': data.get('city'),
                        'country': country,
                        'latitude': data.get('lat'),
                        'longitude': data.get('lon'),
                    }
                )
                return country
    except Exception as e:
        logger.error(f"Sync IP lookup failed: {e}")
    
    return "Unknown"
