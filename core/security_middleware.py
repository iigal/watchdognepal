import time
import logging
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from .utils import get_client_ip

logger = logging.getLogger(__name__)

class ScannerBlockingMiddleware:
    """
    Middleware to block IPs that trigger too many 404s in a short window.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Configurable thresholds
        self.block_threshold = 20  # Number of 404s
        self.window_seconds = 60   # Time window
        self.block_duration = 3600 # Block for 1 hour

    def __call__(self, request):
        # Don't block staff/admin
        if hasattr(request, 'user') and request.user.is_authenticated and request.user.is_staff:
            return self.get_response(request)

        ip = get_client_ip(request)
        
        # Check if already blocked
        if cache.get(f"blocked_ip_{ip}"):
            logger.warning(f"Blocked request from scanner IP: {ip}")
            return HttpResponseForbidden("Your IP has been temporarily blocked due to suspicious activity.")

        response = self.get_response(request)

        # Track 404s
        if response.status_code == 404:
            count_key = f"scanner_count_{ip}"
            current_count = cache.get(count_key, 0) + 1
            
            if current_count >= self.block_threshold:
                # Block the IP
                cache.set(f"blocked_ip_{ip}", True, self.block_duration)
                logger.error(f"IP {ip} blocked for hitting threshold of {current_count} 404s.")
                return HttpResponseForbidden("Suspicious activity detected. Your IP is blocked.")
            
            # Update count with window expiry
            cache.set(count_key, current_count, self.window_seconds)

        return response
